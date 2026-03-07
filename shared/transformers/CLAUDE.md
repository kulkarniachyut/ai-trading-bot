# shared/transformers/ — Data Normalization

Transforms raw provider data into typed standard schemas.

## Rules
1. Input: raw dict/list from a provider. Output: list of typed dataclass instances.
2. MUST handle missing or None fields gracefully — use defaults, skip bad records, log warnings.
3. MUST NOT make any API calls. Transformers are pure data mapping.
4. MUST NOT raise exceptions to caller. Log errors, skip malformed records, return what you can.
5. Output schemas defined in `docs/tech-design-v1.md` Section 5.

## Pattern
```python
class MarketTransformer:
    def normalize(self, raw_data: dict, source: str) -> list[MarketSnapshot]:
        results = []
        for item in raw_data:
            try:
                results.append(MarketSnapshot(
                    market=item.get("name", "Unknown"),
                    close=float(item.get("close", 0)),
                    ...
                ))
            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Skipping malformed record", error=str(e), source=source)
        return results
```

## Key Principle
If you swap a provider (e.g., yfinance → Alpha Vantage), the transformer MAY need an update to handle different raw formats, but the OUTPUT schema stays exactly the same. Downstream code never changes.
