
In all interactions and commit messages, be extremely concise and sacrifice grammar for the sake of concision

# Project: ai-trading-bot

Two independent day trading intelligence systems (India NSE/BSE + US Robinhood) in one monorepo.

**Stack:** Python 3.11, asyncio, httpx, pandas-ta, SQLite (aiosqlite), Telegram (python-telegram-bot v20+)
**Deploy:** Docker on VPS

## Key References

| Document | Path | Purpose |
|----------|------|---------|
| Tech Design | `docs/tech-design-v1.md` | Full HLD, system design, DB schema, data models, API contracts |
| Step Plans | `docs/plans/step-NN-*.md` | Detailed implementation plan for each build step |
| Session History | `docs/context/session-history.md` | Build context for new sessions — read this first to pick up where we left off |

## Build Progress

| Step | Scope | Plan | Status |
|------|-------|------|--------|
| 1 | Shared foundation — config, logger, DB, India configs | `docs/plans/step-01-shared-foundation.md` | ✅ Done |
| 2 | Shared Telegram bot | `docs/plans/step-02-shared-telegram.md` | ✅ Done |
| 3 | Shared providers (yfinance, NewsAPI, GDELT, Reddit, LLM) | `docs/plans/step-03-shared-providers.md` | Pending |
| 4 | India broker adapter + config | `docs/plans/step-04-india-broker.md` | Pending |
| 5 | India ingestion — overnight, commodities, FII/DII | `docs/plans/step-05-india-ingestion-overnight.md` | Pending |
| 6 | India ingestion — geopolitics, earnings, central banks | `docs/plans/step-06-india-ingestion-intelligence.md` | Pending |
| 7 | India analysis — technical, fundamental, macro, risk | `docs/plans/step-07-india-analysis.md` | Pending |
| 8 | India strategy — screener, ranker, trade plan | `docs/plans/step-08-india-strategy.md` | Pending |
| 9 | India delivery — Telegram formatter + pipeline | `docs/plans/step-09-india-delivery.md` | Pending |
| 10 | India review — journal, KPIs, weekly review | `docs/plans/step-10-india-review.md` | Pending |
| 11 | India scheduler + main.py | `docs/plans/step-11-india-scheduler.md` | Pending |
| 12 | India end-to-end testing | `docs/plans/step-12-india-e2e-testing.md` | Pending |
| 13 | US broker adapter + providers (Polygon, Robinhood) | `docs/plans/step-13-us-broker-providers.md` | Planned |
| 14 | US ingestion — markets, pre-market, equities | `docs/plans/step-14-us-ingestion-batch1.md` | Planned |
| 15 | US ingestion — geopolitics, earnings, Fed policy | `docs/plans/step-15-us-ingestion-batch2.md` | Planned |
| 16 | US analysis — technical, fundamental, macro, risk | `docs/plans/step-16-us-analysis.md` | Planned |
| 17 | US strategy — screener, ranker, trade plan | `docs/plans/step-17-us-strategy.md` | Planned |
| 18 | US delivery + review | `docs/plans/step-18-us-delivery-review.md` | Planned |
| 19 | US scheduler + main.py + E2E testing | `docs/plans/step-19-us-scheduler-e2e.md` | Planned |
| 20 | Docker deployment | `docs/plans/step-20-docker-deployment.md` | Planned |

## Hard Rules

- ALL env vars through `shared/utils/config.py`. No inline `os.getenv()` anywhere.
- DB: raw SQL with parameterized inputs via aiosqlite. No ORM. Never use string formatting for queries.
- Every async HTTP call MUST have a timeout (max 15s) + tenacity retry.
- NEVER use `datetime.now()`. Always timezone-aware: `datetime.now(tz=ZoneInfo("Asia/Kolkata"))` or UTC.
- Risk params loaded from `{system}/config/risk_params.yaml` are NON-NEGOTIABLE in code.
- All prices in ₹ (INR) for India, $ (USD) for US. Percentages as decimals (0.02 not 2).
- Logging: structured via loguru. No `print()`. Log every API call, fallback, and decision.
- No wildcard imports. Explicit only.
- No magic numbers in code. All thresholds, weights, limits in config YAML.

## Vendor Abstraction

- External data flows: Provider (raw API response) → Transformer (normalize) → Standard Output (typed dataclass).
- Swap vendor = swap one provider file. Transformers and downstream are unchanged.
- Providers ONLY return raw data. No business logic.
- Transformers ONLY normalize. No API calls.

## Two-System Independence

- `india/` and `us/` are fully independent. NEVER import across systems.
- Shared code lives in `shared/`. Both systems import from `shared/`.
- Each system has its own config, strategy, scheduler, main.py.
- Breaking `india/` must never break `us/` and vice versa.

## Git Workflow

- NEVER push directly to `main`. Always feature branch → PR → review → merge.
- Each PR = one logical build step. Max 15 files.
- Commit messages: `feat|fix|refactor|docs|test|chore: short description`
- Branch naming: `feature/shared-NN-desc`, `feature/india-NN-desc`, `feature/us-NN-desc`

## Logging Requirements

- Every external API call: provider name, latency_ms, status, data_points returned.
- Every fallback activation: from_provider, to_provider, reason.
- Every trade decision: symbol, score, direction, accepted/rejected, rejection reasons.
- Every risk rule evaluation: rule_name, value, threshold, pass/fail.
- Critical failures → also send Telegram alert.

## Testing

- Test files mirror source: `india/ingestion/fii_dii.py` → `tests/india/test_fii_dii.py`
- Each module must be testable standalone (no dependency on full pipeline running).
- Every step/commit MUST be tested end-to-end before marking complete. Unit tests alone are insufficient — write integration tests that exercise the full path from config → DB init → module init → operation → DB verification.
- Integration tests required: every step must have tests that wire up real components (config loader, DB, module under test) end-to-end with only external APIs mocked.
- No step is marked complete until `pytest tests/` passes with all unit AND integration tests green.

## New Session Startup

When starting a new session on this project:
1. Read this `CLAUDE.md` file for rules and current build progress
2. Read `docs/context/session-history.md` for detailed build context, decisions, and error history
3. Read the specific step plan from `docs/plans/step-NN-*.md` for the step you're working on
4. Check `git log --oneline -5` and `git branch` to understand the current branch state

## Memory & Evolution

- Update this file when encountering real issues — rules come from mistakes, not speculation.
- After each build step, reflect and add relevant rules if something went wrong.
- After each step, update `docs/context/session-history.md` with the step's status, decisions, and errors.
- After each step, update the step's plan file in `docs/plans/` with status and lessons learned.
- The constitution compounds over time. That's the point.
