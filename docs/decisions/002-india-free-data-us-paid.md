# ADR-002: India Uses Free Data, US Uses Paid (Polygon)

**Date:** 2026-03-07
**Status:** Accepted

## Context
India system needs global market data only for overnight direction (how did US/Asia close?). It doesn't need tick-by-tick real-time global data. Real-time data is only needed for Indian stocks (available free via broker API).

US system needs real-time pre-market and intraday data for US stocks — this requires a paid provider.

## Decision
- **India:** yfinance (free) for global overnight summaries + broker API (free) for Indian real-time. No Polygon or Twelve Data subscription needed.
- **US:** Polygon.io Starter+ ($29/mo) for real-time US data.

## Consequences
- India system costs ~$15-25/mo (mostly LLM + Twitter scraping)
- US system adds ~$34-39/mo (Polygon + LLM share)
- Total: ~$55-76/mo vs ~$105/mo if both used paid data

## Risk
- yfinance has no SLA and can break without notice. Mitigated by jugaad-data as fallback for India-specific data.
