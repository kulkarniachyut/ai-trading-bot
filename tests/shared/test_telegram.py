"""
Unit tests for shared/delivery/telegram.py

Each function is tested in isolation with mocked dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import telegram.error

from shared.delivery.telegram import (
    AlertType,
    _content_hash,
    _split_message,
    escape_md,
    init_telegram,
    send_alert,
    send_message,
    shutdown_telegram,
)


# ─── Test: escape_md ───


class TestEscapeMd:
    def test_escapes_all_special_chars(self):
        raw = r'_*[]()~`>#+-=|{}.!'
        escaped = escape_md(raw)
        for char in raw:
            assert f"\\{char}" in escaped

    def test_plain_text_unchanged(self):
        assert escape_md("hello world") == "hello world"

    def test_empty_string(self):
        assert escape_md("") == ""

    def test_mixed_content(self):
        result = escape_md("RELIANCE: 2450.50 (+1.2%)")
        assert "\\." in result
        assert "\\+" in result
        assert "\\(" in result
        assert "\\)" in result
        assert "RELIANCE" in result

    def test_preserves_non_special(self):
        assert escape_md("abc123") == "abc123"

    def test_rupee_symbol_unchanged(self):
        assert escape_md("₹2,450") == "₹2,450"


# ─── Test: _split_message ───


class TestSplitMessage:
    def test_short_message_single_chunk(self):
        assert _split_message("Hello") == ["Hello"]

    def test_exact_limit_single_chunk(self):
        text = "a" * 4096
        assert _split_message(text) == [text]

    def test_splits_on_paragraph_boundary(self):
        para1 = "a" * 2000
        para2 = "b" * 2000
        para3 = "c" * 2000
        text = f"{para1}\n\n{para2}\n\n{para3}"
        chunks = _split_message(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 4096

    def test_splits_on_line_boundary(self):
        lines = ["a" * 100 for _ in range(50)]
        text = "\n".join(lines)
        chunks = _split_message(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 4096

    def test_hard_cut_no_newlines(self):
        text = "a" * 5000
        chunks = _split_message(text)
        assert len(chunks) == 2
        assert len(chunks[0]) == 4096
        assert len(chunks[1]) == 904

    def test_multiple_chunks(self):
        text = "a" * 12000
        chunks = _split_message(text)
        assert len(chunks) == 3
        for chunk in chunks:
            assert len(chunk) <= 4096

    def test_empty_string(self):
        assert _split_message("") == [""]

    def test_custom_max_length(self):
        text = "a" * 20
        chunks = _split_message(text, max_length=10)
        assert len(chunks) == 2
        assert all(len(c) <= 10 for c in chunks)


# ─── Test: _content_hash ───


class TestContentHash:
    def test_deterministic(self):
        assert _content_hash("hello") == _content_hash("hello")

    def test_different_input_different_hash(self):
        assert _content_hash("hello") != _content_hash("world")

    def test_returns_hex_string(self):
        h = _content_hash("test")
        assert all(c in "0123456789abcdef" for c in h)
        assert len(h) == 64


# ─── Test: AlertType ───


class TestAlertType:
    def test_all_types_defined(self):
        assert len(AlertType) == 11

    def test_string_serialization(self):
        assert AlertType.TRADE_ALERT == "trade_alert"
        assert AlertType.MORNING_BRIEFING == "morning_briefing"

    def test_all_values(self):
        expected = {
            "morning_briefing", "trade_alert", "prep_alert",
            "entry_trigger", "watchpoint", "target_hit",
            "sl_hit", "exit_reminder", "weekly_review",
            "system_error", "risk_breach",
        }
        assert {a.value for a in AlertType} == expected

    def test_value_attribute(self):
        assert AlertType.SYSTEM_ERROR.value == "system_error"


# ─── Fixtures for bot tests ───


def _make_mock_config(bot_token="test-token", india_chat_id="111", us_chat_id="222"):
    """Create a mock AppConfig with telegram settings."""
    config = MagicMock()
    config.telegram.bot_token = bot_token
    config.telegram.india_chat_id = india_chat_id
    config.telegram.us_chat_id = us_chat_id
    return config


# ─── Test: init_telegram ───


class TestInitTelegram:
    async def test_successful_init(self):
        config = _make_mock_config()
        mock_bot_instance = AsyncMock()
        mock_bot_instance.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
        mock_bot_instance.shutdown = AsyncMock()

        with patch("shared.delivery.telegram.telegram.Bot", return_value=mock_bot_instance):
            await init_telegram(config)
            mock_bot_instance.get_me.assert_awaited_once()
            await shutdown_telegram()

    async def test_empty_token_raises(self):
        config = _make_mock_config(bot_token="")
        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN is not set"):
            await init_telegram(config)

    async def test_invalid_token_raises(self):
        config = _make_mock_config()
        mock_bot_instance = AsyncMock()
        mock_bot_instance.get_me = AsyncMock(
            side_effect=telegram.error.InvalidToken()
        )
        mock_bot_instance.shutdown = AsyncMock()

        with patch("shared.delivery.telegram.telegram.Bot", return_value=mock_bot_instance):
            with pytest.raises(RuntimeError, match="validation failed"):
                await init_telegram(config)


# ─── Test: send_message ───


class TestSendMessage:
    @pytest_asyncio.fixture(autouse=True)
    async def _setup_bot(self):
        """Initialize bot with mock for each test."""
        config = _make_mock_config()
        self.mock_bot = AsyncMock()
        self.mock_bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
        self.mock_msg = MagicMock()
        self.mock_msg.message_id = 12345
        self.mock_bot.send_message = AsyncMock(return_value=self.mock_msg)
        self.mock_bot.shutdown = AsyncMock()

        with patch("shared.delivery.telegram.telegram.Bot", return_value=self.mock_bot):
            await init_telegram(config)
            yield
            await shutdown_telegram()

    async def test_successful_send(self):
        result = await send_message("111", "Hello")
        assert result is True
        self.mock_bot.send_message.assert_awaited_once()

    async def test_empty_chat_id_returns_false(self):
        result = await send_message("", "Hello")
        assert result is False
        self.mock_bot.send_message.assert_not_awaited()

    async def test_empty_text_returns_false(self):
        result = await send_message("111", "")
        assert result is False
        self.mock_bot.send_message.assert_not_awaited()

    async def test_long_message_split(self):
        text = "a" * 5000
        result = await send_message("111", text)
        assert result is True
        assert self.mock_bot.send_message.await_count == 2

    async def test_telegram_error_returns_false(self):
        self.mock_bot.send_message = AsyncMock(
            side_effect=telegram.error.BadRequest("Bad request")
        )
        result = await send_message("111", "Hello")
        assert result is False

    async def test_parse_mode_passed(self):
        await send_message("111", "Hello", parse_mode="HTML")
        call_kwargs = self.mock_bot.send_message.call_args[1]
        assert call_kwargs["parse_mode"] == "HTML"


# ─── Test: send_alert ───


class TestSendAlert:
    @pytest_asyncio.fixture(autouse=True)
    async def _setup_bot_and_db(self):
        """Initialize bot with mock and patch DB for each test."""
        config = _make_mock_config()
        self.mock_bot = AsyncMock()
        self.mock_bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
        self.mock_msg = MagicMock()
        self.mock_msg.message_id = 12345
        self.mock_bot.send_message = AsyncMock(return_value=self.mock_msg)
        self.mock_bot.shutdown = AsyncMock()

        # Mock DB for _is_duplicate and _log_alert_to_db
        self.mock_db = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(0,))
        self.mock_db.execute = AsyncMock(return_value=mock_cursor)
        self.mock_db.commit = AsyncMock()
        self.mock_db.__aenter__ = AsyncMock(return_value=self.mock_db)
        self.mock_db.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.delivery.telegram.telegram.Bot", return_value=self.mock_bot):
            await init_telegram(config)
            with patch("shared.delivery.telegram.get_db", return_value=self.mock_db):
                yield
            await shutdown_telegram()

    async def test_routes_to_india_chat(self):
        await send_alert("india", AlertType.TRADE_ALERT, "Test alert", symbol="RELIANCE")
        call_kwargs = self.mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == "111"

    async def test_routes_to_us_chat(self):
        await send_alert("us", AlertType.TRADE_ALERT, "Test alert", symbol="AAPL")
        call_kwargs = self.mock_bot.send_message.call_args[1]
        assert call_kwargs["chat_id"] == "222"

    async def test_unknown_system_returns_false(self):
        result = await send_alert("japan", AlertType.TRADE_ALERT, "Test")
        assert result is False
        self.mock_bot.send_message.assert_not_awaited()

    async def test_accepts_enum_alert_type(self):
        result = await send_alert("india", AlertType.MORNING_BRIEFING, "Briefing text")
        assert result is True

    async def test_accepts_string_alert_type(self):
        result = await send_alert("india", "trade_alert", "Trade text", symbol="TCS")
        assert result is True

    async def test_symbol_is_optional(self):
        result = await send_alert("india", AlertType.WEEKLY_REVIEW, "Weekly review text")
        assert result is True

    async def test_send_failure_returns_false(self):
        self.mock_bot.send_message = AsyncMock(
            side_effect=telegram.error.BadRequest("Bad request")
        )
        result = await send_alert("india", AlertType.SYSTEM_ERROR, "Error text")
        assert result is False

    async def test_dedup_suppresses_duplicate(self):
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1,))
        self.mock_db.execute = AsyncMock(return_value=mock_cursor)

        result = await send_alert("india", AlertType.TRADE_ALERT, "Duplicate text")
        assert result is True
        self.mock_bot.send_message.assert_not_awaited()

    async def test_empty_chat_id_returns_false(self):
        config = _make_mock_config(india_chat_id="")
        with patch("shared.delivery.telegram.telegram.Bot", return_value=self.mock_bot):
            await init_telegram(config)
            result = await send_alert("india", AlertType.TRADE_ALERT, "Test")
            assert result is False


# ─── Test: shutdown_telegram ───


class TestShutdownTelegram:
    async def test_shutdown_calls_bot_shutdown(self):
        config = _make_mock_config()
        mock_bot = AsyncMock()
        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
        mock_bot.shutdown = AsyncMock()

        with patch("shared.delivery.telegram.telegram.Bot", return_value=mock_bot):
            await init_telegram(config)
            await shutdown_telegram()
            mock_bot.shutdown.assert_awaited_once()

    async def test_shutdown_when_not_initialized(self):
        await shutdown_telegram()
