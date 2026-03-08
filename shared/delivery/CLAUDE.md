# shared/delivery/ — Telegram Bot & Base Formatting

**Status:** Built — Step 2

Shared Telegram infrastructure. One bot serves both India and US systems, routing to different chat IDs.

## Public API (`shared.delivery.telegram`)

- `init_telegram(config: AppConfig)` — call once at startup, after `init_db()`
- `shutdown_telegram()` — call during shutdown for clean HTTP session teardown
- `send_message(chat_id, text, parse_mode="MarkdownV2") -> bool` — low-level send with auto-splitting
- `send_alert(system, alert_type, text, symbol=None) -> bool` — routed + deduped + DB-logged send
- `escape_md(text) -> str` — escape MarkdownV2 special characters
- `AlertType` enum — 11 alert types: morning_briefing, trade_alert, prep_alert, entry_trigger, watchpoint, target_hit, sl_hit, exit_reminder, weekly_review, system_error, risk_breach

## Rules

1. Use `python-telegram-bot` v21+ (async API).
2. Messages use Telegram MarkdownV2 format. MUST escape special characters: `_*[]()~>#+-=|{}.!`
3. Message size limit: 4096 characters. If a message exceeds this, split into multiple messages.
4. Bot token from config (`TELEGRAM_BOT_TOKEN`). Chat IDs: `TELEGRAM_INDIA_CHAT_ID`, `TELEGRAM_US_CHAT_ID`.
5. Every message send is logged via `log_api_call`. Failed sends are retried once, then logged as error.
6. System-specific message templates live in `{india,us}/delivery/formatter.py`. Only base utilities live here.
7. Content deduplication: duplicate alerts (same content_hash) within 60 minutes are suppressed.
8. All sends are logged to the `alerts_sent` DB table for audit trail.
9. `escape_md` must be applied to ALL dynamic text. Static formatting markup should NOT pass through it.
