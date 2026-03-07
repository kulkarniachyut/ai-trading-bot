"""
Integration tests for shared/delivery/telegram.py

These tests wire up the FULL path: config → DB → telegram module → DB verification.
Only the external Telegram API is mocked. Everything else (config loading, real SQLite DB,
real dedup logic, real DB logging) runs for real.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
import pytest_asyncio

from shared.db.models import init_db
from shared.delivery.telegram import (
    AlertType,
    _content_hash,
    init_telegram,
    send_alert,
    shutdown_telegram,
)

# ─── Fixtures ───


@pytest.fixture
def _set_test_env():
    """Set minimal env vars for config loading."""
    env_overrides = {
        "TELEGRAM_BOT_TOKEN": "test-token-123",
        "TELEGRAM_INDIA_CHAT_ID": "india-chat-999",
        "TELEGRAM_US_CHAT_ID": "us-chat-888",
    }
    with patch.dict(os.environ, env_overrides):
        yield


@pytest_asyncio.fixture
async def tmp_db(tmp_path):
    """Create a real temp SQLite DB with all tables via init_db."""
    db_path = str(tmp_path / "test_trading.db")
    await init_db(db_path)
    yield db_path


@pytest.fixture
def mock_telegram_api():
    """Patch telegram.Bot so network calls are mocked but everything else is real."""
    mock_bot = AsyncMock()
    mock_bot.get_me = AsyncMock(return_value=MagicMock(username="test_integration_bot"))
    mock_msg = MagicMock()
    mock_msg.message_id = 42
    mock_bot.send_message = AsyncMock(return_value=mock_msg)
    mock_bot.shutdown = AsyncMock()

    with patch("shared.delivery.telegram.telegram.Bot", return_value=mock_bot):
        yield mock_bot


@pytest.fixture
def test_config(_set_test_env):
    """Load a real AppConfig from test env vars."""
    from shared.utils.config import load_config

    return load_config()


@pytest_asyncio.fixture
async def full_setup(tmp_db, test_config, mock_telegram_api):
    """Full end-to-end setup: real DB + real config + mocked Telegram API."""
    await init_telegram(test_config)
    yield {
        "db_path": tmp_db,
        "config": test_config,
        "mock_bot": mock_telegram_api,
    }
    await shutdown_telegram()


# ─── Helper ───


async def _get_alerts_sent(db_path: str) -> list[dict]:
    """Query all rows from alerts_sent table."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM alerts_sent ORDER BY id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ─── Test: Full Pipeline Init ───


class TestFullPipelineInit:
    async def test_init_creates_tables_and_bot(self, tmp_db, test_config, mock_telegram_api):
        """Config → DB init → telegram init all work together."""
        await init_telegram(test_config)
        mock_telegram_api.get_me.assert_awaited_once()

        # Verify DB tables exist
        async with aiosqlite.connect(tmp_db) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in await cursor.fetchall()}

        assert "alerts_sent" in tables
        assert "trades" in tables
        assert "signals" in tables

        await shutdown_telegram()


# ─── Test: Full Alert Pipeline ───


class TestFullAlertPipeline:
    async def test_send_alert_end_to_end(self, full_setup):
        """Full flow: send_alert → Telegram API → alerts_sent DB row."""
        setup = full_setup
        result = await send_alert(
            system="india",
            alert_type=AlertType.TRADE_ALERT,
            text="Buy RELIANCE at 2450",
            symbol="RELIANCE",
        )
        assert result is True

        # Verify Telegram API was called with correct chat_id
        call_kwargs = setup["mock_bot"].send_message.call_args[1]
        assert call_kwargs["chat_id"] == "india-chat-999"
        assert call_kwargs["text"] == "Buy RELIANCE at 2450"
        assert call_kwargs["parse_mode"] == "MarkdownV2"

        # Verify DB row
        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 1
        row = rows[0]
        assert row["system"] == "india"
        assert row["alert_type"] == "trade_alert"
        assert row["symbol"] == "RELIANCE"
        assert row["status"] == "sent"
        assert row["telegram_msg_id"] == "42"
        assert row["content_hash"] == _content_hash("Buy RELIANCE at 2450")
        assert row["error"] is None

    async def test_send_alert_stores_timestamp(self, full_setup):
        """Alert timestamp is stored as ISO 8601."""
        await send_alert("india", AlertType.SYSTEM_ERROR, "Test timestamp")
        rows = await _get_alerts_sent(full_setup["db_path"])
        assert len(rows) == 1
        assert "T" in rows[0]["timestamp"]


# ─── Test: Full Deduplication Pipeline ───


