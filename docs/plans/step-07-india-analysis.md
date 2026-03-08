# Step 7: India Analysis — Technical, Fundamental, Macro, Risk

**Status:** Pending
**Branch:** `feature/india-07-analysis`

## Objective

Build the analysis layer that scores stocks across technical, fundamental, and macro dimensions, plus the risk validation engine.

## Modules to Build

### 1. Technical Analysis (`india/analysis/technical.py`)
```python
async def analyze_technicals(equities: list[EquityOHLCV]) -> list[TechnicalSignal]
```
- Uses pandas-ta for indicator computation
- Indicators: RSI, MACD, Bollinger Bands, VWAP, ATR, OBV, EMA crossovers, support/resistance
- Scoring: 0-100 based on signal confluence
- Direction: LONG / SHORT / NEUTRAL
- ATR used downstream for SL/TP calculation

### 2. Fundamental Analysis (`india/analysis/fundamental.py`)
```python
async def analyze_fundamentals(symbols: list[str]) -> list[FundamentalScore]
```
- Quick-check metrics: P/E ratio vs sector, promoter holding changes, D/E ratio, ROE
- Data from yfinance fundamentals
- Scoring: 0-100

### 3. Macro Analysis (`india/analysis/macro.py`)
```python
def compute_macro_scores(flows, commodities, geo_signals, central_bank, symbols) -> list[MacroScore]
```
- Combines FII/DII flow direction, sector tailwinds/headwinds from commodities, geopolitical risk, central bank tone
- Per-stock scoring based on sector mapping

### 4. Risk Engine (`india/analysis/risk.py`)
```python
def validate_trade(plan, current_positions, india_vix, day_of_week) -> tuple[bool, list[str]]
```
- Rules from `india/config/risk_params.yaml` (NON-NEGOTIABLE):
  - R:R ratio >= 2.0
  - SL <= 3% from entry
  - Max concurrent trades: 3
  - VIX gate: no new trades if VIX > threshold
  - Sector concentration: max 2 trades in same sector
  - Friday rule: no new positions on Friday
  - Max loss per trade: 2% of capital
- Every rule evaluation logged: rule_name, value, threshold, pass/fail

## Key Constraints

- All thresholds and weights from `india/config/risk_params.yaml` and `india/config/settings.yaml`
- No magic numbers in code
- Risk params are NON-NEGOTIABLE — code cannot override them
- Prices in INR, percentages as decimals (0.02 not 2)
- Log every trade decision: symbol, score, direction, accepted/rejected, reasons

## Files to Create

| File | Description |
|------|-------------|
| `india/analysis/__init__.py` | Package marker |
| `india/analysis/technical.py` | Technical indicator scoring |
| `india/analysis/fundamental.py` | Fundamental quick-check |
| `india/analysis/macro.py` | Macro environment scoring |
| `india/analysis/risk.py` | Risk gate validation |
| `tests/india/test_analysis.py` | Unit tests |
| `tests/india/test_analysis_integration.py` | Integration tests |

## Testing

- Unit tests: test each scoring function with known inputs → expected scores
- Test risk engine: each rule individually + combined scenarios
- Integration tests: ingestion output → analysis → scored output pipeline
- Test edge cases: VIX exactly at threshold, Friday boundary, sector limit hit
