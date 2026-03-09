"""Integration tests: config → provider init → mocked fetch → transformer → dataclass.

These tests wire real components end-to-end.
Only external network calls (httpx, yfinance, praw, feedparser, anthropic) are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from shared.providers.fred_provider import FREDProvider
from shared.providers.gdelt_provider import GDELTProvider
from shared.providers.llm_provider import LLMProvider
from shared.providers.newsapi_provider import NewsAPIProvider
from shared.providers.reddit_provider import RedditProvider
from shared.providers.rss_provider import RSSProvider
from shared.providers.yfinance_provider import YFinanceProvider
from shared.transformers.market_transformer import MarketTransformer
from shared.transformers.news_transformer import NewsTransformer
from shared.utils.config import (
    AppConfig,
    DBConfig,
    IndiaBrokerConfig,
    LLMConfig,
    RiskConfig,
    SharedProviderConfig,
    TelegramConfig,
    USBrokerConfig,
)


# ---------------------------------------------------------------------------
# Shared config fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def cfg() -> AppConfig:
    return AppConfig(
        telegram=TelegramConfig(
            bot_token="test_token",
            india_chat_id="111",
            us_chat_id="222",
        ),
        llm=LLMConfig(
            anthropic_api_key="sk-test",
            openai_api_key="",
        ),
        shared_providers=SharedProviderConfig(
            newsapi_key="test_newsapi",
            fred_api_key="test_fred",
            reddit_client_id="test_id",
            reddit_client_secret="test_secret",
            reddit_user_agent="test_agent/1.0",
            apify_token="",
            openweather_api_key="",
        ),
        india_broker=IndiaBrokerConfig(
            broker="dhan",
            api_key="x",
            api_secret="x",
            capital=100000.0,
        ),
        us_broker=USBrokerConfig(
            polygon_api_key="x",
            robinhood_username="x",
            robinhood_password="x",
            capital=10000.0,
        ),
        risk=RiskConfig(
            max_loss_per_trade_pct=0.02,
            max_concurrent_trades=3,
            min_rr_ratio=2.0,
        ),
        db=DBConfig(path="test.db"),
        root_dir=Path("."),
    )


def _ohlcv(rows: int = 10, start: float = 100.0, end: float = 105.0) -> pd.DataFrame:
    closes = np.linspace(start, end, rows)
    return pd.DataFrame(
        {"Open": closes, "High": closes * 1.01, "Low": closes * 0.99,
         "Close": closes, "Volume": np.full(rows, 1_000_000)},
        index=pd.date_range("2024-01-01", periods=rows, freq="B"),
    )


# ---------------------------------------------------------------------------
# yfinance → MarketTransformer
# ---------------------------------------------------------------------------

class TestYFinanceToMarketTransformer:
    """Full chain: config → YFinanceProvider → MarketTransformer → MarketSnapshot."""

    @pytest.mark.asyncio
    async def test_market_snapshots_end_to_end(self, cfg: AppConfig) -> None:
        provider = YFinanceProvider(cfg)
        transformer = MarketTransformer()
        df = _ohlcv(rows=10, start=4400.0, end=4500.0)

        with patch("shared.providers.yfinance_provider.yf.download", return_value=df):
            result = await provider.fetch_price_history(["^GSPC", "^N225"], period="5d")

        assert result.success
        snapshots = transformer.to_market_snapshots(result.data)
        assert len(snapshots) == 2
        sp500 = next(s for s in snapshots if s.market == "S&P 500")
        assert sp500.close > 0
        assert sp500.direction in ("bullish", "bearish", "neutral")
        assert sp500.source == "yfinance"
        assert sp500.fetched_at != ""

    @pytest.mark.asyncio
    async def test_commodity_snapshots_end_to_end(self, cfg: AppConfig) -> None:
        provider = YFinanceProvider(cfg)
        transformer = MarketTransformer()
        df = _ohlcv(rows=10, start=80.0, end=78.0)  # price falling

        with patch("shared.providers.yfinance_provider.yf.download", return_value=df):
            result = await provider.fetch_price_history(["BZ=F", "GC=F"], period="5d")

        assert result.success
        commodities = transformer.to_commodity_snapshots(result.data)
        assert len(commodities) == 2
        crude = next(c for c in commodities if c.ticker == "BZ=F")
        assert crude.commodity == "Brent Crude"
        assert crude.change_pct < 0
        assert "negative OMCs" in crude.impact_summary
        assert crude.trend_5d == "down"

    @pytest.mark.asyncio
    async def test_provider_failure_returns_empty_snapshots(self, cfg: AppConfig) -> None:
        provider = YFinanceProvider(cfg)
        transformer = MarketTransformer()

        with patch(
            "shared.providers.yfinance_provider.yf.download",
            side_effect=RuntimeError("network error"),
        ):
            result = await provider.fetch_price_history(["^GSPC"])

        assert not result.success
        # transformer should handle empty/bad data gracefully
        snapshots = transformer.to_market_snapshots({})
        assert snapshots == []


# ---------------------------------------------------------------------------
# NewsAPI → NewsTransformer
# ---------------------------------------------------------------------------

class TestNewsAPIToNewsTransformer:
    """Full chain: config → NewsAPIProvider → NewsTransformer → GeoSignal."""

    @pytest.mark.asyncio
    async def test_geo_signals_end_to_end(self, cfg: AppConfig) -> None:
        provider = NewsAPIProvider(cfg)
        transformer = NewsTransformer()
        mock_data = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "title": "RBI cuts repo rate amid growth concerns",
                    "description": "Central bank reduces rates to boost economy",
                    "url": "https://example.com/1",
                    "publishedAt": "2024-01-01T10:00:00Z",
                },
                {
                    "title": "Markets rally after positive GDP data",
                    "description": "Stocks surged on strong growth numbers",
                    "url": "https://example.com/2",
                    "publishedAt": "2024-01-01T09:00:00Z",
                },
            ],
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("shared.providers.newsapi_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await provider.fetch_headlines("India RBI economy")

        assert result.success
        signals = transformer.to_geo_signals(result.data, "newsapi")
        assert len(signals) == 2
        assert all(s.source == "newsapi" for s in signals)
        assert all(s.sentiment in ("bullish", "bearish", "neutral") for s in signals)
        assert all(s.urgency >= 1 for s in signals)
        assert all(s.fetched_at != "" for s in signals)

    @pytest.mark.asyncio
    async def test_provider_error_empty_signals(self, cfg: AppConfig) -> None:
        provider = NewsAPIProvider(cfg)
        transformer = NewsTransformer()

        with patch("shared.providers.newsapi_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("timeout")
            )
            result = await provider.fetch_headlines("test")

        assert not result.success
        signals = transformer.to_geo_signals(result.data or {}, "newsapi")
        assert signals == []


# ---------------------------------------------------------------------------
# GDELT → NewsTransformer
# ---------------------------------------------------------------------------

class TestGDELTToNewsTransformer:
    @pytest.mark.asyncio
    async def test_geo_signals_end_to_end(self, cfg: AppConfig) -> None:
        provider = GDELTProvider(cfg)
        transformer = NewsTransformer()
        mock_data = {
            "articles": [
                {
                    "title": "India Pakistan border tension escalates",
                    "url": "https://gdelt.com/1",
                    "seendate": "20240101T100000Z",
                },
                {
                    "title": "China trade sanctions hit Asian markets",
                    "url": "https://gdelt.com/2",
                    "seendate": "20240101T090000Z",
                },
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("shared.providers.gdelt_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await provider.fetch_articles("India geopolitics")

        assert result.success
        signals = transformer.to_geo_signals(result.data, "gdelt")
        assert len(signals) == 2
        assert all(s.source == "gdelt" for s in signals)
        # "tension" and "sanction" are high urgency keywords
        assert any(s.urgency >= 3 for s in signals)


# ---------------------------------------------------------------------------
# Reddit → NewsTransformer
# ---------------------------------------------------------------------------

class TestRedditToNewsTransformer:
    @pytest.mark.asyncio
    async def test_geo_signals_end_to_end(self, cfg: AppConfig) -> None:
        transformer = NewsTransformer()

        mock_post = MagicMock()
        mock_post.title = "Nifty 50 crashes 3% — global selloff continues"
        mock_post.score = 300
        mock_post.url = "https://reddit.com/r/IndianStockMarket/1"
        mock_post.selftext = "Everything crashing, recession fears"
        mock_post.created_utc = 1704067200.0
        mock_post.author = MagicMock(__str__=lambda self: "trader123")
        mock_post.num_comments = 85
        mock_post.upvote_ratio = 0.92

        mock_sub = MagicMock()
        mock_sub.hot.return_value = [mock_post]
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_sub

        with patch("shared.providers.reddit_provider.praw.Reddit", return_value=mock_reddit):
            provider = RedditProvider(cfg)
            result = await provider.fetch_posts(["IndianStockMarket"], limit=10)

        assert result.success
        signals = transformer.to_geo_signals(result.data, "reddit")
        assert len(signals) == 1
        sig = signals[0]
        assert sig.source == "reddit"
        assert sig.sentiment == "bearish"
        assert sig.market_impact == "medium"  # score > 50


# ---------------------------------------------------------------------------
# RSS → NewsTransformer
# ---------------------------------------------------------------------------

class TestRSSToNewsTransformer:
    @pytest.mark.asyncio
    async def test_geo_signals_end_to_end(self, cfg: AppConfig) -> None:
        provider = RSSProvider(cfg)
        transformer = NewsTransformer()

        mock_entry = MagicMock()
        mock_entry.get = lambda k, d="": {
            "title": "RBI issues circular on digital lending guidelines",
            "link": "https://rbi.org.in/circular/1",
            "published": "Mon, 01 Jan 2024 10:00:00 +0000",
            "summary": "New digital lending norms effective from Q1 2024",
        }.get(k, d)

        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.feed.get.return_value = "RBI RSS"
        mock_parsed.entries = [mock_entry]

        with patch("shared.providers.rss_provider.feedparser.parse", return_value=mock_parsed):
            result = await provider.fetch_feed("https://rbi.org.in/rss.xml")

        assert result.success
        signals = transformer.to_geo_signals(result.data, "rss")
        assert len(signals) == 1
        sig = signals[0]
        assert sig.source == "rss"
        assert sig.source_url == "https://rbi.org.in/circular/1"
        assert sig.headline == "RBI issues circular on digital lending guidelines"

    @pytest.mark.asyncio
    async def test_multiple_feeds_end_to_end(self, cfg: AppConfig) -> None:
        provider = RSSProvider(cfg)
        transformer = NewsTransformer()

        mock_entry = MagicMock()
        mock_entry.get = lambda k, d="": {
            "title": "SEBI tightens F&O margin requirements",
            "link": "https://sebi.gov.in/1",
            "published": "Mon, 01 Jan 2024",
            "summary": "Margin hike for derivatives",
        }.get(k, d)

        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.feed.get.return_value = "SEBI"
        mock_parsed.entries = [mock_entry]

        with patch("shared.providers.rss_provider.feedparser.parse", return_value=mock_parsed):
            results = await provider.fetch_feeds([
                "https://rbi.org.in/rss.xml",
                "https://sebi.gov.in/rss.xml",
            ])

        assert len(results) == 2
        all_signals = []
        for r in results:
            assert r.success
            all_signals.extend(transformer.to_geo_signals(r.data, "rss"))
        assert len(all_signals) == 2


# ---------------------------------------------------------------------------
# FRED (standalone — no transformer yet)
# ---------------------------------------------------------------------------

class TestFREDIntegration:
    @pytest.mark.asyncio
    async def test_fetch_series_end_to_end(self, cfg: AppConfig) -> None:
        provider = FREDProvider(cfg)
        mock_data = {
            "realtime_start": "2024-01-01",
            "observations": [
                {"date": "2024-01-01", "value": "5.33"},
                {"date": "2023-12-01", "value": "5.33"},
                {"date": "2023-11-01", "value": "5.33"},
            ],
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("shared.providers.fred_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await provider.fetch_series("FEDFUNDS", limit=3)

        assert result.success
        assert result.provider == "fred"
        obs = result.data["observations"]
        assert len(obs) == 3
        assert obs[0]["value"] == "5.33"


# ---------------------------------------------------------------------------
# LLM provider (standalone — no transformer)
# ---------------------------------------------------------------------------

class TestLLMIntegration:
    @pytest.mark.asyncio
    async def test_complete_end_to_end(self, cfg: AppConfig) -> None:
        mock_content = MagicMock()
        mock_content.text = '{"sentiment": "bullish", "sectors": ["Banking", "IT"]}'

        mock_usage = MagicMock()
        mock_usage.input_tokens = 120
        mock_usage.output_tokens = 35

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("shared.providers.llm_provider.anthropic.AsyncAnthropic", return_value=mock_client):
            provider = LLMProvider(cfg)
            result = await provider.complete(
                prompt="Classify sentiment: RBI cuts rates by 25bps",
                system="You are a financial analyst. Reply in JSON.",
            )

        assert result.success
        assert result.provider == "llm_anthropic"
        assert "bullish" in result.data["text"]
        assert result.data["input_tokens"] == 120
        assert result.data["output_tokens"] == 35
        assert result.latency_ms >= 0