class TestFullDeduplicationPipeline:
    async def test_duplicate_suppressed(self, full_setup):
        """Same alert sent twice — second is suppressed."""
        setup = full_setup
        text = "Duplicate alert test"

        result1 = await send_alert("india", AlertType.TRADE_ALERT, text)
        assert result1 is True
        assert setup["mock_bot"].send_message.await_count == 1

        result2 = await send_alert("india", AlertType.TRADE_ALERT, text)
        assert result2 is True
        assert setup["mock_bot"].send_message.await_count == 1

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 1

    async def test_different_text_not_suppressed(self, full_setup):
        """Different text produces different hash — both sent."""
        setup = full_setup

        await send_alert("india", AlertType.TRADE_ALERT, "Alert one")
        await send_alert("india", AlertType.TRADE_ALERT, "Alert two")

        assert setup["mock_bot"].send_message.await_count == 2

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 2

    async def test_different_system_not_suppressed(self, full_setup):
        """Same text to different systems — both sent (dedup is per-system)."""
        setup = full_setup
        text = "Cross-system test"

        await send_alert("india", AlertType.TRADE_ALERT, text)
        await send_alert("us", AlertType.TRADE_ALERT, text)

        assert setup["mock_bot"].send_message.await_count == 2

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 2
        systems = {row["system"] for row in rows}
        assert systems == {"india", "us"}


# ─── Test: Full Failure Pipeline ───


class TestFullFailurePipeline:
    async def test_telegram_error_logged_to_db(self, full_setup):
        """Telegram API error → DB row with status='failed' and error message."""
        setup = full_setup
        import telegram.error

        setup["mock_bot"].send_message = AsyncMock(
            side_effect=telegram.error.BadRequest("Invalid chat_id")
        )

        result = await send_alert("india", AlertType.SYSTEM_ERROR, "Error test")
        assert result is False

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 1
        assert rows[0]["status"] == "failed"
        assert "Invalid chat_id" in rows[0]["error"]

    async def test_system_recovers_after_failure(self, full_setup):
        """After a failed send, the system can still send the next alert."""
        setup = full_setup
        import telegram.error

        setup["mock_bot"].send_message = AsyncMock(
            side_effect=telegram.error.BadRequest("Temporary failure")
        )
        result1 = await send_alert("india", AlertType.SYSTEM_ERROR, "Fail alert")
        assert result1 is False

        mock_msg = MagicMock()
        mock_msg.message_id = 99
        setup["mock_bot"].send_message = AsyncMock(return_value=mock_msg)
        result2 = await send_alert("india", AlertType.TRADE_ALERT, "Recovery alert")
        assert result2 is True

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 2
        assert rows[0]["status"] == "failed"
        assert rows[1]["status"] == "sent"


# ─── Test: Full Message Split Pipeline ───


class TestFullMessageSplitPipeline:
    async def test_long_alert_split_and_logged(self, full_setup):
        """Alert > 4096 chars is split into chunks, DB has single row with first msg_id."""
        setup = full_setup
        long_text = "a" * 5000

        result = await send_alert("india", AlertType.MORNING_BRIEFING, long_text)
        assert result is True

        assert setup["mock_bot"].send_message.await_count == 2

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 1
        assert rows[0]["telegram_msg_id"] == "42"


# ─── Test: Full Multi-System Routing ───


class TestFullMultiSystemRouting:
    async def test_india_and_us_routing(self, full_setup):
        """India routes to india_chat_id, US routes to us_chat_id."""
        setup = full_setup

        await send_alert("india", AlertType.TRADE_ALERT, "India alert", symbol="TCS")
        await send_alert("us", AlertType.TRADE_ALERT, "US alert", symbol="AAPL")

        calls = setup["mock_bot"].send_message.call_args_list
        assert calls[0][1]["chat_id"] == "india-chat-999"
        assert calls[1][1]["chat_id"] == "us-chat-888"

        rows = await _get_alerts_sent(setup["db_path"])
        assert len(rows) == 2
        india_row = [r for r in rows if r["system"] == "india"][0]
        us_row = [r for r in rows if r["system"] == "us"][0]
        assert india_row["symbol"] == "TCS"
        assert us_row["symbol"] == "AAPL"


# ─── Test: Shutdown and Reinit ───


class TestShutdownAndReinit:
    async def test_lifecycle(self, tmp_db, test_config, mock_telegram_api):
        """Init → send → shutdown → reinit → send again."""
        await init_telegram(test_config)

        mock_msg = MagicMock()
        mock_msg.message_id = 1
        mock_telegram_api.send_message = AsyncMock(return_value=mock_msg)

        result1 = await send_alert("india", AlertType.SYSTEM_ERROR, "First alert")
        assert result1 is True

        await shutdown_telegram()
        mock_telegram_api.shutdown.assert_awaited_once()

        # Reinit
        mock_telegram_api.shutdown.reset_mock()
        await init_telegram(test_config)

        mock_msg2 = MagicMock()
        mock_msg2.message_id = 2
        mock_telegram_api.send_message = AsyncMock(return_value=mock_msg2)

        result2 = await send_alert("india", AlertType.SYSTEM_ERROR, "Second alert")
        assert result2 is True

        rows = await _get_alerts_sent(tmp_db)
        assert len(rows) == 2

        await shutdown_telegram()
