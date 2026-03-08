# Step 18: US Delivery + Review

**Status:** Planned
**Branch:** `feature/us-18-delivery-review`

## Objective

Build the US delivery (Telegram formatting) and review (journal, KPIs) modules. Mirrors Steps 9-10 architecture.

## Modules to Build

### Delivery
- `us/delivery/formatter.py` — US-specific message templates (prices in $)
- `us/delivery/notifier.py` — US delivery pipeline (ET timezone)

### Review
- `us/review/journal.py` — US trade journaling
- `us/review/kpi_tracker.py` — US KPI computation
- `us/review/weekly_review.py` — US weekly report (Saturday 10:00 AM ET)
- `us/review/feedback.py` — US weight auto-tuning

## Files to Create

| File | Description |
|------|-------------|
| `us/delivery/__init__.py` | Package marker |
| `us/delivery/formatter.py` | US message templates |
| `us/delivery/notifier.py` | US delivery pipeline |
| `us/review/__init__.py` | Package marker |
| `us/review/journal.py` | US trade journal |
| `us/review/kpi_tracker.py` | US KPI tracker |
| `us/review/weekly_review.py` | US weekly review |
| `us/review/feedback.py` | US feedback loop |
| `tests/us/test_delivery.py` | Unit + integration tests |
| `tests/us/test_review.py` | Unit + integration tests |
