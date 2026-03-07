# us/ — US Trading System (Robinhood)

Fully independent trading intelligence system for US equity markets.

## Market Info
- Exchanges: NYSE, NASDAQ
- Universe: TBD (S&P 500 subset or curated watchlist)
- Trading hours: 9:30 AM - 4:00 PM ET
- Pre-market: 4:00 AM - 9:30 AM ET (we monitor from ~8:30 AM)
- Currency: USD ($). All prices in $.
- Timezone: America/New_York (ET, UTC-5 / UTC-4 DST)

## Data Sources (US-specific)
- Real-time market data: Polygon.io ($29/mo) — required for pre-market + intraday
- Portfolio/positions: robin_stocks (unofficial Robinhood API)
- Historical OHLCV: Polygon.io (primary), yfinance (fallback)
- Earnings calendar: Polygon.io or yfinance
- Fed/economic data: FRED API (free)

## Key Signals (Priority Order)
1. Pre-market futures (S&P, Nasdaq, Dow)
2. Pre-market earnings releases (biggest daily catalyst)
3. VIX level and direction
4. Fed speeches / FOMC calendar
5. Economic data releases (CPI, jobs, GDP)
6. Technical setup on individual stocks
7. Sector rotation / momentum

## Rules
- NEVER import from `india/`. Only import from `shared/` and `us/`.
- All config in `us/config/`. Never share config with India system.
- Robinhood API is unofficial — handle auth carefully, expect breaking changes.
- US system will be built AFTER India system is live and stable.

## Status
Not yet built. Design pending. Will follow same architecture as India system.
