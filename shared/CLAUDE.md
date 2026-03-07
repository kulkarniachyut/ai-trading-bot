# shared/ — Shared Infrastructure

Code in this directory is used by BOTH the India and US trading systems.

## Built Modules

| Module | File | Status |
|--------|------|--------|
| Config loader | `utils/config.py` | ✅ Built — loads `.env` + YAML, returns frozen `AppConfig` |
| Structured logger | `utils/logger.py` | ✅ Built — loguru with `log_api_call`, `log_fallback`, `log_trade_decision`, `log_risk_check` |
| Database layer | `db/models.py` | ✅ Built — 6 tables, WAL mode, `init_db()`, `get_db()`, `log_ingestion()`, `prune_old_data()` |
| Telegram bot | `delivery/` | Pending — Step 2 |
| Providers | `providers/` | Pending — Step 3 (yfinance, NewsAPI, GDELT, Reddit, LLM) |
| Transformers | `transformers/` | Pending — Step 3 |

## What Belongs Here
- Vendor-agnostic provider wrappers (yfinance, newsapi, LLM clients)
- Utility modules (config loader, logger)
- Database layer (schema, queries)
- Telegram bot (shared bot, routes to different chat IDs per system)
- Transformers for data types used by both systems (e.g., news normalization)

## What Does NOT Belong Here
- India-specific logic (FII/DII, NSE scraping, Indian broker adapters)
- US-specific logic (Polygon, Robinhood, pre-market analysis)
- Strategy or analysis logic (these are system-specific)

## Key Imports
```python
from shared.utils.config import load_config, load_system_config, load_sources_config
from shared.utils.logger import get_logger, log_api_call, log_fallback, log_trade_decision, log_risk_check
from shared.db.models import init_db, get_db, log_ingestion
```

## Rules
- Every module here must be system-agnostic. If it takes a `system` parameter, fine. If it hardcodes "india" or "us" logic, it doesn't belong here.
- Changes to shared/ affect both systems. Test both after changes.
- ALL env vars through `shared/utils/config.py`. No inline `os.getenv()` anywhere.
- ALL logging through `shared/utils/logger.py`. No `print()`. No bare `loguru.logger`.
