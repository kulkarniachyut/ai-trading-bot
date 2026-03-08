# Step 14: US Ingestion — Markets, Pre-Market, Equities

**Status:** Planned
**Branch:** `feature/us-14-ingestion-batch1`

## Objective

Build the first batch of US ingestion modules: market data, pre-market data, and equity OHLCV. Mirrors Steps 5 architecture.

## Modules to Build

### 1. US Markets (`us/ingestion/us_markets.py`)
- S&P 500, DJIA, NASDAQ, Russell 2000
- VIX, Treasury yields, DXY
- Provider: Polygon.io → yfinance fallback

### 2. Pre-Market (`us/ingestion/pre_market.py`)
- Pre-market movers, gap analysis
- Futures data
- Provider: Polygon.io (real-time required)

### 3. US Equities (`us/ingestion/us_equities.py`)
- OHLCV for watchlist stocks (200-day history)
- Real-time quotes during market hours
- Provider: Polygon.io → yfinance fallback

## Files to Create

| File | Description |
|------|-------------|
| `us/ingestion/__init__.py` | Package marker |
| `us/ingestion/us_markets.py` | US market indices |
| `us/ingestion/pre_market.py` | Pre-market data |
| `us/ingestion/us_equities.py` | US equity OHLCV |
| `us/transformers/__init__.py` | Package marker |
| `us/transformers/market.py` | US market normalizer |
| `us/transformers/equities.py` | US equity normalizer |
| `tests/us/test_ingestion_batch1.py` | Unit + integration tests |
