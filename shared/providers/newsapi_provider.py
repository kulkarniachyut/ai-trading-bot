"""NewsAPI provider — fetch headlines by query."""

from __future__ import annotations

import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "newsapi"
_BASE_URL = "https://newsapi.org/v2"
_TIMEOUT = 15.0


class NewsAPIProvider:
    """Fetches news headlines from NewsAPI.org."""

    def __init__(self, config: AppConfig) -> None:
        self._api_key = config.shared_providers.newsapi_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def fetch_headlines(
        self,
        query: str,
        language: str = "en",
        page_size: int = 20,
        sort_by: str = "publishedAt",
    ) -> ProviderResult:
        """Fetch top headlines matching a query.

        Args:
            query: Search terms e.g. "India stock market RBI"
            language: ISO 639-1 language code
            page_size: Max articles (1-100)
            sort_by: "relevancy" | "popularity" | "publishedAt"

        Returns:
            ProviderResult.data = raw NewsAPI /v2/everything JSON dict
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/everything",
                    params={
                        "q": query,
                        "language": language,
                        "pageSize": page_size,
                        "sortBy": sort_by,
                        "apiKey": self._api_key,
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            latency = int((time.monotonic() - t0) * 1000)
            data_points = raw.get("totalResults", 0)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="everything",
                status="success",
                latency_ms=latency,
                data_points=data_points,
            )
            return ProviderResult(
                success=True,
                data=raw,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"query": query, "language": language},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="everything",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def fetch_top_headlines(
        self,
        country: str = "in",
        category: str = "business",
        page_size: int = 20,
    ) -> ProviderResult:
        """Fetch top headlines by country/category.

        Returns:
            ProviderResult.data = raw NewsAPI /v2/top-headlines JSON dict
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/top-headlines",
                    params={
                        "country": country,
                        "category": category,
                        "pageSize": page_size,
                        "apiKey": self._api_key,
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            latency = int((time.monotonic() - t0) * 1000)
            data_points = raw.get("totalResults", 0)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="top-headlines",
                status="success",
                latency_ms=latency,
                data_points=data_points,
            )
            return ProviderResult(
                success=True,
                data=raw,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"country": country, "category": category},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="top-headlines",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)
