"""Shared providers — vendor API clients."""

from shared.providers.base import ProviderResult, make_error_result
from shared.providers.fred_provider import FREDProvider
from shared.providers.gdelt_provider import GDELTProvider
from shared.providers.llm_provider import LLMProvider
from shared.providers.newsapi_provider import NewsAPIProvider
from shared.providers.reddit_provider import RedditProvider
from shared.providers.rss_provider import RSSProvider
from shared.providers.yfinance_provider import YFinanceProvider

__all__ = [
    "ProviderResult",
    "make_error_result",
    "FREDProvider",
    "GDELTProvider",
    "LLMProvider",
    "NewsAPIProvider",
    "RedditProvider",
    "RSSProvider",
    "YFinanceProvider",
]
