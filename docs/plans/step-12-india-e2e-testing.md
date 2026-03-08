# Step 12: India End-to-End Testing

**Status:** Pending
**Branch:** `feature/india-12-e2e`

## Objective

Full end-to-end testing of the complete India system pipeline. Validate that all modules work together from ingestion through delivery.

## Test Scenarios

### 1. Happy Path — Full Pipeline
- Config loads → DB initializes → all ingestion runs → analysis scores → strategy picks → delivery sends → journal logs → KPIs compute
- All external APIs mocked with realistic data
- Verify: correct trades generated, messages formatted, DB records created

### 2. Degraded Mode — Non-Critical Failures
- Overnight global provider fails → system continues without it
- Social signals fail → briefing sent with reduced data
- Verify: system still delivers, briefing notes missing data

### 3. Critical Failure — FII/DII Down
- All FII/DII providers fail
- Verify: Telegram alert sent, reduced confidence noted, possible "NO TRADE TODAY"

### 4. No Trade Day
- All stocks score below threshold
- Verify: "NO TRADE TODAY" briefing sent, no trade alerts, journal records "no_trade"

### 5. Risk Gate Rejections
- High VIX → all trades rejected
- Friday rule → no new positions
- Sector concentration → 3rd trade in same sector rejected
- Verify: rejection reasons logged, alert sent explaining why

### 6. Message Splitting
- Briefing exceeds 4096 chars
- Verify: split into multiple messages, all sent successfully

### 7. Deduplication
- Same briefing triggered twice (scheduler restart)
- Verify: second send blocked by dedup

## Key Constraints

- ALL external APIs mocked — tests must run without internet
- Tests use real config, real DB (temp file), real module wiring
- Every assertion checks both the output AND the DB state
- Tests run in < 60 seconds total

## Files to Create

| File | Description |
|------|-------------|
| `tests/india/test_e2e_pipeline.py` | Full pipeline integration tests |
| `tests/india/conftest.py` | Shared fixtures for India tests |

## Testing

This IS the testing step. All tests must pass: `pytest tests/ -v`
