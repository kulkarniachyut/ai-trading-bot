# Step 10: India Review — Journal, KPIs, Weekly Review

**Status:** Pending
**Branch:** `feature/india-10-review`

## Objective

Build the trade journaling, KPI computation, and weekly review system for the India system.

## Modules to Build

### 1. Trade Journal (`india/review/journal.py`)
```python
async def log_trade(trade: TradePlan, status: str) -> int  # Returns trade ID
async def update_trade(trade_id: int, **updates) -> None
async def close_trade(trade_id: int, exit_price: float, exit_reason: str) -> None
```
- Every trade recommendation logged to `trades` table
- Status tracking: planned → entered → partial_exit → closed / cancelled / skipped
- Exit reasons: target_1, target_2, stop_loss, trailing_sl, eod_exit, manual, time_expiry

### 2. KPI Tracker (`india/review/kpi_tracker.py`)
```python
async def compute_daily_kpis(system: str, date: str) -> dict
async def compute_weekly_kpis(system: str, week_start: str) -> dict
async def compute_rolling_kpis(system: str, weeks: int = 4) -> dict
```
- Daily: trades_taken, wins, losses, net_pnl, net_pnl_pct, win_rate, profit_factor
- Weekly: aggregated daily KPIs + max_drawdown
- Rolling: 4-week trends, consistency metrics

### 3. Weekly Review (`india/review/weekly_review.py`)
```python
async def generate_weekly_review(system: str) -> str  # Formatted message
```
- Performance report: week's trades, P&L, win rate, best/worst trade
- Sent via Telegram every Saturday 10:00 AM IST

### 4. Feedback Loop (`india/review/feedback.py`)
```python
async def auto_tune_weights(system: str) -> dict  # Returns new weights
```
- Analyze signal accuracy over past 4 weeks
- Adjust composite weights (tech/macro/fund) within safe bounds
- Log weight changes to `weight_history` table
- Safety checks: weights can't change more than 10% per week

## Files to Create

| File | Description |
|------|-------------|
| `india/review/__init__.py` | Package marker |
| `india/review/journal.py` | Trade journaling |
| `india/review/kpi_tracker.py` | KPI computation |
| `india/review/weekly_review.py` | Weekly performance report |
| `india/review/feedback.py` | Auto-tuning feedback loop |
| `tests/india/test_review.py` | Unit tests |
| `tests/india/test_review_integration.py` | Integration tests |

## Testing

- Unit tests: KPI math, weight adjustment bounds, status transitions
- Integration tests: log trade → close trade → compute KPIs → verify DB
- Test weight safety: ensure bounds respected, changes logged
