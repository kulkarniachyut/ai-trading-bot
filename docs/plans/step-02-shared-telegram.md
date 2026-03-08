# Step 2: Shared Telegram Bot

**Status:** ✅ Complete
**Branch:** `feature/shared-02-telegram`
**Merged to main:** Pending PR

## Objective

Build the shared Telegram delivery module (`shared/delivery/telegram.py`) that both India and US systems use to send alerts, trade signals, and system notifications.

## Architecture Decisions

### Pattern: Lazy-Init Singleton (mirrors `init_db`/`get_db`)
- `init_telegram(config)` called once at startup — stores singleton
- `send_message()` / `send_alert()` use the singleton
- `shutdown_telegram()` tears down gracefully

### Message Handling
- Auto-split messages at Telegram's 4096-char limit
- Split priority: paragraph boundary → line boundary → hard cut
- Fail-fast on first chunk failure (no partial messages)

### Deduplication
- SHA-256 hash of (chat_id + text) with 60-minute sliding window
- Prevents duplicate alerts on scheduler restarts or retries
- In-memory dict, pruned on each send call

### Retry Strategy
- tenacity retry on `telegram.error.TimedOut` only (2 attempts)
- Other errors (NetworkError, Forbidden, BadRequest) fail immediately
- 15-second send timeout per Telegram API call

### DB Logging
- Every sent alert logged to `alerts_sent` table (already in schema from Step 1)
- DB logging failures are swallowed — never crash the delivery pipeline

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `shared/delivery/telegram.py` | Created | Core module — init, send, dedup, split, alert routing |
| `tests/shared/test_telegram.py` | Created | 41 unit tests across 8 test classes |
| `tests/shared/test_telegram_integration.py` | Created | 11 integration tests across 7 test classes |
| `tests/__init__.py` | Created | Package marker |
| `tests/shared/__init__.py` | Created | Package marker |
| `pyproject.toml` | Created | pytest config with `asyncio_mode = "auto"` |
| `CLAUDE.md` | Modified | Added e2e testing rules |
| `shared/delivery/CLAUDE.md` | Modified | Updated status, documented public API |

## Public API

```python
# Initialization
async def init_telegram(config: AppConfig) -> None
async def shutdown_telegram() -> None

# Sending
async def send_message(chat_id: str, text: str, parse_mode: str = "MarkdownV2") -> bool
async def send_alert(system: str, alert_type: AlertType, text: str, symbol: str | None = None) -> bool

# Utilities
def escape_md(text: str) -> str

# Enum
class AlertType(Enum):
    OVERNIGHT_SUMMARY, TRADE_SIGNAL, RISK_ALERT, SYSTEM_STATUS,
    EARNINGS_ALERT, MACRO_EVENT, COMMODITY_ALERT, FII_DII_FLOW,
    STRATEGY_UPDATE, WEEKLY_REVIEW, ERROR_ALERT
```

## Testing

### Unit Tests (41 tests)
- `TestEscapeMd` — markdown escaping for all special characters
- `TestSplitMessage` — paragraph, line, and hard-cut splitting
- `TestContentHash` — deterministic hashing, uniqueness
- `TestAlertType` — all 11 alert types exist
- `TestInitTelegram` — singleton lifecycle, config validation
- `TestSendMessage` — success, failure, dedup, splitting, retry
- `TestSendAlert` — routing to correct chat_id, DB logging, formatting
- `TestShutdownTelegram` — graceful cleanup

### Integration Tests (11 tests)
- `TestFullPipelineInit` — config → DB → telegram init end-to-end
- `TestFullAlertPipeline` — full alert: init → send_alert → DB verify
- `TestFullDeduplicationPipeline` — send → dedup block → verify
- `TestFullFailurePipeline` — API failure → no DB record → verify
- `TestFullMessageSplitPipeline` — long message → split → all chunks sent
- `TestFullMultiSystemRouting` — India vs US routing to correct chat_ids
- `TestShutdownAndReinit` — shutdown → reinit → functional again

## Lessons Learned

- `pytest-asyncio` must be >= 0.21 for `asyncio_mode = "auto"` in pyproject.toml
- Async fixtures need `@pytest_asyncio.fixture`, not `@pytest.fixture`
- `pandas-ta==0.3.14b` doesn't install on Python 3.14 — install only needed deps for the step
