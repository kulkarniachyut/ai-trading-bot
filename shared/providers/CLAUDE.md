# shared/providers/ — Vendor API Clients

**Status:** Pending — Step 3

Raw API wrappers for external data sources used by both India and US systems.

## Rules
1. Providers return RAW API responses. No business logic. No normalization.
2. Every async method MUST use `httpx.AsyncClient` with `timeout=15`.
3. Every method MUST be decorated with `@retry` (tenacity) — 3 attempts, exponential backoff.
4. Every method MUST return `ProviderResult(success, data, provider, latency_ms, error)`.
5. Every method MUST log the API call: provider name, endpoint, latency, status.
6. API keys accessed via `shared/utils/config.py`. Never hardcoded. Never inline `os.getenv()`.
7. If provider needs authentication (session cookies, tokens), handle it in the provider class `__init__` or a dedicated auth method.

## ProviderResult Schema
```python
@dataclass
class ProviderResult:
    success: bool
    data: Any              # Raw API response
    provider: str          # e.g., "yfinance", "newsapi"
    latency_ms: int
    error: str | None
    metadata: dict | None  # Optional: rate limits, pagination info
```

## Adding a New Provider
Follow the skill: `.claude/skills/add-provider/SKILL.md`
