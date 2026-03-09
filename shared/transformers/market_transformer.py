"""Market transformer — yfinance raw → MarketSnapshot, CommoditySnapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from shared.transformers.base import CommoditySnapshot, MarketSnapshot
from shared.utils.logger import get_logger

logger = get_logger(__name__)

# Thresholds loaded inline — overridden by callers if needed
_BULLISH_THRESHOLD = 0.002   # >0.2% = bullish
_BEARISH_THRESHOLD = -0.002  # <-0.2% = bearish
_FLAT_TREND_THRESHOLD = 0.005  # 5d change within ±0.5% = flat


def _direction(change_pct: float) -> str:
    if change_pct > _BULLISH_THRESHOLD:
        return "bullish"
    if change_pct < _BEARISH_THRESHOLD:
        return "bearish"
    return "neutral"


def _trend_5d(df: pd.DataFrame) -> str:
    """Compute 5-day trend from OHLCV DataFrame."""
    if df is None or len(df) < 5:
        return "flat"
    try:
        close_col = "Close" if "Close" in df.columns else df.columns[-1]
        recent = df[close_col].iloc[-5:]
        change = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]
        if change > _FLAT_TREND_THRESHOLD:
            return "up"
        if change < -_FLAT_TREND_THRESHOLD:
            return "down"
        return "flat"
    except Exception as exc:
        logger.warning("trend_5d failed", error=str(exc))
        return "flat"


class MarketTransformer:
    """Normalizes yfinance raw data into MarketSnapshot and CommoditySnapshot."""

    # Market index config: ticker → display name + sector signal template
    _MARKET_MAP: dict[str, dict[str, str]] = {
        "^GSPC": {"name": "S&P 500", "signal_template": "US market {dir} — {impact} for IT/pharma exports"},
        "^DJI": {"name": "Dow Jones", "signal_template": "US Dow {dir}"},
        "^IXIC": {"name": "NASDAQ", "signal_template": "NASDAQ {dir} — tech sentiment"},
        "^N225": {"name": "Nikkei 225", "signal_template": "Japan market {dir} — Asia risk {sentiment}"},
        "^HSI": {"name": "Hang Seng", "signal_template": "HK market {dir} — China risk {sentiment}"},
        "^FTSE": {"name": "FTSE 100", "signal_template": "UK market {dir}"},
        "^GDAXI": {"name": "DAX", "signal_template": "Germany market {dir}"},
        "^NSEI": {"name": "Nifty 50", "signal_template": "Nifty {dir}"},
    }

    # Commodity config: ticker → display name + affected sectors
    _COMMODITY_MAP: dict[str, dict[str, Any]] = {
        "BZ=F": {
            "name": "Brent Crude",
            "sectors": ["Oil & Gas", "Paints", "Chemicals", "Aviation"],
            "impact_up": "Crude up — positive OMCs, negative paints/aviation",
            "impact_down": "Crude down — negative OMCs, positive paints/aviation",
        },
        "CL=F": {
            "name": "WTI Crude",
            "sectors": ["Oil & Gas", "Chemicals"],
            "impact_up": "WTI up — positive OMCs",
            "impact_down": "WTI down — negative OMCs",
        },
        "GC=F": {
            "name": "Gold",
            "sectors": ["Jewellery", "Safe Haven"],
            "impact_up": "Gold up — defensive/safe-haven bid",
            "impact_down": "Gold down — risk-on sentiment",
        },
        "SI=F": {
            "name": "Silver",
            "sectors": ["Metals", "Industrial"],
            "impact_up": "Silver up — industrial demand signal",
            "impact_down": "Silver down — industrial slowdown signal",
        },
        "HG=F": {
            "name": "Copper",
            "sectors": ["Metals", "Infrastructure", "EVs"],
            "impact_up": "Copper up — global growth positive",
            "impact_down": "Copper down — global growth concern",
        },
        "NG=F": {
            "name": "Natural Gas",
            "sectors": ["Energy", "Utilities"],
            "impact_up": "NatGas up — energy cost pressure",
            "impact_down": "NatGas down — energy cost relief",
        },
    }

    def to_market_snapshots(
        self,
        raw: dict[str, pd.DataFrame],
    ) -> list[MarketSnapshot]:
        """Convert yfinance price history dict → list of MarketSnapshot.

        Args:
            raw: {ticker: pd.DataFrame} from YFinanceProvider.fetch_price_history

        Returns:
            List of MarketSnapshot (skips tickers with bad/empty data)
        """
        fetched_at = datetime.now(timezone.utc).isoformat()
        snapshots: list[MarketSnapshot] = []

        for ticker, df in raw.items():
            try:
                if df is None or df.empty or len(df) < 2:
                    logger.warning("empty df skipped", ticker=ticker)
                    continue

                close_col = "Close" if "Close" in df.columns else df.columns[-1]
                prev_close = float(df[close_col].iloc[-2])
                last_close = float(df[close_col].iloc[-1])

                if prev_close == 0:
                    logger.warning("zero prev_close skipped", ticker=ticker)
                    continue

                change_pct = (last_close - prev_close) / prev_close
                direction = _direction(change_pct)
                meta = self._MARKET_MAP.get(ticker, {"name": ticker, "signal_template": "{dir}"})

                impact = "positive" if direction == "bullish" else ("negative" if direction == "bearish" else "neutral")
                signal = (
                    meta["signal_template"]
                    .replace("{dir}", direction)
                    .replace("{impact}", impact)
                    .replace("{sentiment}", "on" if direction == "bullish" else "off")
                )

                snapshots.append(MarketSnapshot(
                    market=meta["name"],
                    close=last_close,
                    change_pct=round(change_pct, 6),
                    direction=direction,
                    signal=signal,
                    source="yfinance",
                    fetched_at=fetched_at,
                ))
            except Exception as exc:
                logger.warning("market snapshot failed", ticker=ticker, error=str(exc))

        return snapshots

    def to_commodity_snapshots(
        self,
        raw: dict[str, pd.DataFrame],
    ) -> list[CommoditySnapshot]:
        """Convert yfinance price history dict → list of CommoditySnapshot.

        Args:
            raw: {ticker: pd.DataFrame} from YFinanceProvider.fetch_price_history

        Returns:
            List of CommoditySnapshot (skips tickers with bad/empty data)
        """
        fetched_at = datetime.now(timezone.utc).isoformat()
        snapshots: list[CommoditySnapshot] = []

        for ticker, df in raw.items():
            try:
                if df is None or df.empty or len(df) < 2:
                    logger.warning("empty commodity df skipped", ticker=ticker)
                    continue

                close_col = "Close" if "Close" in df.columns else df.columns[-1]
                prev_close = float(df[close_col].iloc[-2])
                last_close = float(df[close_col].iloc[-1])

                if prev_close == 0:
                    continue

                change_pct = (last_close - prev_close) / prev_close
                trend = _trend_5d(df)
                meta = self._COMMODITY_MAP.get(ticker, {
                    "name": ticker,
                    "sectors": [],
                    "impact_up": f"{ticker} up",
                    "impact_down": f"{ticker} down",
                })

                impact_summary = meta["impact_up"] if change_pct >= 0 else meta["impact_down"]

                snapshots.append(CommoditySnapshot(
                    commodity=meta["name"],
                    ticker=ticker,
                    price=round(last_close, 4),
                    change_pct=round(change_pct, 6),
                    trend_5d=trend,
                    affected_sectors=meta.get("sectors", []),
                    impact_summary=impact_summary,
                    source="yfinance",
                    fetched_at=fetched_at,
                ))
            except Exception as exc:
                logger.warning("commodity snapshot failed", ticker=ticker, error=str(exc))

        return snapshots
