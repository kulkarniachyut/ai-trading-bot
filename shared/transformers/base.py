"""Standard output dataclasses — contracts between providers, transformers, and ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketSnapshot:
    """Normalized snapshot of a global market index."""

    market: str          # "S&P 500", "Nikkei 225"
    close: float
    change_pct: float    # Decimal: 0.0082 = 0.82%
    direction: str       # "bullish" | "bearish" | "neutral"
    signal: str          # Human-readable summary e.g. "Risk-on, positive for IT"
    source: str          # "yfinance"
    fetched_at: str      # ISO 8601


@dataclass
class CommoditySnapshot:
    """Normalized commodity price snapshot."""

    commodity: str               # "Brent Crude", "Gold"
    ticker: str                  # "BZ=F", "GC=F"
    price: float                 # USD
    change_pct: float            # Decimal
    trend_5d: str                # "up" | "down" | "flat"
    affected_sectors: list[str]  # Sectors impacted
    impact_summary: str          # e.g. "Crude down 1.2% — positive for OMCs"
    source: str
    fetched_at: str


@dataclass
class GeoSignal:
    """Normalized geopolitical/macro news signal."""

    headline: str
    summary: str                 # 1-line summary (LLM-generated or truncated)
    source: str                  # "newsapi" | "gdelt" | "reddit" | "rss"
    source_url: str
    published_at: str            # ISO 8601
    market_impact: str           # "high" | "medium" | "low"
    sentiment: str               # "bullish" | "bearish" | "neutral"
    affected_sectors: list[str]
    urgency: int                 # 1-5 (5 = act now)
    fetched_at: str


@dataclass
class IngestionResult:
    """Wrapper returned by ingestion modules after a data collection run."""

    success: bool
    data: list[Any]              # List of typed schema objects
    partial: bool = False        # True if some sources failed but data was returned
    errors: list[str] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    fetched_at: str = ""
