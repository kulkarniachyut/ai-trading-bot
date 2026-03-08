# Step 16: US Analysis — Technical, Fundamental, Macro, Risk

**Status:** Planned
**Branch:** `feature/us-16-analysis`

## Objective

Build the US analysis layer. Mirrors Step 7 architecture with US-specific adjustments.

## Modules to Build

### 1. Technical Analysis (`us/analysis/technical.py`)
- Same indicator suite as India (pandas-ta)
- Adjusted for US market behavior (higher volume, different volatility profile)

### 2. Fundamental Analysis (`us/analysis/fundamental.py`)
- US-specific fundamentals: P/E, P/S, earnings growth, insider activity
- Data from Polygon.io or yfinance

### 3. Macro Analysis (`us/analysis/macro.py`)
- Fed policy impact, Treasury yields, DXY, sector rotation
- No FII/DII equivalent — use institutional flow proxies

### 4. Risk Engine (`us/analysis/risk.py`)
- US risk params from `us/config/risk_params.yaml`
- Prices in USD, position sizing in USD
- VIX thresholds adjusted for US market

## Files to Create

| File | Description |
|------|-------------|
| `us/analysis/__init__.py` | Package marker |
| `us/analysis/technical.py` | US technical scoring |
| `us/analysis/fundamental.py` | US fundamental scoring |
| `us/analysis/macro.py` | US macro scoring |
| `us/analysis/risk.py` | US risk validation |
| `tests/us/test_analysis.py` | Unit + integration tests |
