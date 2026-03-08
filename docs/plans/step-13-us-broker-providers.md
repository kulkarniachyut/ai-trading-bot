# Step 13: US Broker Adapter + Providers (Polygon, Robinhood)

**Status:** Planned
**Branch:** `feature/us-13-broker-providers`

## Objective

Build US-specific broker adapter (Robinhood) and real-time data provider (Polygon.io). Mirrors Step 4 architecture for the US market.

## Modules to Build

### 1. Polygon Provider (`us/providers/polygon_provider.py`)
- Real-time quotes, OHLCV, pre-market data
- REST API with websocket capability (future)
- $29/mo subscription
- Output: `ProviderResult`

### 2. Robinhood Adapter (`us/providers/robinhood_adapter.py`)
- Portfolio positions, order status
- Unofficial API (robin_stocks library)
- MFA/TOTP handling
- Output: `ProviderResult`

### 3. US Config Files
- `us/config/settings.yaml` — US watchlist, timing (ET), thresholds
- `us/config/risk_params.yaml` — US risk rules (position sizing in USD)
- `us/config/sources.yaml` — US data source fallback chains

## Fallback Chains
| Module | Primary | Fallback 1 |
|--------|---------|------------|
| US Markets | Polygon.io | yfinance |
| Pre-Market | Polygon.io | — |
| US Equities | Polygon.io | yfinance |

## Files to Create

| File | Description |
|------|-------------|
| `us/providers/__init__.py` | Package marker |
| `us/providers/polygon_provider.py` | Polygon.io API client |
| `us/providers/robinhood_adapter.py` | Robinhood API adapter |
| `us/config/settings.yaml` | US system settings |
| `us/config/risk_params.yaml` | US risk parameters |
| `us/config/sources.yaml` | US data sources |
| `tests/us/test_providers.py` | Unit tests |
| `tests/us/test_providers_integration.py` | Integration tests |
