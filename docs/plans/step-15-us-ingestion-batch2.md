# Step 15: US Ingestion — Geopolitics, Earnings, Fed Policy

**Status:** Planned
**Branch:** `feature/us-15-ingestion-batch2`

## Objective

Build the second batch of US ingestion modules: geopolitical news, earnings calendar, and Federal Reserve policy signals. Mirrors Step 6 architecture.

## Modules to Build

### 1. Geopolitics (`us/ingestion/geopolitics.py`)
- US-focused geopolitical news, trade policy, international relations
- Provider: NewsAPI + GDELT → RSS fallback
- LLM summarization for market impact

### 2. Earnings (`us/ingestion/earnings.py`)
- US earnings calendar, blackout list
- Provider: Polygon.io → yfinance fallback

### 3. Fed Policy (`us/ingestion/fed_policy.py`)
- FOMC decisions, Fed speeches, economic indicators
- Provider: FRED + RSS → NewsAPI fallback

## Files to Create

| File | Description |
|------|-------------|
| `us/ingestion/geopolitics.py` | US geopolitical signals |
| `us/ingestion/earnings.py` | US earnings calendar |
| `us/ingestion/fed_policy.py` | Federal Reserve policy |
| `us/transformers/geopolitics.py` | US geo normalizer |
| `us/transformers/earnings.py` | US earnings normalizer |
| `us/transformers/fed_policy.py` | Fed policy normalizer |
| `tests/us/test_ingestion_batch2.py` | Unit + integration tests |
