# Step 3: Shared Providers (yfinance, NewsAPI, GDELT, Reddit, LLM)

**Status:** ✅ Done
**Branch:** `feature/shared-03-providers` → merged to `main`

## Objective

Build the shared provider layer — vendor-specific API clients that return raw data. These are the lowest layer of the data pipeline, used by both India and US ingestion modules.

## Providers Built

| Provider | File | APIs Used | Cost |
|----------|------|-----------|------|
| yfinance | `shared/providers/yfinance_provider.py` | yfinance Python lib | Free |
| NewsAPI | `shared/providers/newsapi_provider.py` | newsapi.org REST API | Free tier (100/day) |
| GDELT | `shared/providers/gdelt_provider.py` | GDELT 2.0 API | Free |
| Reddit | `shared/providers/reddit_provider.py` | PRAW (Reddit API) | Free |
| LLM | `shared/providers/llm_provider.py` | Anthropic API (claude-3-haiku) | Pay-per-use |
| FRED | `shared/providers/fred_provider.py` | FRED REST API | Free |
| RSS | `shared/providers/rss_provider.py` | feedparser | Free |

## Transformers Built

| Transformer | File | Input → Output |
|-------------|------|----------------|
| MarketTransformer | `shared/transformers/market_transformer.py` | yfinance raw → MarketSnapshot, CommoditySnapshot |
| NewsTransformer | `shared/transformers/news_transformer.py` | NewsAPI/GDELT/Reddit/RSS raw → GeoSignal |
| Base dataclasses | `shared/transformers/base.py` | MarketSnapshot, CommoditySnapshot, GeoSignal, IngestionResult |

## Architecture

Each provider follows the standard contract:

```python
class SomeProvider:
    async def fetch_something(self, params...) -> ProviderResult:
        # httpx with timeout=15s
        # tenacity @retry(stop_after_attempt(3), wait_exponential)
        # returns ProviderResult — never raises
        # logs via log_api_call()
```

### ProviderResult dataclass
```python
@dataclass
class ProviderResult:
    success: bool
    data: Any
    provider: str
    latency_ms: int
    error: str | None
    metadata: dict | None
```

## Key Decisions

- **LLM backend:** Anthropic (claude-3-haiku-20240307) — fast + cheap for enrichment
- **LLMConfig has no `llm_model` field** — model is hardcoded to `_DEFAULT_MODEL` in provider
- **yfinance/Reddit/RSS run sync in executor** — they have no async API
- **No llm_transformer** — LLM output is plain text, parsed by ingestion layer per use case
- **All output dataclasses in `shared/transformers/base.py`** — single source of truth

## Files Created (15 total)

```
shared/providers/
  base.py                  # ProviderResult + make_error_result
  yfinance_provider.py
  newsapi_provider.py
  gdelt_provider.py
  reddit_provider.py
  llm_provider.py
  fred_provider.py
  rss_provider.py
  __init__.py
shared/transformers/
  base.py                  # MarketSnapshot, CommoditySnapshot, GeoSignal, IngestionResult
  market_transformer.py
  news_transformer.py
  __init__.py
tests/shared/
  test_providers.py            # 40 unit tests
  test_providers_integration.py # 17 integration tests
```

## Test Results

```
103 passed (40 unit + 17 integration + 41 telegram unit + 5 telegram integration)
```

All integration tests wire: AppConfig → Provider(config) → mocked external API → ProviderResult → Transformer → dataclass verification.

## Lessons Learned

1. **Always read actual config dataclass fields before writing tests** — `LLMConfig` had no `llm_model`, `IndiaBrokerConfig` used `broker` not `broker_name`, `AppConfig` required `risk` + `root_dir` fields that weren't obvious.
2. **yfinance runs sync** — must use `asyncio.get_event_loop().run_in_executor()` — same for PRAW and feedparser.
3. **feedparser never raises** — check `bozo` flag + empty entries instead.
4. **Python 3.14 deprecation warnings** from pytest-asyncio about `asyncio.get_event_loop_policy` — harmless, not our code.
