# Step 11: India Scheduler + main.py

**Status:** Pending
**Branch:** `feature/india-11-scheduler`

## Objective

Build the India system scheduler (APScheduler) and main entry point that orchestrates the entire daily pipeline.

## Modules to Build

### 1. Scheduler (`india/scheduler.py`)
- APScheduler with IST timezone cron jobs
- Full daily schedule (Mon-Fri):
  - 08:45 IST — `run_all_ingestion()`
  - 08:55 IST — `run_analysis_and_strategy()`
  - 09:00 IST — `send_morning_briefing()`
  - 09:05 IST — `send_trade_alerts()`
  - 09:25 IST — `send_prep_alerts()`
  - 09:30-15:25 IST — `monitor_positions()` (every 5 min)
  - 15:15 IST — `send_exit_reminders()`
  - 18:00 IST — `log_daily_trades()`
- Weekly schedule:
  - Saturday 10:00 IST — `generate_weekly_review()`
  - Saturday 10:30 IST — `run_feedback_loop()`
  - Sunday 02:00 IST — `run_maintenance()` (prune logs, backup DB)
- NSE holiday calendar awareness — skip trading days on holidays

### 2. Main Entry (`india/main.py`)
```python
async def main():
    config = load_config()
    await init_db(config.db_path)
    await init_telegram(config)
    scheduler = create_scheduler(config)
    scheduler.start()
    # Keep alive
```

## Key Constraints

- All times in IST (Asia/Kolkata timezone)
- NSE holiday calendar check before scheduling trading-day jobs
- Each job wrapped in try/except — one job failure doesn't crash the scheduler
- Every job start/end logged with duration_ms
- Critical job failures send Telegram alerts

## Files to Create

| File | Description |
|------|-------------|
| `india/scheduler.py` | APScheduler setup with all cron jobs |
| `india/main.py` | Entry point for India system |
| `tests/india/test_scheduler.py` | Unit tests |
| `tests/india/test_scheduler_integration.py` | Integration tests |

## Testing

- Unit tests: verify job schedule times, holiday skipping logic
- Integration tests: scheduler init → mock job execution → verify logging
- Test graceful shutdown: scheduler stops, telegram shuts down, DB closes
