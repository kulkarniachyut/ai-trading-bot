# Step 9: India Delivery — Telegram Formatter + Pipeline

**Status:** Pending
**Branch:** `feature/india-09-delivery`

## Objective

Build the India-specific Telegram message formatters and the delivery pipeline that composes the morning briefing and trade alerts.

## Modules to Build

### 1. Formatter (`india/delivery/formatter.py`)
```python
def format_morning_briefing(briefing: DailyBriefing) -> str
def format_trade_alert(plan: TradePlan, trade_number: int) -> str
def format_prep_alert(symbol: str, current_price: float) -> str
def format_entry_trigger(symbol: str, price: float, volume_ratio: float) -> str
def format_target_hit(symbol: str, target: int, price: float) -> str
def format_sl_hit(symbol: str, price: float) -> str
def format_exit_reminder(symbol: str, price: float) -> str
def format_weekly_review(kpis: dict) -> str
```

### 2. Notifier / Pipeline (`india/delivery/notifier.py`)
```python
async def send_morning_briefing(briefing: DailyBriefing) -> None
async def send_trade_alerts(plans: list[TradePlan]) -> None
async def send_prep_alerts(plans: list[TradePlan]) -> None
async def monitor_positions(positions: list[TradePlan]) -> None
```

## Key Constraints

- All messages in MarkdownV2 format — use `escape_md()` from `shared/delivery/telegram.py`
- Prices in INR with ₹ symbol
- Messages must fit 4096-char limit (split handled by shared module)
- Morning briefing: global markets + commodities + FII/DII + signals + trade picks
- Trade alerts: one message per trade with full entry/SL/TP details
- Uses `send_alert()` from shared module for routing + logging

## Files to Create

| File | Description |
|------|-------------|
| `india/delivery/__init__.py` | Package marker |
| `india/delivery/formatter.py` | All India message templates |
| `india/delivery/notifier.py` | Delivery pipeline orchestration |
| `tests/india/test_delivery.py` | Unit tests |
| `tests/india/test_delivery_integration.py` | Integration tests |

## Testing

- Unit tests: verify each formatter produces valid MarkdownV2
- Test message length: briefing with max data stays under 4096 or splits correctly
- Integration tests: DailyBriefing → formatter → send_alert → DB logging
