"""
Shared Telegram delivery module.

One bot serves both India and US systems, routing to different chat IDs.
Handles message sending, retry logic, deduplication, and audit logging
to the alerts_sent DB table.

Usage:
    from shared.delivery.telegram import init_telegram, send_alert, send_message

    # At startup (after init_db)
    await init_telegram(config)

    # Send a routed alert (preferred for all alerts)
    await send_alert(system="india", alert_type=AlertType.TRADE_ALERT,
                     text="...", symbol="RELIANCE")

    # Send a raw message (low-level, no dedup/logging)
    await send_message(chat_id="123456", text="Hello")
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

import telegram
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.db.models import get_db
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

# ─── Constants (no magic numbers) ───

_MAX_MESSAGE_LENGTH = 4096
_SEND_TIMEOUT_SECONDS = 15
_RETRY_MAX_ATTEMPTS = 2
_RETRY_MIN_WAIT_SECONDS = 1
_RETRY_MAX_WAIT_SECONDS = 5
_DEDUP_WINDOW_MINUTES = 60
_MARKDOWNV2_SPECIAL_CHARS = r'_*[]()~`>#+-=|{}.!'


# ─── Alert type enum ───


class AlertType(str, Enum):
    """Alert types matching the alerts_sent table schema.

    Using str mixin so values serialize naturally to SQL TEXT columns.
    """

    MORNING_BRIEFING = "morning_briefing"
    TRADE_ALERT = "trade_alert"
    PREP_ALERT = "prep_alert"
    ENTRY_TRIGGER = "entry_trigger"
    WATCHPOINT = "watchpoint"
    TARGET_HIT = "target_hit"
    SL_HIT = "sl_hit"
    EXIT_REMINDER = "exit_reminder"
    WEEKLY_REVIEW = "weekly_review"
    SYSTEM_ERROR = "system_error"
    RISK_BREACH = "risk_breach"


# ─── Module-level state (set by init_telegram) ───

logger = get_logger(__name__)

_bot: telegram.Bot | None = None
_india_chat_id: str | None = None
_us_chat_id: str | None = None


# ─── Lifecycle ───


async def init_telegram(config: AppConfig) -> None:
    """Initialize the Telegram bot.

    Must be called once at startup, after init_db().
    Validates the bot token by calling getMe().

    Args:
        config: Application config with telegram.bot_token and chat IDs.

    Raises:
        RuntimeError: If bot token is empty or invalid.
    """
    global _bot, _india_chat_id, _us_chat_id

    if not config.telegram.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    _bot = telegram.Bot(token=config.telegram.bot_token)
    _india_chat_id = config.telegram.india_chat_id
    _us_chat_id = config.telegram.us_chat_id

    start = time.monotonic()
    try:
        me = await _bot.get_me()
        latency = int((time.monotonic() - start) * 1000)
        log_api_call(
            logger,
            provider="telegram",
            endpoint="getMe",
            status="success",
            latency_ms=latency,
            data_points=1,
        )
        logger.info(
            "Telegram bot initialized",
            bot_username=me.username,
            india_chat_id=_india_chat_id,
            us_chat_id=_us_chat_id,
        )
    except telegram.error.TelegramError as exc:
        latency = int((time.monotonic() - start) * 1000)
        log_api_call(
            logger,
            provider="telegram",
            endpoint="getMe",
            status="failure",
            latency_ms=latency,
            error=str(exc),
        )
        _bot = None
        raise RuntimeError(f"Telegram bot token validation failed: {exc}") from exc


async def shutdown_telegram() -> None:
    """Shutdown the Telegram bot, closing its HTTP session.

    Called during application shutdown for clean resource cleanup.
    Safe to call even if bot is not initialized.
    """
    global _bot
    if _bot is not None:
        await _bot.shutdown()
        _bot = None
        logger.info("Telegram bot shutdown")


# ─── Helpers ───


def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format.

    Apply to ALL dynamic text before embedding in MarkdownV2 messages.
    Do NOT apply to static formatting characters (e.g., *bold*).

    Args:
        text: Raw text to escape.

    Returns:
        Escaped text safe for MarkdownV2.
    """
    for char in _MARKDOWNV2_SPECIAL_CHARS:
        text = text.replace(char, f"\\{char}")
    return text


