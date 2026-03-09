"""Unit tests for shared transformers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from shared.transformers.base import CommoditySnapshot, GeoSignal, IngestionResult, MarketSnapshot
from shared.transformers.market_transformer import MarketTransformer
from shared.transformers.news_transformer import NewsTransformer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv_df(rows: int = 10, start_price: float = 100.0, end_price: float = 105.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=rows, freq="B")
    closes = np.linspace(start_price, end_price, rows)
    return pd.DataFrame({
        "Open": closes * 0.99,
        "High": closes * 1.01,
        "Low": closes * 0.98,
        "Close": closes,
        "Volume": np.full(rows, 1_000_000),
    }, index=idx)


# ---------------------------------------------------------------------------
# MarketTransformer
# ---------------------------------------------------------------------------

class TestMarketTransformer:
    def setup_method(self) -> None:
        self.t = MarketTransformer()

    def test_to_market_snapshots_bullish(self) -> None:
        df = _make_ohlcv_df(rows=5, start_price=100.0, end_price=102.0)
        result = self.t.to_market_snapshots({"^GSPC": df})
        assert len(result) == 1
        snap = result[0]
        assert isinstance(snap, MarketSnapshot)
        assert snap.market == "S&P 500"
        assert snap.source == "yfinance"
        assert snap.change_pct != 0
        assert snap.direction in ("bullish", "bearish", "neutral")
        assert snap.fetched_at != ""

    def test_to_market_snapshots_known_and_unknown_ticker(self) -> None:
        df = _make_ohlcv_df(5)
        result = self.t.to_market_snapshots({"^GSPC": df, "UNKNOWN": df})
        assert len(result) == 2
        names = [s.market for s in result]
        assert "S&P 500" in names
        assert "UNKNOWN" in names

    def test_to_market_snapshots_empty_df_skipped(self) -> None:
        raw = {"^GSPC": pd.DataFrame()}
        result = self.t.to_market_snapshots(raw)
        assert result == []

    def test_to_market_snapshots_single_row_skipped(self) -> None:
        df = _make_ohlcv_df(rows=1)
        result = self.t.to_market_snapshots({"^GSPC": df})
        assert result == []

    def test_to_commodity_snapshots_known_ticker(self) -> None:
        df = _make_ohlcv_df(rows=10, start_price=80.0, end_price=78.0)
        result = self.t.to_commodity_snapshots({"BZ=F": df})
        assert len(result) == 1
        snap = result[0]
        assert isinstance(snap, CommoditySnapshot)
        assert snap.commodity == "Brent Crude"
        assert snap.ticker == "BZ=F"
        assert snap.change_pct < 0
        assert snap.trend_5d in ("up", "down", "flat")
        assert len(snap.affected_sectors) > 0

    def test_to_commodity_snapshots_impact_down(self) -> None:
        df = _make_ohlcv_df(rows=5, start_price=100.0, end_price=95.0)
        result = self.t.to_commodity_snapshots({"BZ=F": df})
        assert "negative OMCs" in result[0].impact_summary

    def test_to_commodity_snapshots_impact_up(self) -> None:
        df = _make_ohlcv_df(rows=5, start_price=80.0, end_price=85.0)
        result = self.t.to_commodity_snapshots({"BZ=F": df})
        assert "positive OMCs" in result[0].impact_summary

    def test_to_commodity_snapshots_empty_df_skipped(self) -> None:
        result = self.t.to_commodity_snapshots({"GC=F": pd.DataFrame()})
        assert result == []

    def test_trend_5d_up(self) -> None:
        df = _make_ohlcv_df(rows=10, start_price=100.0, end_price=110.0)
        result = self.t.to_commodity_snapshots({"GC=F": df})
        assert result[0].trend_5d == "up"

    def test_trend_5d_down(self) -> None:
        df = _make_ohlcv_df(rows=10, start_price=110.0, end_price=100.0)
        result = self.t.to_commodity_snapshots({"GC=F": df})
        assert result[0].trend_5d == "down"


# ---------------------------------------------------------------------------
# NewsTransformer
# ---------------------------------------------------------------------------

class TestNewsTransformer:
    def setup_method(self) -> None:
        self.t = NewsTransformer()

    # NewsAPI
    def test_from_newsapi_success(self) -> None:
        raw = {
            "articles": [
                {
                    "title": "RBI cuts rates boosting market rally",
                    "url": "https://example.com/1",
                    "description": "Stocks surged after rate cut",
                    "publishedAt": "2024-01-01T10:00:00Z",
                },
            ]
        }
        result = self.t.to_geo_signals(raw, "newsapi")
        assert len(result) == 1
        sig = result[0]
        assert isinstance(sig, GeoSignal)
        assert sig.source == "newsapi"
        assert sig.sentiment in ("bullish", "bearish", "neutral")
        assert sig.urgency >= 1

    def test_from_newsapi_removed_article_skipped(self) -> None:
        raw = {"articles": [{"title": "[Removed]", "url": "", "publishedAt": ""}]}
        result = self.t.to_geo_signals(raw, "newsapi")
        assert result == []

    def test_from_newsapi_empty(self) -> None:
        result = self.t.to_geo_signals({"articles": []}, "newsapi")
        assert result == []

    # GDELT
    def test_from_gdelt_success(self) -> None:
        raw = {
            "articles": [
                {
                    "title": "India sanctions Pakistan amid border tension",
                    "url": "https://gdelt.com/1",
                    "seendate": "20240101T100000Z",
                },
            ]
        }
        result = self.t.to_geo_signals(raw, "gdelt")
        assert len(result) == 1
        sig = result[0]
        assert sig.source == "gdelt"
        assert sig.urgency >= 3  # "tension" is high urgency keyword

    def test_from_gdelt_empty_title_skipped(self) -> None:
        raw = {"articles": [{"title": "", "url": "https://gdelt.com/1"}]}
        result = self.t.to_geo_signals(raw, "gdelt")
        assert result == []

    # Reddit
    def test_from_reddit_success(self) -> None:
        raw = [
            {
                "title": "Nifty 50 crashes 3% on global selloff",
                "score": 200,
                "url": "https://reddit.com/r/1",
                "selftext": "everything is down",
                "created_utc": 1704067200.0,
            }
        ]
        result = self.t.to_geo_signals(raw, "reddit")
        assert len(result) == 1
        sig = result[0]
        assert sig.source == "reddit"
        assert sig.sentiment == "bearish"
        assert sig.market_impact == "medium"  # score > 50

    def test_from_reddit_low_score_low_impact(self) -> None:
        raw = [{"title": "Test", "score": 5, "url": "", "created_utc": 0.0, "selftext": ""}]
        result = self.t.to_geo_signals(raw, "reddit")
        assert result[0].market_impact == "low"

    # RSS
    def test_from_rss_success(self) -> None:
        raw = [
            {
                "title": "SEBI issues circular on derivatives",
                "link": "https://sebi.gov.in/1",
                "published": "Mon, 01 Jan 2024 10:00:00 +0000",
                "summary": "New margin requirements effective immediately",
            }
        ]
        result = self.t.to_geo_signals(raw, "rss")
        assert len(result) == 1
        sig = result[0]
        assert sig.source == "rss"
        assert sig.source_url == "https://sebi.gov.in/1"

    def test_from_rss_empty_title_skipped(self) -> None:
        raw = [{"title": "", "link": "", "published": "", "summary": ""}]
        result = self.t.to_geo_signals(raw, "rss")
        assert result == []

    # Unknown source
    def test_unknown_source_returns_empty(self) -> None:
        result = self.t.to_geo_signals({}, "twitter")
        assert result == []

    # Sentiment inference
    def test_sentiment_bullish(self) -> None:
        raw = {"articles": [{"title": "Markets rally on strong GDP growth", "url": "", "publishedAt": ""}]}
        result = self.t.to_geo_signals(raw, "newsapi")
        assert result[0].sentiment == "bullish"

    def test_sentiment_bearish(self) -> None:
        raw = {"articles": [{"title": "Markets crash amid recession fears", "url": "", "publishedAt": ""}]}
        result = self.t.to_geo_signals(raw, "newsapi")
        assert result[0].sentiment == "bearish"

    # IngestionResult dataclass
    def test_ingestion_result_defaults(self) -> None:
        r = IngestionResult(success=True, data=[])
        assert not r.partial
        assert r.errors == []
        assert r.sources_used == []
