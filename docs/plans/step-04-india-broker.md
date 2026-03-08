# Step 4: India Broker Adapter + Config

**Status:** Pending
**Branch:** `feature/india-04-broker`

## Objective

Build the India-specific broker adapter that abstracts broker APIs (Dhan/Breeze/Kite) behind a common interface. This enables swapping brokers without changing downstream code.

## Architecture

### Broker Abstraction
```python
class BrokerAdapter(ABC):
    async def get_ohlcv(self, symbol: str, days: int = 200) -> ProviderResult
    async def get_quote(self, symbol: str) -> ProviderResult
    async def get_fno_ban_list(self) -> ProviderResult
    async def get_market_status(self) -> ProviderResult
```

### Broker Selection
- `INDIA_BROKER` env var selects which adapter to use (`dhan`, `breeze`, `kite`)
- Factory pattern: `create_broker(config) -> BrokerAdapter`

## Files to Create

| File | Description |
|------|-------------|
| `india/providers/broker/__init__.py` | Factory function + ABC |
| `india/providers/broker/dhan_adapter.py` | Dhan API implementation |
| `india/providers/broker/breeze_adapter.py` | Breeze API (stub for later) |
| `india/providers/broker/kite_adapter.py` | Kite API (stub for later) |
| `tests/india/test_broker.py` | Unit tests |
| `tests/india/test_broker_integration.py` | Integration tests |

## Key Constraints

- Broker API keys from config — never hardcoded
- 15s timeout + tenacity retry on all broker calls
- Log every call: latency_ms, data_points, status
- Fallback: broker API → yfinance → jugaad-data for equities

## Testing

- Unit tests: mock HTTP responses for each broker API
- Integration tests: config → broker factory → mock API → verify ProviderResult
