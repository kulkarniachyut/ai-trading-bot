# shared/delivery/ — Telegram Bot & Base Formatting

**Status:** Pending — Step 2 (next)

Shared Telegram infrastructure. One bot serves both India and US systems, routing to different chat IDs.

## Rules
1. Use `python-telegram-bot` v20+ (async API).
2. Messages use Telegram MarkdownV2 format. MUST escape special characters: `_*[]()~>#+-=|{}.!`
3. Message size limit: 4096 characters. If a message exceeds this, split into multiple messages.
4. Bot token from config (`TELEGRAM_BOT_TOKEN`). Chat IDs: `TELEGRAM_INDIA_CHAT_ID`, `TELEGRAM_US_CHAT_ID`.
5. Every message send is logged. Failed sends are retried once, then logged as error.
6. System-specific message templates live in `{india,us}/delivery/formatter.py`. Only base utilities live here.

## Escaping Helper
```python
def escape_md(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2"""
    special = r'_*[]()~`>#+-=|{}.!'
    for char in special:
        text = text.replace(char, f'\\{char}')
    return text
```
