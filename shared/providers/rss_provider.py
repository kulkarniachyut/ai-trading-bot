"""RSS provider — fetch and parse RSS/Atom feeds."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import feedparser
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "rss"


class RSSProvider:
    """Parses RSS/Atom feeds via feedparser (no API key needed)."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def fetch_feed(self, url: str) -> ProviderResult:
        """Fetch and parse an RSS/Atom feed URL.

        Args:
            url: Feed URL e.g. "https://rbi.org.in/rss.xml"

        Returns:
            ProviderResult.data = list of entry dicts
                [{title, link, published, summary, source_url}]
        """
        t0 = time.monotonic()
        try:
            parsed = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: feedparser.parse(url),
            )
            # feedparser never raises — check bozo flag for parse errors
            if parsed.bozo and not parsed.entries:
                raise ValueError(f"Feed parse error: {parsed.bozo_exception}")

            entries: list[dict[str, Any]] = []
            for entry in parsed.entries:
                entries.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", "")[:500],
                    "source_url": url,
                })

            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="fetch_feed",
                status="success",
                latency_ms=latency,
                data_points=len(entries),
            )
            return ProviderResult(
                success=True,
                data=entries,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"url": url, "feed_title": parsed.feed.get("title", "")},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="fetch_feed",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)

    async def fetch_feeds(self, urls: list[str]) -> list[ProviderResult]:
        """Fetch multiple feeds concurrently.

        Returns:
            List of ProviderResult — one per URL (preserves order)
        """
        return list(await asyncio.gather(*[self.fetch_feed(url) for url in urls]))
