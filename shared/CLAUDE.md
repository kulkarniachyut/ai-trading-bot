# shared/ — Shared Infrastructure

Code in this directory is used by BOTH the India and US trading systems.

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

## Rules
- Every module here must be system-agnostic. If it takes a `system` parameter, fine. If it hardcodes "india" or "us" logic, it doesn't belong here.
- Changes to shared/ affect both systems. Test both after changes.
