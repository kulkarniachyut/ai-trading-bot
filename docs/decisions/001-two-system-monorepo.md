# ADR-001: Two Independent Systems in One Monorepo

**Date:** 2026-03-07
**Status:** Accepted

## Context
We trade two markets — India (NSE/BSE) and US (NYSE/NASDAQ via Robinhood). Each market has fundamentally different data sources, timing, risk rules, and intelligence needs.

## Decision
Build both systems in a single git repository with clear directory separation (`india/`, `us/`, `shared/`). Each system is fully independent — never imports from the other. Shared infrastructure (Telegram, DB, providers like yfinance/newsapi) lives in `shared/`.

## Consequences
- **Pro:** Code sharing where it makes sense (providers, utils, telegram)
- **Pro:** Single deployment artifact (one Docker container runs both)
- **Pro:** Single repo to manage, one CI pipeline
- **Con:** Must be disciplined about never crossing india↔us boundaries
- **Con:** A shared/ bug could theoretically affect both systems

## Alternatives Considered
- Two separate repos: More isolation but duplicate code and harder to maintain shared providers.
- Monorepo with shared strategy layer: Rejected — strategies are too different between markets.
