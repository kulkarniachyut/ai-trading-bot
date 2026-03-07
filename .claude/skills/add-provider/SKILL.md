# Skill: Add a New Data Provider

## Purpose
Step-by-step workflow for adding a new external data vendor to the system without breaking existing functionality.

## When to Use
- Adding a new market data source (e.g., switching from yfinance to Alpha Vantage)
- Adding a new news provider (e.g., adding Event Registry)
- Adding a new broker adapter (e.g., adding Upstox)

## Steps

### 1. Create the Provider File
Location: `shared/providers/{vendor_name}.py` or `{india,us}/providers/{vendor_name}.py`

```python
# Template:
from dataclasses import dataclass
from shared.utils.config import config
from shared.utils.logger import get_logger

logger = get_logger(__name__)

class NewVendorProvider:
    """Raw API client for NewVendor. Returns raw data only."""

    def __init__(self):
        self.api_key = config.get("NEW_VENDOR_API_KEY")
        self.base_url = "https://api.newvendor.com/v1"

    async def fetch_something(self, params) -> ProviderResult:
        # MUST: timeout, retry, return ProviderResult
        ...
```

Rules:
- Provider returns raw API data. NO business logic. NO normalization.
- MUST use httpx with timeout (max 15s)
- MUST use tenacity retry decorator
- MUST return `ProviderResult(success, data, provider, latency_ms, error)`
- MUST log the API call

### 2. Create or Update the Transformer
Location: `{india,us}/transformers/{data_type}.py` or `shared/transformers/`

- If raw format is different from existing providers, add a normalization branch
- Output MUST match the existing typed schema (e.g., `MarketSnapshot`, `FlowData`)
- NEVER change the output schema to fit a new vendor — transform the vendor data to fit

### 3. Update the Fallback Chain
In the relevant ingestion module, add the new provider to the fallback chain:

```python
PROVIDERS = [
    ("new_vendor", new_vendor_provider.fetch_something),
    ("existing_vendor", existing_provider.fetch_something),  # fallback
]
```

### 4. Add API Key to Config
- Add to `.env.example`
- Add to `shared/utils/config.py` if needed
- Document in `docs/tech-design-v1.md` provider table

### 5. Test Standalone
- Verify the provider fetches data independently
- Verify the transformer produces correct typed output
- Verify the fallback chain works (mock primary failure)

### 6. Log the Decision
- Add an ADR in `docs/decisions/` explaining why this vendor was added
