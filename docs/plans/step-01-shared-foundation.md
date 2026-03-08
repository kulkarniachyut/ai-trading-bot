# Step 1: Shared Foundation — Config, Logger, DB, India Configs

**Status:** ✅ Complete
**Branch:** `feature/shared-01-foundation`
**Merged to main:** Yes

## Objective

Build the core infrastructure that every other module depends on: configuration loading, structured logging, database setup, and India-specific config files.

## What Was Built

### Files Created

| File | Description |
|------|-------------|
| `shared/__init__.py` | Package marker |
| `shared/utils/__init__.py` | Package marker |
| `shared/utils/config.py` | Frozen dataclass config, `load_config()` from `.env` + YAML |
| `shared/utils/logger.py` | loguru wrapper: `get_logger()`, `log_api_call()`, `log_fallback()`, `log_trade_decision()`, `log_risk_check()` |
| `shared/db/__init__.py` | Package marker |
| `shared/db/models.py` | `init_db()`, `get_db()`, `log_ingestion()`, `prune_old_data()`, full DDL for 6 tables |
| `india/__init__.py` | Package marker |
| `india/config/settings.yaml` | India system settings (watchlist, timing, thresholds) |
| `india/config/risk_params.yaml` | Non-negotiable risk rules (SL limits, position sizing, VIX gates) |
| `india/config/sources.yaml` | Data source configuration and fallback chains |
| `india/config/central_bank_calendar.json` | RBI MPC and key central bank event dates |
| `.env.example` | Template with all required env vars |
| `requirements.txt` | All Python dependencies |
| `CLAUDE.md` | Project constitution |

### Key Design Decisions

1. **Config pattern:** Frozen dataclasses (`AppConfig`, `TelegramConfig`, `IndiaConfig`, `USConfig`, `RiskConfig`). `load_config()` called once at startup.
2. **Logger pattern:** loguru with structured helpers. Every module calls `get_logger(__name__)`.
3. **DB pattern:** `init_db()` creates tables idempotently, `get_db()` context manager for connections. Raw SQL with parameterized queries.
4. **Six tables:** `trades`, `signals`, `daily_kpis`, `weight_history`, `ingestion_log`, `alerts_sent`.

## Testing

- Unit tests for config loading, logger formatting, DB operations
- Integration tests: config → DB init → operations → verification