def _split_message(text: str, max_length: int = _MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a message into chunks that fit Telegram's size limit.

    Splitting priority:
    1. Paragraph boundaries (double newline)
    2. Line boundaries (single newline)
    3. Hard cut at max_length

    Args:
        text: Full message text.
        max_length: Maximum characters per chunk.

    Returns:
        List of message chunks, each within max_length.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try paragraph boundary first
        cut_point = remaining.rfind("\n\n", 0, max_length)
        if cut_point == -1:
            # Try line boundary
            cut_point = remaining.rfind("\n", 0, max_length)
        if cut_point == -1:
            # Hard cut
            cut_point = max_length

        chunks.append(remaining[:cut_point])
        remaining = remaining[cut_point:].lstrip("\n")

    return chunks


def _content_hash(text: str) -> str:
    """Generate SHA-256 hash of message content for deduplication.

    Args:
        text: Message text to hash.

    Returns:
        Hex digest of SHA-256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _is_duplicate(system: str, content_hash: str) -> bool:
    """Check if a message with this content hash was sent recently.

    Looks up alerts_sent for a matching content_hash within the
    deduplication window.

    Args:
        system: "india" or "us".
        content_hash: SHA-256 hash of the message content.

    Returns:
        True if a matching sent alert exists within the dedup window.
    """
    try:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM alerts_sent
                WHERE system = ?
                  AND content_hash = ?
                  AND status = 'sent'
                  AND timestamp > datetime('now', ?)
                """,
                (system, content_hash, f"-{_DEDUP_WINDOW_MINUTES} minutes"),
            )
            row = await cursor.fetchone()
            return row[0] > 0 if row else False
    except Exception as exc:
        # DB check failure should NOT suppress the message — send it anyway
        logger.warning(
            "Dedup check failed, proceeding with send",
            system=system,
            error=str(exc),
        )
        return False


async def _log_alert_to_db(
    *,
    system: str,
    alert_type: str,
    symbol: str | None,
    content_hash: str,
    telegram_msg_id: str | None,
    status: str,
    error: str | None,
) -> None:
    """Insert a record into the alerts_sent table.

    DB logging failure should never crash the system.
    """
    timestamp = datetime.now(tz=ZoneInfo("UTC")).isoformat()
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO alerts_sent
                    (system, timestamp, alert_type, symbol, content_hash,
                     telegram_msg_id, status, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    system,
                    timestamp,
                    alert_type,
                    symbol,
                    content_hash,
                    telegram_msg_id,
                    status,
                    error,
                ),
            )
            await db.commit()
    except Exception as exc:
        logger.error(
            "Failed to log alert to DB",
            system=system,
            alert_type=alert_type,
            error=str(exc),
        )


# ─── Send functions ───


@retry(
    stop=stop_after_attempt(_RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(
        multiplier=1,
        min=_RETRY_MIN_WAIT_SECONDS,
        max=_RETRY_MAX_WAIT_SECONDS,
    ),
    retry=retry_if_exception_type(telegram.error.TimedOut),
    reraise=True,
)
async def _send_single_message(
    chat_id: str,
    text: str,
    parse_mode: str,
) -> telegram.Message:
    """Send a single message chunk with retry logic.

    Only retries on timeout; other Telegram errors are not retried.

    Raises:
        RuntimeError: If bot is not initialized.
        telegram.error.TelegramError: On non-retryable failure.
    """
    if _bot is None:
        raise RuntimeError("Telegram bot not initialized. Call init_telegram() first.")

    return await _bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        read_timeout=_SEND_TIMEOUT_SECONDS,
        write_timeout=_SEND_TIMEOUT_SECONDS,
        connect_timeout=_SEND_TIMEOUT_SECONDS,
    )


