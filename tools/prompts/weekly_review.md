# Prompt: Weekly Performance Review Analysis

## Used By
`india/review/weekly_review.py` and `us/review/weekly_review.py`

## User Prompt Template
```
Analyze this week's trading performance and provide actionable insights.

Performance data:
{performance_json}

Provide:
1. WHAT WORKED (2-3 bullet points): Which signals/strategies produced winning trades and why
2. WHAT FAILED (2-3 bullet points): Which signals/strategies produced losing trades and why
3. ITERATIONS FOR NEXT WEEK (2-3 specific, actionable changes):
   - Be specific: "Increase ADX threshold from 25 to 30 for shorts" not "Improve entries"
   - Reference actual data from the trades
   - Suggest parameter tweaks with reasoning

Keep it concise. No fluff. Trader-to-trader tone.
```

## Variables
- `{performance_json}`: JSON with trades, P&L by day, by sector, win rate, signal accuracy

## Expected Output
Plain text, 3 sections, bulleted. Used directly in Telegram weekly review message.
