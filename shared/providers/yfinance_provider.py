"""yfinance provider — price history + current quotes."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "yfinance"


class YFinanceProvider:
    """Wraps yfinance lib. All calls run sync yfinance in executor."""

    def __init__(self, config: AppConfig) -> None:
        # yfinance needs no API key
        self._config = config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def fetch_price_history(
        self,
        symbols: list[str],
        period: str = "1y",
        interval: str = "1d",
    ) -> ProviderResult:
        """Fetch OHLCV history for a list of symbols.

        Args:
            symbols: Ticker list e.g. ["RELIANCE.NS", "TCS.NS"]
            period: yfinance period string — "1y", "6mo", "200d" etc.
            interval: "1d", "1h" etc.

        Returns:
            ProviderResult.data = dict[symbol, pd.DataFrame]
        """
        t0 = time.monotonic()
        try:
            data: dict[str, Any] = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: {
                    sym: yf.download(
                        sym,
                        period=period,
                        interval=interval,
                        auto_adjust=True,
                        progress=False,
                        threads=False,
                    )
                    for sym in symbols
                },
            )
            latency = int((time.monotonic() - t0) * 1000)
            data_points = sum(len(df) for df in data.values())
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="download",
                status="success",
                latency_ms=latency,
                data_points=data_points,
            )
            return ProviderResult(
                success=True,
                data=data,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"symbols": symbols, "period": period, "interval": interval},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="download",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def fetch_quote(self, symbol: str) -> ProviderResult:
        """Fetch latest quote (price, volume, bid, ask) for a symbol.

        Returns:
            ProviderResult.data = dict with quote fields
        """
        t0 = time.monotonic()
        try:
            info: dict[str, Any] = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: yf.Ticker(symbol).fast_info,
            )
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="fast_info",
                status="success",
                latency_ms=latency,
                data_points=1,
            )
            return ProviderResult(
                success=True,
                data=dict(info),
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"symbol": symbol},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="fast_info",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)
