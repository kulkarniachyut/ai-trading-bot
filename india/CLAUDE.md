# india/ — India Trading System (NSE/BSE)

Fully independent trading intelligence system for Indian equity markets.

## Market Info
- Exchange: NSE (primary), BSE (secondary)
- Universe: Nifty 200
- Trading hours: 9:15 AM - 3:30 PM IST
- Currency: INR (₹). All prices in ₹.
- Timezone: Asia/Kolkata (IST, UTC+5:30)
- Holidays: NSE holiday calendar (check annually)

## Data Sources (India-specific)
- Real-time stock prices: Broker API (Dhan/Breeze/Kite) — FREE
- Historical OHLCV: Broker API or yfinance fallback — FREE
- FII/DII flows: NSE API / jugaad-data — FREE
- F&O ban list: NSE website — FREE
- Overnight global: yfinance (delayed, free) — we only need direction, not real-time

## Key Signals (Priority Order)
1. FII/DII flows (strongest predictor of Indian market direction)
2. SGX Nifty / GIFT Nifty futures (gap up/down indicator)
3. Crude oil price (impacts ~20% of Nifty by market cap)
4. USD/INR movement (IT, pharma, exporters)
5. Technical setup on individual stocks
6. RBI/SEBI policy changes
7. Global overnight sentiment (US, Asia close)

## Rules
- NEVER import from `us/`. Only import from `shared/` and `india/`.
- All config in `india/config/`. Never share config with US system.
- Risk rules in `india/config/risk_params.yaml` are non-negotiable.
- India VIX > 22: no long trades (shorts allowed).
- Friday: half position sizes (weekend risk).
- First 15 minutes (9:15-9:30): no entries (gap volatility).