async def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = "MarkdownV2",
) -> bool:
    """Send a message to a Telegram chat.

    Handles message splitting if text exceeds 4096 characters.
    Logs every send attempt via log_api_call.

    Args:
        chat_id: Telegram chat ID to send to.
        text: Message text (will be split if too long).
        parse_mode: Telegram parse mode. Default "MarkdownV2".

    Returns:
        True if ALL chunks sent successfully, False otherwise.
    """
    if not chat_id:
        logger.error("Cannot send message: empty chat_id")
        return False

    if not text:
        logger.error("Cannot send message: empty text")
        return False

    chunks = _split_message(text)
    all_sent = True

    for i, chunk in enumerate(chunks):
        start = time.monotonic()
        try:
            msg = await _send_single_message(chat_id, chunk, parse_mode)
            latency = int((time.monotonic() - start) * 1000)
            log_api_call(
                logger,
                provider="telegram",
                endpoint="sendMessage",
                status="success",
                latency_ms=latency,
                data_points=1,
            )
            logger.debug(
                "Message chunk sent",
                chat_id=chat_id,
                chunk=f"{i + 1}/{len(chunks)}",
                msg_id=msg.message_id,
            )
        except Exception as exc:
            latency = int((time.monotonic() - start) * 1000)
            log_api_call(
                logger,
                provider="telegram",
                endpoint="sendMessage",
                status="failure",
                latency_ms=latency,
                error=str(exc),
            )
            logger.error(
                "Failed to send message chunk",
                chat_id=chat_id,
                chunk=f"{i + 1}/{len(chunks)}",
                error=str(exc),
            )
            all_sent = False
            break  # Don't send partial messages

    return all_sent


async def send_alert(
    system: str,
    alert_type: AlertType | str,
    text: str,
    symbol: str | None = None,
) -> bool:
    """Send an alert via Telegram with routing, deduplication, and DB logging.

    Routes to the correct chat_id based on system. Checks for duplicate
    content within the dedup window. Logs every attempt to alerts_sent.

    Args:
        system: "india" or "us".
        alert_type: Type of alert (use AlertType enum).
        text: Fully formatted message text (already MarkdownV2-escaped).
        symbol: Stock symbol if applicable, None for briefings/reviews.

    Returns:
        True if sent (or correctly suppressed as duplicate). False on failure.
    """
    alert_type_str = alert_type.value if isinstance(alert_type, AlertType) else alert_type

    # Route to correct chat ID
    if system == "india":
        chat_id = _india_chat_id
    elif system == "us":
        chat_id = _us_chat_id
    else:
        logger.error("Unknown system for alert routing", system=system)
        return False

    if not chat_id:
        logger.error(
            "Chat ID not configured for system",
            system=system,
            alert_type=alert_type_str,
        )
        return False

    # Deduplication check
    hash_val = _content_hash(text)
    if await _is_duplicate(system, hash_val):
        logger.info(
            "Alert suppressed as duplicate",
            system=system,
            alert_type=alert_type_str,
            symbol=symbol,
        )
        return True  # Not a failure — intentionally suppressed

    # Send the message
    chunks = _split_message(text)
    first_msg_id: str | None = None
    send_error: str | None = None
    all_sent = True

    for i, chunk in enumerate(chunks):
        start = time.monotonic()
        try:
            msg = await _send_single_message(chat_id, chunk, "MarkdownV2")
            latency = int((time.monotonic() - start) * 1000)
            log_api_call(
                logger,
                provider="telegram",
                endpoint="sendMessage",
                status="success",
                latency_ms=latency,
                data_points=1,
            )
            if i == 0:
                first_msg_id = str(msg.message_id)
        except Exception as exc:
            latency = int((time.monotonic() - start) * 1000)
            log_api_call(
                logger,
                provider="telegram",
                endpoint="sendMessage",
                status="failure",
                latency_ms=latency,
                error=str(exc),
            )
            send_error = str(exc)
            all_sent = False
            break  # Stop sending remaining chunks on failure

    # Log to alerts_sent table
    await _log_alert_to_db(
        system=system,
        alert_type=alert_type_str,
        symbol=symbol,
        content_hash=hash_val,
        telegram_msg_id=first_msg_id,
        status="sent" if all_sent else "failed",
        error=send_error,
    )

    if all_sent:
        logger.info(
            "Alert sent successfully",
            system=system,
            alert_type=alert_type_str,
            symbol=symbol,
            msg_id=first_msg_id,
            chunks=len(chunks),
        )
    else:
        logger.error(
            "Alert send failed",
            system=system,
            alert_type=alert_type_str,
            symbol=symbol,
            error=send_error,
        )

    return all_sent
