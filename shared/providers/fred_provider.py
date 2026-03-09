"""FRED provider — economic data series from St. Louis Fed."""

from __future__ import annotations

import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "fred"
_BASE_URL = "https://api.stlouisfed.org/fred"
_TIMEOUT = 15.0


class FREDProvider:
    """Fetches economic series from FRED (Federal Reserve Economic Data)."""

    def __init__(self, config: AppConfig) -> None:
        self._api_key = config.shared_providers.fred_api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def fetch_series(
        self,
        series_id: str,
        limit: int = 10,
        sort_order: str = "desc",
    ) -> ProviderResult:
        """Fetch observations for a FRED series.

        Args:
            series_id: e.g. "FEDFUNDS", "DGS10", "CPIAUCSL"
            limit: Number of recent observations
            sort_order: "asc" | "desc"

        Returns:
            ProviderResult.data = raw FRED observations JSON dict
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": self._api_key,
                        "file_type": "json",
                        "limit": limit,
                        "sort_order": sort_order,
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            latency = int((time.monotonic() - t0) * 1000)
            data_points = len(raw.get("observations", []))
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="series/observations",
                status="success",
                latency_ms=latency,
                data_points=data_points,
            )
            return ProviderResult(
                success=True,
                data=raw,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"series_id": series_id},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="series/observations",
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
    async def fetch_series_info(self, series_id: str) -> ProviderResult:
        """Fetch metadata for a FRED series (title, units, frequency).

        Returns:
            ProviderResult.data = raw FRED series JSON dict
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/series",
                    params={
                        "series_id": series_id,
                        "api_key": self._api_key,
                        "file_type": "json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="series",
                status="success",
                latency_ms=latency,
                data_points=1,
            )
            return ProviderResult(
                success=True,
                data=raw,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"series_id": series_id},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="series",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)
