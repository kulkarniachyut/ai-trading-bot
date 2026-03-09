"""News transformer — normalize NewsAPI, GDELT, Reddit, RSS → GeoSignal."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.transformers.base import GeoSignal
from shared.utils.logger import get_logger

logger = get_logger(__name__)

# Default urgency when not computable
_DEFAULT_URGENCY = 2
_DEFAULT_SENTIMENT = "neutral"
_DEFAULT_IMPACT = "medium"

# Keywords for basic sentiment inference (no LLM needed here)
_BEARISH_KEYWORDS = frozenset([
    "crash", "fall", "drop", "decline", "slump", "recession", "crisis",
    "ban", "sanction", "war", "attack", "default", "inflation", "hike",
    "downgrade", "loss", "risk", "concern", "warning", "tension",
])
_BULLISH_KEYWORDS = frozenset([
    "rally", "surge", "gain", "rise", "growth", "recovery", "boost",
    "reform", "cut", "stimulus", "upgrade", "profit", "record", "expansion",
    "deal", "agreement", "positive", "strong",
])
_HIGH_URGENCY_KEYWORDS = frozenset([
    "breaking", "urgent", "emergency", "crash", "war", "attack", "ban",
    "sanction", "default", "crisis", "halt",
])


def _infer_sentiment(text: str) -> str:
    lower = text.lower()
    bearish = sum(1 for kw in _BEARISH_KEYWORDS if kw in lower)
    bullish = sum(1 for kw in _BULLISH_KEYWORDS if kw in lower)
    if bullish > bearish:
        return "bullish"
    if bearish > bullish:
        return "bearish"
    return "neutral"


def _infer_urgency(text: str) -> int:
    lower = text.lower()
    if any(kw in lower for kw in _HIGH_URGENCY_KEYWORDS):
        return 4
    return _DEFAULT_URGENCY


def _safe_str(val: Any, default: str = "") -> str:
    return str(val).strip() if val else default


class NewsTransformer:
    """Normalizes raw news data from multiple sources into GeoSignal."""

    def to_geo_signals(
        self,
        raw: dict | list,
        source: str,
    ) -> list[GeoSignal]:
        """Dispatch to the right normalizer based on source.

        Args:
            raw: Raw provider data (varies by source)
            source: "newsapi" | "gdelt" | "reddit" | "rss"

        Returns:
            List of GeoSignal (skips bad records, never raises)
        """
        try:
            if source == "newsapi":
                return self._from_newsapi(raw)
            if source == "gdelt":
                return self._from_gdelt(raw)
            if source == "reddit":
                return self._from_reddit(raw)
            if source == "rss":
                return self._from_rss(raw)
            logger.warning("unknown news source", source=source)
            return []
        except Exception as exc:
            logger.error("to_geo_signals failed", source=source, error=str(exc))
            return []

    def _from_newsapi(self, raw: dict) -> list[GeoSignal]:
        fetched_at = datetime.now(timezone.utc).isoformat()
        signals: list[GeoSignal] = []
        articles = raw.get("articles", [])
        for art in articles:
            try:
                title = _safe_str(art.get("title"))
                if not title or title == "[Removed]":
                    continue
                text = f"{title} {_safe_str(art.get('description', ''))}"
                signals.append(GeoSignal(
                    headline=title,
                    summary=_safe_str(art.get("description", title))[:200],
                    source="newsapi",
                    source_url=_safe_str(art.get("url")),
                    published_at=_safe_str(art.get("publishedAt", fetched_at)),
                    market_impact=_DEFAULT_IMPACT,
                    sentiment=_infer_sentiment(text),
                    affected_sectors=[],
                    urgency=_infer_urgency(text),
                    fetched_at=fetched_at,
                ))
            except Exception as exc:
                logger.warning("newsapi article skip", error=str(exc))
        return signals

    def _from_gdelt(self, raw: dict) -> list[GeoSignal]:
        fetched_at = datetime.now(timezone.utc).isoformat()
        signals: list[GeoSignal] = []
        articles = raw.get("articles", [])
        for art in articles:
            try:
                title = _safe_str(art.get("title"))
                if not title:
                    continue
                signals.append(GeoSignal(
                    headline=title,
                    summary=title[:200],
                    source="gdelt",
                    source_url=_safe_str(art.get("url")),
                    published_at=_safe_str(art.get("seendate", fetched_at)),
                    market_impact=_DEFAULT_IMPACT,
                    sentiment=_infer_sentiment(title),
                    affected_sectors=[],
                    urgency=_infer_urgency(title),
                    fetched_at=fetched_at,
                ))
            except Exception as exc:
                logger.warning("gdelt article skip", error=str(exc))
        return signals

    def _from_reddit(self, raw: list) -> list[GeoSignal]:
        fetched_at = datetime.now(timezone.utc).isoformat()
        signals: list[GeoSignal] = []
        for post in raw:
            try:
                title = _safe_str(post.get("title"))
                if not title:
                    continue
                text = f"{title} {_safe_str(post.get('selftext', ''))}"
                created = post.get("created_utc", 0)
                published_at = (
                    datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                    if created else fetched_at
                )
                signals.append(GeoSignal(
                    headline=title,
                    summary=title[:200],
                    source="reddit",
                    source_url=_safe_str(post.get("url")),
                    published_at=published_at,
                    market_impact="medium" if post.get("score", 0) > 50 else "low",
                    sentiment=_infer_sentiment(text),
                    affected_sectors=[],
                    urgency=_infer_urgency(title),
                    fetched_at=fetched_at,
                ))
            except Exception as exc:
                logger.warning("reddit post skip", error=str(exc))
        return signals

    def _from_rss(self, raw: list) -> list[GeoSignal]:
        fetched_at = datetime.now(timezone.utc).isoformat()
        signals: list[GeoSignal] = []
        for entry in raw:
            try:
                title = _safe_str(entry.get("title"))
                if not title:
                    continue
                text = f"{title} {_safe_str(entry.get('summary', ''))}"
                signals.append(GeoSignal(
                    headline=title,
                    summary=_safe_str(entry.get("summary", title))[:200],
                    source="rss",
                    source_url=_safe_str(entry.get("link")),
                    published_at=_safe_str(entry.get("published", fetched_at)),
                    market_impact=_DEFAULT_IMPACT,
                    sentiment=_infer_sentiment(text),
                    affected_sectors=[],
                    urgency=_infer_urgency(title),
                    fetched_at=fetched_at,
                ))
            except Exception as exc:
                logger.warning("rss entry skip", error=str(exc))
        return signals
