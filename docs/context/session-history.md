# Session History — Build Context for New Sessions

This file captures the build history and key decisions. Read this at the start of any new session to pick up where we left off.

---

## Current State

**Last completed step:** Step 3 (Shared Providers + Transformers)
**Next step:** Step 4 (India Broker Adapter)
**Active branch:** `feature/shared-03-providers` (pending merge to main)

## Completed Steps

### Step 1: Shared Foundation (✅ Merged to main)
- **Branch:** `feature/shared-01-foundation`
- **What was built:** config loader (frozen dataclasses), loguru logger, SQLite DB (aiosqlite), India config files (settings, risk params, sources, central bank calendar)
- **Key patterns established:**
  - `load_config()` → `AppConfig` frozen dataclass, called once at startup
  - `get_logger(__name__)` → loguru with structured helpers
  - `init_db()` → creates 6 tables idempotently, `get_db()` context manager
  - All env vars through `shared/utils/config.py` only

### Step 3: Shared Providers + Transformers (✅ Complete, pending PR merge)
- **Branch:** `feature/shared-03-providers`
- **Commit:** `0f79f87`
- **What was built:**
  - 7 providers: yfinance, newsapi, gdelt, reddit, llm (Anthropic), fred, rss
  - 3 transformer files: `market_transformer.py`, `news_transformer.py`, `base.py` (dataclasses)
  - Output dataclasses: `MarketSnapshot`, `CommoditySnapshot`, `GeoSignal`, `IngestionResult`
- **Tests:** 57 new (40 unit + 17 integration), 103 total passing
- **Key patterns established:**
  - `ProviderResult` uniform return type — `success, data, provider, latency_ms, error, metadata`
  - `make_error_result()` helper for exception handling
  - yfinance/PRAW/feedparser run sync in `run_in_executor` — no async API
  - `MarketTransformer` handles both market indices + commodities; lookup maps drive display name + affected sectors
  - `NewsTransformer` dispatches by `source` string — add new sources without changing interface
  - Sentiment inferred from keyword matching (no LLM needed at transformer layer)
- **Config gotchas:**
  - `LLMConfig` has no `llm_model` field — model hardcoded in provider
  - `AppConfig` requires `risk: RiskConfig` + `root_dir: Path` fields
  - `IndiaBrokerConfig` uses `broker` not `broker_name`, `api_secret` not `client_id`
- **Lessons:**
  - Read config dataclass fields before writing tests — field names differ from what you'd guess
  - feedparser never raises — check `bozo` flag + empty entries
  - Python 3.14 pytest-asyncio deprecation warnings are harmless

### Step 2: Shared Telegram Bot (✅ Complete, pending PR merge)
- **Branch:** `feature/shared-02-telegram`
- **Commit:** `733727b`
- **What was built:** `shared/delivery/telegram.py` — init/shutdown singleton, send_message with auto-split, send_alert with system routing, SHA-256 content dedup, DB logging to `alerts_sent`
- **Tests:** 52 total (41 unit + 11 integration), all passing
- **Key patterns established:**
  - Lazy-init singleton: `init_telegram(config)` → `send_alert(system, alert_type, text)`
  - Message splitting: paragraph → line → hard cut at 4096 chars
  - Dedup: 60-min window, in-memory SHA-256 hash
  - Retry: tenacity on `TimedOut` only, 2 attempts

## Key Technical Decisions

1. **Singleton pattern for shared modules** — `init_telegram` / `init_db` called once at startup, module-level state. Consistent across shared layer.
2. **Integration tests required for every step** — not just unit tests. Must wire up real config, real DB, mock only external APIs.
3. **pytest-asyncio >= 0.25** — needed for `asyncio_mode = "auto"` and `@pytest_asyncio.fixture`
4. **pyproject.toml** — contains `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`
5. **DB logging failures swallowed** — never crash the pipeline due to audit logging failure

## Errors Encountered and Solutions

| Error | Solution |
|-------|----------|
| PEP 668 blocks pip install on system Python 3.14 | Created `.venv` with `python3 -m venv .venv` |
| `pandas-ta==0.3.14b` not available | Install only step-needed deps, not full requirements.txt |
| `pytest-asyncio==1.3.0` too old for auto mode | Upgrade to `pytest-asyncio==0.25.3` |
| `@pytest.fixture` doesn't work for async fixtures | Use `@pytest_asyncio.fixture` instead |

## File Structure Reference

```
ai-trading-bot/
├── CLAUDE.md                           # Project constitution
├── pyproject.toml                      # pytest config
├── requirements.txt                    # Python dependencies
├── docs/
│   ├── tech-design-v1.md               # Full technical design
│   ├── plans/                          # Step-by-step build plans
│   │   ├── step-01-shared-foundation.md
│   │   ├── step-02-shared-telegram.md
│   │   └── ... (steps 03-20)
│   └── context/
│       └── session-history.md          # THIS FILE
├── shared/
│   ├── utils/
│   │   ├── config.py                   # load_config() → AppConfig
│   │   └── logger.py                   # get_logger(), log_api_call(), etc.
│   ├── db/
│   │   └── models.py                   # init_db(), get_db(), 6 tables
│   ├── delivery/
│   │   ├── CLAUDE.md                   # Delivery module rules
│   │   └── telegram.py                 # init_telegram(), send_alert(), etc.
│   ├── providers/                      # (Step 3 — pending)
│   └── transformers/                   # (Step 3 — pending)
├── india/
│   ├── config/
│   │   ├── settings.yaml               # Watchlist, timing, thresholds
│   │   ├── risk_params.yaml            # Non-negotiable risk rules
│   │   ├── sources.yaml                # Data source fallback chains
│   │   └── central_bank_calendar.json  # RBI MPC dates
│   ├── analysis/                       # (Step 7 — pending)
│   ├── delivery/                       # (Step 9 — pending)
│   ├── ingestion/                      # (Steps 5-6 — pending)
│   ├── providers/broker/               # (Step 4 — pending)
│   ├── review/                         # (Step 10 — pending)
│   ├── strategy/                       # (Step 8 — pending)
│   └── transformers/                   # (Steps 5-6 — pending)
├── us/                                 # (Steps 13-19 — planned)
└── tests/
    ├── shared/
    │   ├── test_telegram.py            # 41 unit tests
    │   └── test_telegram_integration.py # 11 integration tests
    └── india/                          # (Steps 4-12 — pending)
```

## How to Continue

1. Read this file + `CLAUDE.md` + the relevant step plan in `docs/plans/`
2. Create a feature branch from `main` following naming convention
3. Build the step, write unit + integration tests
4. Run `pytest tests/ -v` — all tests must pass
5. Commit and create PR
6. Update this file with the new step's status and decisions
