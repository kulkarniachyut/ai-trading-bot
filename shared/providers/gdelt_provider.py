"""GDELT 2.0 provider — geopolitical events and articles."""

from __future__ import annotations

import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "gdelt"
_BASE_URL = "https://api.gdeltproject.org/api/v2"
_TIMEOUT = 15.0


class GDELTProvider:
    """Fetches events and articles from GDELT 2.0 (no API key required)."""

    def __init__(self, config: AppConfig) -> None:
        # GDELT is free, no key needed
        self._config = config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def fetch_articles(
        self,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
        mode: str = "artlist",
    ) -> ProviderResult:
        """Search GDELT article list by query.

        Args:
            query: GDELT query string e.g. "India economy RBI"
            max_records: Max articles (1-250)
            timespan: "24h", "48h", "1week" etc.
            mode: "artlist" for article list, "timelinevol" for volume timeline

        Returns:
            ProviderResult.data = raw GDELT JSON (articles list)
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/doc/doc",
                    params={
                        "query": query,
                        "mode": mode,
                        "maxrecords": max_records,
                        "timespan": timespan,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            latency = int((time.monotonic() - t0) * 1000)
            articles = raw.get("articles", [])
            data_points = len(articles)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="doc",
                status="success",
                latency_ms=latency,
                data_points=data_points,
            )
            return ProviderResult(
                success=True,
                data=raw,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"query": query, "timespan": timespan},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="doc",
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
    async def fetch_tone_timeline(
        self,
        query: str,
        timespan: str = "7d",
    ) -> ProviderResult:
        """Fetch sentiment/tone timeline for a query.

        Returns:
            ProviderResult.data = raw GDELT timeline JSON
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/doc/doc",
                    params={
                        "query": query,
                        "mode": "timelinetone",
                        "timespan": timespan,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="timelinetone",
                status="success",
                latency_ms=latency,
                data_points=1,
            )
            return ProviderResult(
                success=True,
                data=raw,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"query": query, "timespan": timespan},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="timelinetone",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)
