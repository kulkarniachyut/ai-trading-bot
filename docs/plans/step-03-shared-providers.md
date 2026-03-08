# Step 3: Shared Providers (yfinance, NewsAPI, GDELT, Reddit, LLM)

**Status:** Pending
**Branch:** `feature/shared-03-providers`

## Objective

Build the shared provider layer — vendor-specific API clients that return raw data. These are the lowest layer of the data pipeline, used by both India and US ingestion modules.

## Providers to Build

| Provider | File | APIs Used | Cost |
|----------|------|-----------|------|
| yfinance | `shared/providers/yfinance_provider.py` | yfinance Python lib | Free |
| NewsAPI | `shared/providers/newsapi_provider.py` | newsapi.org REST API | Free tier (100/day) |
| GDELT | `shared/providers/gdelt_provider.py` | GDELT 2.0 API | Free |
| Reddit | `shared/providers/reddit_provider.py` | PRAW (Reddit API) | Free |
| LLM | `shared/providers/llm_provider.py` | Anthropic / OpenAI API | Pay-per-use |
| FRED | `shared/providers/fred_provider.py` | FRED REST API | Free |
| RSS | `shared/providers/rss_provider.py` | feedparser | Free |

## Architecture

Each provider follows the standard contract:

```python
class SomeProvider:
    async def fetch_something(self, params...) -> ProviderResult:
        # MUST use httpx with timeout (max 15s)
        # MUST be wrapped in tenacity retry
        # MUST return ProviderResult (never raise to caller)
        # MUST log the call via shared logger
        # Returns raw API data — no normalization
```

### ProviderResult dataclass
```python
@dataclass
class ProviderResult:
    success: bool
    data: Any              # Raw API response
    provider: str          # Provider name for logging
    latency_ms: int        # Call duration
    error: str | None      # Error message if failed
    metadata: dict | None  # Rate limits, etc.
```

## Key Constraints

- Providers ONLY return raw data. No business logic, no normalization.
- Every call logged: provider name, latency_ms, status, data_points.
- All API keys from `shared/utils/config.py` — no `os.getenv()`.
- httpx with 15s timeout + tenacity retry on every call.
- Rate limit awareness: respect provider limits, log when approaching.

## Testing

- Unit tests: mock httpx responses, verify ProviderResult fields
- Integration tests: wire up real config → provider init → mock HTTP → verify end-to-end
- Test fallback behavior (provider returns error → ProviderResult.success=False)

## Files to Create

| File | Description |
|------|-------------|
| `shared/providers/__init__.py` | Package + ProviderResult dataclass |
| `shared/providers/yfinance_provider.py` | Market data, commodities, fundamentals |
| `shared/providers/newsapi_provider.py` | News search by topic/keyword |
| `shared/providers/gdelt_provider.py` | Geopolitical event monitoring |
| `shared/providers/reddit_provider.py` | Subreddit sentiment (r/IndianStreetBets, r/wallstreetbets) |
| `shared/providers/llm_provider.py` | LLM summarization and sentiment analysis |
| `shared/providers/fred_provider.py` | Federal Reserve economic data |
| `shared/providers/rss_provider.py` | RSS feed parsing (RBI, SEBI, Fed) |
| `tests/shared/test_providers.py` | Unit tests |
| `tests/shared/test_providers_integration.py` | Integration tests |
