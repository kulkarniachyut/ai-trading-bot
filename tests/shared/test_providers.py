"""Unit + integration tests for shared providers."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from shared.providers.base import ProviderResult, make_error_result
from shared.providers.fred_provider import FREDProvider
from shared.providers.gdelt_provider import GDELTProvider
from shared.providers.llm_provider import LLMProvider
from shared.providers.newsapi_provider import NewsAPIProvider
from shared.providers.reddit_provider import RedditProvider
from shared.providers.rss_provider import RSSProvider
from shared.providers.yfinance_provider import YFinanceProvider
from shared.utils.config import AppConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config() -> AppConfig:
    """Build a minimal AppConfig for testing (no real API keys needed)."""
    from pathlib import Path

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


def _make_ohlcv_df(rows: int = 10) -> pd.DataFrame:
    import numpy as np
    idx = pd.date_range("2024-01-01", periods=rows, freq="B")
    return pd.DataFrame({
        "Open": np.random.uniform(100, 200, rows),
        "High": np.random.uniform(100, 200, rows),
        "Low": np.random.uniform(100, 200, rows),
        "Close": np.linspace(100, 110, rows),
        "Volume": np.random.randint(1_000_000, 5_000_000, rows),
    }, index=idx)


# ---------------------------------------------------------------------------
# ProviderResult / base
# ---------------------------------------------------------------------------

class TestProviderResultBase:
    def test_success_result(self) -> None:
        r = ProviderResult(success=True, data={"a": 1}, provider="test", latency_ms=50)
        assert r.success
        assert r.data == {"a": 1}
        assert r.error is None
        assert r.metadata is None

    def test_make_error_result(self) -> None:
        t0 = time.monotonic()
        r = make_error_result("test", "boom", t0)
        assert not r.success
        assert r.error == "boom"
        assert r.data is None
        assert r.latency_ms >= 0


# ---------------------------------------------------------------------------
# YFinanceProvider
# ---------------------------------------------------------------------------

class TestYFinanceProvider:
    @pytest.mark.asyncio
    async def test_fetch_price_history_success(self) -> None:
        cfg = _make_config()
        df = _make_ohlcv_df(10)
        provider = YFinanceProvider(cfg)

        with patch("shared.providers.yfinance_provider.yf.download", return_value=df):
            result = await provider.fetch_price_history(["^GSPC"], period="5d")

        assert result.success
        assert "^GSPC" in result.data
        assert result.provider == "yfinance"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_fetch_price_history_failure(self) -> None:
        cfg = _make_config()
        provider = YFinanceProvider(cfg)

        with patch(
            "shared.providers.yfinance_provider.yf.download",
            side_effect=RuntimeError("network error"),
        ):
            result = await provider.fetch_price_history(["^GSPC"])

        assert not result.success
        assert "network error" in result.error

    @pytest.mark.asyncio
    async def test_fetch_quote_success(self) -> None:
        cfg = _make_config()
        provider = YFinanceProvider(cfg)
        mock_info = {"last_price": 4500.0, "volume": 1_000_000}

        with patch(
            "shared.providers.yfinance_provider.yf.Ticker",
        ) as mock_ticker:
            mock_ticker.return_value.fast_info = mock_info
            result = await provider.fetch_quote("^GSPC")

        assert result.success
        assert result.provider == "yfinance"


# ---------------------------------------------------------------------------
# NewsAPIProvider
# ---------------------------------------------------------------------------

class TestNewsAPIProvider:
    @pytest.mark.asyncio
    async def test_fetch_headlines_success(self) -> None:
        cfg = _make_config()
        provider = NewsAPIProvider(cfg)
        mock_response = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {"title": "Markets rally on Fed pivot", "url": "https://example.com/1",
                 "description": "Stocks rose sharply", "publishedAt": "2024-01-01T10:00:00Z"},
                {"title": "RBI holds rates steady", "url": "https://example.com/2",
                 "description": "Central bank policy", "publishedAt": "2024-01-01T09:00:00Z"},
            ],
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()

        with patch("shared.providers.newsapi_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await provider.fetch_headlines("India stock market")

        assert result.success
        assert result.data["totalResults"] == 2
        assert result.provider == "newsapi"

    @pytest.mark.asyncio
    async def test_fetch_headlines_http_error(self) -> None:
        cfg = _make_config()
        provider = NewsAPIProvider(cfg)

        with patch("shared.providers.newsapi_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("connection refused")
            )
            result = await provider.fetch_headlines("test")

        assert not result.success
        assert result.error is not None


# ---------------------------------------------------------------------------
# GDELTProvider
# ---------------------------------------------------------------------------

class TestGDELTProvider:
    @pytest.mark.asyncio
    async def test_fetch_articles_success(self) -> None:
        cfg = _make_config()
        provider = GDELTProvider(cfg)
        mock_data = {
            "articles": [
                {"title": "India GDP growth beats expectations", "url": "https://gdelt.com/1",
                 "seendate": "20240101T100000Z"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("shared.providers.gdelt_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await provider.fetch_articles("India economy")

        assert result.success
        assert len(result.data["articles"]) == 1
        assert result.provider == "gdelt"

    @pytest.mark.asyncio
    async def test_fetch_articles_failure(self) -> None:
        cfg = _make_config()
        provider = GDELTProvider(cfg)

        with patch("shared.providers.gdelt_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("timeout")
            )
            result = await provider.fetch_articles("test")

        assert not result.success


# ---------------------------------------------------------------------------
# RedditProvider
# ---------------------------------------------------------------------------

class TestRedditProvider:
    @pytest.mark.asyncio
    async def test_fetch_posts_success(self) -> None:
        cfg = _make_config()

        mock_post = MagicMock()
        mock_post.title = "Nifty 50 all-time high!"
        mock_post.score = 150
        mock_post.url = "https://reddit.com/r/IndianStockMarket/1"
        mock_post.selftext = "Market is booming"
        mock_post.created_utc = 1704067200.0
        mock_post.author = MagicMock(__str__=lambda self: "user123")
        mock_post.num_comments = 25
        mock_post.upvote_ratio = 0.95

        mock_sub = MagicMock()
        mock_sub.hot.return_value = [mock_post]

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_sub

        with patch("shared.providers.reddit_provider.praw.Reddit", return_value=mock_reddit):
            provider = RedditProvider(cfg)
            result = await provider.fetch_posts(["IndianStockMarket"], limit=5)

        assert result.success
        assert len(result.data) == 1
        assert result.data[0]["title"] == "Nifty 50 all-time high!"
        assert result.provider == "reddit"

    @pytest.mark.asyncio
    async def test_fetch_posts_failure(self) -> None:
        cfg = _make_config()

        with patch("shared.providers.reddit_provider.praw.Reddit", side_effect=Exception("auth failed")):
            with pytest.raises(Exception):
                RedditProvider(cfg)


# ---------------------------------------------------------------------------
# LLMProvider
# ---------------------------------------------------------------------------

class TestLLMProvider:
    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        cfg = _make_config()

        mock_content = MagicMock()
        mock_content.text = "Sentiment: bullish. Affected sectors: IT, Banking."

        mock_usage = MagicMock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 20

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage = mock_usage

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(return_value=mock_response)

        with patch("shared.providers.llm_provider.anthropic.AsyncAnthropic", return_value=mock_anthropic):
            provider = LLMProvider(cfg)
            result = await provider.complete("Classify this news: RBI cuts rates")

        assert result.success
        assert "bullish" in result.data["text"]
        assert result.data["input_tokens"] == 50
        assert result.provider == "llm_anthropic"

    @pytest.mark.asyncio
    async def test_complete_failure(self) -> None:
        cfg = _make_config()

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(side_effect=Exception("api error"))

        with patch("shared.providers.llm_provider.anthropic.AsyncAnthropic", return_value=mock_anthropic):
            provider = LLMProvider(cfg)
            result = await provider.complete("test prompt")

        assert not result.success
        assert result.error is not None


# ---------------------------------------------------------------------------
# FREDProvider
# ---------------------------------------------------------------------------

class TestFREDProvider:
    @pytest.mark.asyncio
    async def test_fetch_series_success(self) -> None:
        cfg = _make_config()
        provider = FREDProvider(cfg)
        mock_data = {
            "observations": [
                {"date": "2024-01-01", "value": "5.33"},
                {"date": "2023-12-01", "value": "5.33"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("shared.providers.fred_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await provider.fetch_series("FEDFUNDS", limit=2)

        assert result.success
        assert len(result.data["observations"]) == 2
        assert result.provider == "fred"

    @pytest.mark.asyncio
    async def test_fetch_series_failure(self) -> None:
        cfg = _make_config()
        provider = FREDProvider(cfg)

        with patch("shared.providers.fred_provider.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("rate limit")
            )
            result = await provider.fetch_series("FEDFUNDS")

        assert not result.success


# ---------------------------------------------------------------------------
# RSSProvider
# ---------------------------------------------------------------------------

class TestRSSProvider:
    @pytest.mark.asyncio
    async def test_fetch_feed_success(self) -> None:
        cfg = _make_config()
        provider = RSSProvider(cfg)
        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.feed.get.return_value = "RBI RSS"
        mock_entry = MagicMock()
        mock_entry.get = lambda k, d="": {
            "title": "RBI Monetary Policy Statement",
            "link": "https://rbi.org.in/1",
            "published": "Mon, 01 Jan 2024 10:00:00 +0000",
            "summary": "RBI holds repo rate at 6.5%",
        }.get(k, d)
        mock_parsed.entries = [mock_entry]

        with patch("shared.providers.rss_provider.feedparser.parse", return_value=mock_parsed):
            result = await provider.fetch_feed("https://rbi.org.in/rss.xml")

        assert result.success
        assert len(result.data) == 1
        assert result.provider == "rss"

    @pytest.mark.asyncio
    async def test_fetch_feeds_multiple(self) -> None:
        cfg = _make_config()
        provider = RSSProvider(cfg)

        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.feed.get.return_value = "Feed"
        mock_parsed.entries = []

        with patch("shared.providers.rss_provider.feedparser.parse", return_value=mock_parsed):
            results = await provider.fetch_feeds([
                "https://rbi.org.in/rss.xml",
                "https://sebi.gov.in/rss.xml",
            ])

        assert len(results) == 2
        assert all(r.success for r in results)
