# Step 19: US Scheduler + main.py + E2E Testing

**Status:** Planned
**Branch:** `feature/us-19-scheduler-e2e`

## Objective

Build the US scheduler, entry point, and full end-to-end tests. Mirrors Steps 11-12 architecture.

## Modules to Build

### Scheduler (`us/scheduler.py`)
- APScheduler with ET timezone cron jobs
- US market schedule: 8:30 AM - 5:00 PM ET (Mon-Fri)
- US market holiday calendar awareness

### Main Entry (`us/main.py`)
```python
async def main():
    config = load_config()
    await init_db(config.db_path)
    await init_telegram(config)
    scheduler = create_scheduler(config)
    scheduler.start()
```

### E2E Tests
- Full US pipeline: ingestion → analysis → strategy → delivery → review
- Degraded mode: Polygon.io down → yfinance fallback
- No trade day scenario
- All external APIs mocked

## Files to Create

| File | Description |
|------|-------------|
| `us/scheduler.py` | US scheduler (ET timezone) |
| `us/main.py` | US entry point |
| `tests/us/test_scheduler.py` | Scheduler tests |
| `tests/us/test_e2e_pipeline.py` | Full E2E tests |
| `tests/us/conftest.py` | Shared US test fixtures |
