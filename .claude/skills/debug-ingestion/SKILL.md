# Skill: Debug a Failed Data Ingestion

## Purpose
Systematic workflow for diagnosing and fixing when a data source stops working.

## When to Use
- Morning briefing has missing data sections
- `ingestion_log` table shows repeated failures for a provider
- Telegram alert: "⚠️ Provider X failed"

## Diagnosis Steps

### 1. Check the Ingestion Log
```sql
SELECT * FROM ingestion_log
WHERE provider = 'the_failing_provider'
ORDER BY timestamp DESC
LIMIT 10;
```
Look for: error messages, status pattern (sporadic vs all failures), latency spikes.

### 2. Test the Provider Standalone
```bash
python -c "
import asyncio
from shared.providers.{provider} import {Provider}
p = {Provider}()
result = asyncio.run(p.fetch_something())
print(result)
"
```
- If this fails: provider/API issue (rate limit, key expired, endpoint changed)
- If this works: issue is in transformer or ingestion orchestration

### 3. Check Common Causes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 401/403 error | API key expired or rate limited | Check .env, check provider dashboard |
| Timeout | Provider is slow or down | Increase timeout, check status page |
| Empty data | API changed response format | Update transformer |
| Parsing error | Unexpected field types | Add defensive handling in transformer |
| SSL error | Certificate issue | Update certifi, check system time |

### 4. Check if Fallback Activated
```sql
SELECT * FROM ingestion_log
WHERE module = 'the_module' AND fallback_used IS NOT NULL
ORDER BY timestamp DESC
LIMIT 5;
```
If fallback is working, the system is already degraded-but-functioning. Fix primary at next opportunity.

### 5. Fix and Verify
- Fix the issue in provider or transformer
- Run standalone test again
- Run full ingestion module test
- Monitor next morning's pipeline

### 6. Add a Rule if Needed
If this failure mode was novel, add a rule to the relevant `CLAUDE.md`:
- Example: "yfinance returns None for delisted stocks — transformer must handle None close price"
