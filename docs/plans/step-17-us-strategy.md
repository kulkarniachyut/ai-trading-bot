# Step 17: US Strategy — Screener, Ranker, Trade Plan

**Status:** Planned
**Branch:** `feature/us-17-strategy`

## Objective

Build the US strategy layer. Mirrors Step 8 architecture with US-specific adjustments.

## Modules to Build

### 1. Screener (`us/strategy/screener.py`)
- US watchlist → filtered candidates
- Filters: volume, earnings blackout, market cap, sector diversification

### 2. Ranker (`us/strategy/ranker.py`)
- Same composite scoring as India (weights from US config)
- Top 2-3 picks

### 3. Trade Plan (`us/strategy/trade_plan.py`)
- Entry/SL/TP in USD
- Position sizing based on US capital allocation
- Risk gate validation

## Files to Create

| File | Description |
|------|-------------|
| `us/strategy/__init__.py` | Package marker |
| `us/strategy/screener.py` | US universe filtering |
| `us/strategy/ranker.py` | US composite ranking |
| `us/strategy/trade_plan.py` | US trade plan generation |
| `tests/us/test_strategy.py` | Unit + integration tests |
