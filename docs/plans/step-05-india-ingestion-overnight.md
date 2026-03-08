# Step 5: India Ingestion — Overnight, Commodities, FII/DII

**Status:** Pending
**Branch:** `feature/india-05-ingestion-batch1`

## Objective

Build the first batch of India ingestion modules that run at 8:45 AM IST pre-market. These fetch overnight global markets, commodity prices, and institutional fund flows.

## Modules to Build

### 1. Overnight Global (`india/ingestion/overnight_global.py`)
- Fetches: US close (S&P 500, DJIA, NASDAQ), Asia morning (Nikkei, Hang Seng, SGX Nifty), Europe close, Crude/Gold, USD/INR, US 10Y/DXY
- Provider: yfinance (free)
- Output: `list[MarketSnapshot]`
- Fallback: skip (non-critical)

### 2. Commodities (`india/ingestion/commodities.py`)
- Fetches: Brent Crude, Gold, Silver, Copper, Natural Gas
- Maps commodity moves to affected Indian sectors (OMC, Aviation, Paints, Jewellery, etc.)
- Provider: yfinance (free)
- Output: `list[CommoditySnapshot]`
- Fallback: skip (non-critical)

### 3. FII/DII Flows (`india/ingestion/fii_dii.py`)
- Fetches: FII/DII daily buy/sell/net, 5-day and 10-day trends
- Provider chain: NSE API → jugaad-data → MoneyControl scrape
- Output: `FlowData`
- Fallback: ALERT — this is critical data

## Transformers

| File | Input | Output |
|------|-------|--------|
| `india/transformers/market.py` | yfinance raw dict | `list[MarketSnapshot]` |
| `india/transformers/commodity.py` | yfinance raw dict | `list[CommoditySnapshot]` |
| `india/transformers/flows.py` | NSE/jugaad raw dict | `FlowData` |

## Ingestion Contract

```python
async def fetch_and_process() -> IngestionResult:
    # 1. Call provider(s) with fallback chain
    # 2. Pass raw data through transformer
    # 3. Log to ingestion_log table
    # 4. Return standardized output
```

## Key Constraints

- Transformers ONLY normalize — no API calls
- Providers ONLY return raw data — no business logic
- Every ingestion logged to `ingestion_log` table
- Fallback activation logged: from_provider, to_provider, reason
- FII/DII failure triggers Telegram alert (critical data)

## Files to Create

| File | Description |
|------|-------------|
| `india/ingestion/__init__.py` | Package marker |
| `india/ingestion/overnight_global.py` | Global market overnight data |
| `india/ingestion/commodities.py` | Commodity prices + sector mapping |
| `india/ingestion/fii_dii.py` | FII/DII institutional flows |
| `india/transformers/__init__.py` | Package marker |
| `india/transformers/market.py` | MarketSnapshot normalizer |
| `india/transformers/commodity.py` | CommoditySnapshot normalizer |
| `india/transformers/flows.py` | FlowData normalizer |
| `tests/india/test_ingestion_batch1.py` | Unit tests |
| `tests/india/test_ingestion_batch1_integration.py` | Integration tests |

## Testing

- Unit tests: mock provider responses, verify transformer output matches dataclass schema
- Integration tests: config → DB → provider (mocked) → transformer → ingestion_log verification
- Test fallback chains: primary fails → fallback activates → data still flows
