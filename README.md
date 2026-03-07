# ai-trading-bot

Two independent day trading intelligence systems in one monorepo — **India (NSE/BSE)** and **US (Robinhood)**.

Each system ingests market data, news, macro signals, and fundamentals → runs technical + sentiment + macro analysis → screens and ranks stocks → generates trade plans with risk-gated position sizing → delivers a morning Telegram briefing before market open.

## Systems

| System | Market | Telegram | Data Sources | Status |
|--------|--------|----------|-------------|--------|
| 🇮🇳 **India** | NSE/BSE (Nifty 200) | 9:00 AM IST | Broker API (free) + yfinance (free) | Building |
| 🇺🇸 **US** | NYSE/NASDAQ | ~9:00 AM ET | Polygon.io ($29/mo) + Robinhood | Planned |

Systems are fully independent — `india/` never imports from `us/` and vice versa. Shared infrastructure (Telegram, DB, news providers, LLM) lives in `shared/`.

## Architecture

```
Provider (raw API) → Transformer (normalize) → Ingestion (orchestrate)
    → Analysis (technical + macro + fundamental)
        → Strategy (screen → rank → trade plan)
            → Delivery (Telegram)
                → Review (journal + KPIs + weekly report)
```

Vendors are abstracted — swap a data provider by replacing one file. Downstream code stays unchanged.

## Project Structure

```
ai-trading-bot/
├── shared/              # Shared infrastructure
│   ├── utils/           # Config loader, structured logger
│   ├── db/              # SQLite (aiosqlite, raw SQL, no ORM)
│   ├── providers/       # yfinance, NewsAPI, GDELT, Reddit, LLM, etc.
│   ├── transformers/    # Raw → standard schema normalization
│   └── delivery/        # Telegram bot
├── india/               # India trading system
│   ├── config/          # Settings, risk params, data sources, CB calendar
│   ├── providers/       # Broker adapter (Dhan/Breeze/Kite), jugaad, NSE
│   ├── transformers/    # India-specific normalization
│   ├── ingestion/       # Overnight global, commodities, FII/DII, news, earnings
│   ├── analysis/        # Technical, fundamental, sentiment, correlation, risk
│   ├── strategy/        # Screener, ranker, trade plan generator
│   ├── delivery/        # India Telegram formatter
│   └── review/          # Trade journal, KPIs, weekly review, feedback loop
├── us/                  # US trading system (same structure, different data)
├── docs/                # Tech design doc, ADRs
└── tools/               # LLM prompts, debug scripts
```

## Tech Stack

- **Python 3.11** — asyncio throughout
- **httpx** + **tenacity** — async HTTP with retries and timeouts
- **pandas-ta** — technical indicators
- **SQLite** (aiosqlite) — raw parameterized SQL, WAL mode, 6 tables
- **loguru** — structured logging (every API call, fallback, trade decision)
- **python-telegram-bot v20+** — async Telegram delivery
- **APScheduler** — cron-based scheduling (IST / ET)
- **Docker** — single container deployment on VPS

## Setup

```bash
# Clone
git clone git@github.com:kulkarniachyut/ai-trading-bot.git
cd ai-trading-bot

# Create .env from template
cp .env.example .env
# Fill in API keys in .env

# Install dependencies
pip install -r requirements.txt
```

## Cost

| Component | Monthly |
|-----------|---------|
| India system (free data + LLM + Twitter) | ~$15-25 |
| US system (Polygon.io + LLM) | ~$34-39 |
| VPS (2-4GB RAM) | ~$6-12 |
| **Total** | **~$55-76** |

## Key Design Decisions

See `docs/decisions/` for full ADRs:

- **[ADR-001](docs/decisions/001-two-system-monorepo.md)** — Two independent systems in one monorepo
- **[ADR-002](docs/decisions/002-india-free-data-us-paid.md)** — India uses free data, US uses Polygon ($29/mo)
- **[ADR-003](docs/decisions/003-sqlite-no-orm.md)** — SQLite with raw SQL, no ORM

## Git Workflow

- `main` is protected — PR only, always deployable
- Feature branches: `feature/shared-NN-desc`, `feature/india-NN-desc`, `feature/us-NN-desc`
- Max 15 files per PR — small, focused, reviewable
- Commit format: `feat|fix|refactor|docs|test|chore: description`

## License

Private — not open source.
