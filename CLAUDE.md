# Project: ai-trading-bot

Two independent day trading intelligence systems (India NSE/BSE + US Robinhood) in one monorepo.

**Stack:** Python 3.11, asyncio, httpx, pandas-ta, SQLite (aiosqlite), Telegram (python-telegram-bot v20+)
**Deploy:** Docker on VPS

## Tech Design

Read `docs/tech-design-v1.md` for full HLD, system design, DB schema, data models, API contracts.

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

## Memory & Evolution

- Update this file when encountering real issues — rules come from mistakes, not speculation.
- After each build step, reflect and add relevant rules if something went wrong.
- The constitution compounds over time. That's the point.
