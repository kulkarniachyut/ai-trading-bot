# Step 6: India Ingestion — Geopolitics, Earnings, Central Banks

**Status:** Pending
**Branch:** `feature/india-06-ingestion-batch2`

## Objective

Build the second batch of India ingestion modules: geopolitical news, earnings calendar, and central bank policy signals.

## Modules to Build

### 1. Geopolitics (`india/ingestion/geopolitics.py`)
- Fetches: India-relevant geopolitical news, defense developments, trade policy, border situations
- Provider chain: NewsAPI + GDELT → RSS feeds only
- LLM summarization: headline → 1-line market impact summary
- Output: `list[GeoSignal]`
- Fallback: reduced signal set

### 2. Earnings Calendar (`india/ingestion/earnings.py`)
- Fetches: stocks reporting in next 2 days (blackout list), upcoming domestic earnings, international earnings with Indian proxies
- Provider chain: Trendlyne scrape → MoneyControl → yfinance calendar
- Output: `EarningsInfo`
- Fallback: empty blackout list (conservative — don't trade uncertain stocks)

### 3. Central Banks (`india/ingestion/central_banks.py`)
- Fetches: RBI MPC decisions, SEBI circulars, GOI policy, Fed impact, ECB impact
- Provider chain: FRED + RSS → NewsAPI search
- Uses `india/config/central_bank_calendar.json` for scheduled events
- LLM for tone detection (hawkish/dovish/neutral)
- Output: `list[CentralBankEvent]`
- Fallback: reduced policy data

## Transformers

| File | Input | Output |
|------|-------|--------|
| `india/transformers/geopolitics.py` | NewsAPI/GDELT raw | `list[GeoSignal]` |
| `india/transformers/earnings.py` | Scrape/API raw | `EarningsInfo` |
| `india/transformers/central_banks.py` | FRED/RSS raw | `list[CentralBankEvent]` |

## Key Constraints

- LLM calls for summarization must have 15s timeout + retry
- Earnings blackout is conservative: if data unavailable, block trading uncertain stocks
- Central bank calendar is pre-loaded + augmented by live feeds
- All geopolitical signals scored by urgency (1-5) and sentiment

## Files to Create

| File | Description |
|------|-------------|
| `india/ingestion/geopolitics.py` | Geopolitical news aggregation |
| `india/ingestion/earnings.py` | Earnings calendar + blackout list |
| `india/ingestion/central_banks.py` | Central bank policy signals |
| `india/transformers/geopolitics.py` | GeoSignal normalizer |
| `india/transformers/earnings.py` | EarningsInfo normalizer |
| `india/transformers/central_banks.py` | CentralBankEvent normalizer |
| `tests/india/test_ingestion_batch2.py` | Unit tests |
| `tests/india/test_ingestion_batch2_integration.py` | Integration tests |

## Testing

- Unit tests: mock all provider responses, verify output schema
- Integration tests: full pipeline with mocked APIs
- Test LLM fallback: LLM unavailable → use raw headline without summary
- Test blackout list: verify stocks near earnings get excluded
