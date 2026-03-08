# Step 8: India Strategy — Screener, Ranker, Trade Plan

**Status:** Pending
**Branch:** `feature/india-08-strategy`

## Objective

Build the strategy layer that filters the Nifty 200 universe, ranks candidates, and generates actionable trade plans.

## Modules to Build

### 1. Screener (`india/strategy/screener.py`)
```python
def screen_universe(equities: list[EquityOHLCV], earnings: EarningsInfo) -> list[str]
```
- Nifty 200 → ~30-40 candidates
- Filters: minimum volume, not in F&O ban list, not in earnings blackout, minimum market cap
- All thresholds from `india/config/settings.yaml`

### 2. Ranker (`india/strategy/ranker.py`)
```python
def rank_stocks(technicals, macros, fundamentals, weights) -> list[CompositeScore]
```
- Composite = 0.55 * technical + 0.30 * macro + 0.15 * fundamental
- Weights from config (auto-tuned weekly)
- Filter: composite > 70
- Output: top 2-3 picks sorted by composite

### 3. Trade Plan (`india/strategy/trade_plan.py`)
```python
def generate_plan(scored: CompositeScore, technical: TechnicalSignal, capital: float) -> TradePlan | None
```
- Entry: current price or key level
- SL: based on ATR (from technical analysis)
- TP: R:R ratio * risk distance
- Position size: max risk / SL distance
- Risk gate: final validation (calls risk engine)
- Returns None if risk rules reject the trade

## Key Constraints

- Weights from config YAML, never hardcoded
- "NO TRADE TODAY" is a valid output — system does not force trades
- Position sizing respects max capital allocation and max loss per trade
- Every screening decision logged (in/out + reason)
- Every ranking logged with composite breakdown
- Trade plan rejection reasons fully logged

## Files to Create

| File | Description |
|------|-------------|
| `india/strategy/__init__.py` | Package marker |
| `india/strategy/screener.py` | Universe filtering |
| `india/strategy/ranker.py` | Composite scoring + ranking |
| `india/strategy/trade_plan.py` | Entry/SL/TP/position sizing |
| `tests/india/test_strategy.py` | Unit tests |
| `tests/india/test_strategy_integration.py` | Integration tests |

## Testing

- Unit tests: screener with known universe → expected filtered list
- Test ranker: verify composite math, sorting, cutoff
- Test trade plan: verify SL/TP distances, position sizing math
- Integration tests: analysis output → strategy → trade plans
- Test "NO TRADE" scenario: all stocks below threshold
