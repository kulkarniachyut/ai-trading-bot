"""Reddit provider — fetch posts from subreddits via PRAW."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import praw
import praw.models
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "reddit"


class RedditProvider:
    """Fetches posts from subreddits using PRAW (read-only)."""

    def __init__(self, config: AppConfig) -> None:
        cfg = config.shared_providers
        self._reddit = praw.Reddit(
            client_id=cfg.reddit_client_id,
            client_secret=cfg.reddit_client_secret,
            user_agent=cfg.reddit_user_agent,
            read_only=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def fetch_posts(
        self,
        subreddits: list[str],
        limit: int = 25,
        sort: str = "hot",
        time_filter: str = "day",
    ) -> ProviderResult:
        """Fetch posts from one or more subreddits.

        Args:
            subreddits: e.g. ["IndiaInvestments", "IndianStockMarket"]
            limit: Max posts per subreddit
            sort: "hot" | "new" | "top"
            time_filter: "day" | "week" (used with sort="top")

        Returns:
            ProviderResult.data = list of post dicts
                [{title, score, url, selftext, created_utc, subreddit, author}]
        """
        t0 = time.monotonic()
        try:
            posts: list[dict[str, Any]] = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._fetch_posts_sync(subreddits, limit, sort, time_filter),
            )
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="subreddit.posts",
                status="success",
                latency_ms=latency,
                data_points=len(posts),
            )
            return ProviderResult(
                success=True,
                data=posts,
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"subreddits": subreddits, "sort": sort},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="subreddit.posts",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)

    def _fetch_posts_sync(
        self,
        subreddits: list[str],
        limit: int,
        sort: str,
        time_filter: str,
    ) -> list[dict[str, Any]]:
        posts: list[dict[str, Any]] = []
        for sub_name in subreddits:
            sub = self._reddit.subreddit(sub_name)
            if sort == "hot":
                listing = sub.hot(limit=limit)
            elif sort == "new":
                listing = sub.new(limit=limit)
            elif sort == "top":
                listing = sub.top(time_filter=time_filter, limit=limit)
            else:
                listing = sub.hot(limit=limit)

            for post in listing:
                posts.append({
                    "title": post.title,
                    "score": post.score,
                    "url": post.url,
                    "selftext": post.selftext[:500] if post.selftext else "",
                    "created_utc": post.created_utc,
                    "subreddit": sub_name,
                    "author": str(post.author) if post.author else "[deleted]",
                    "num_comments": post.num_comments,
                    "upvote_ratio": post.upvote_ratio,
                })
        return posts
