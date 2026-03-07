# Prompt: News Classification for Market Impact

## Used By
`india/analysis/sentiment.py` and `us/analysis/sentiment.py`

## System Prompt
```
You are a financial markets analyst specializing in identifying market-moving news.
You will be given a batch of news headlines and summaries.
For each item, classify its impact on the stock market.
```

## User Prompt Template
```
Classify each news item for {market} stock market impact.

For each item return a JSON object with:
- market_impact: "high" | "medium" | "low" | "none"
- sentiment: "bullish" | "bearish" | "neutral"
- affected_sectors: [list of sector names]
- urgency: 1-5 (5 = must act immediately, 1 = background context)
- summary: one line summary of market relevance

Only return items where market_impact is "high" or "medium".
Return as a JSON array.

News items:
{news_items_json}
```

## Variables
- `{market}`: "Indian" or "US"
- `{news_items_json}`: JSON array of `{"headline": "...", "source": "...", "published_at": "..."}`

## Model
- Primary: Claude Sonnet (claude-sonnet-4-20250514)
- Fallback: GPT-4o-mini

## Expected Output
```json
[
  {
    "headline": "US-China tariff escalation announced",
    "market_impact": "high",
    "sentiment": "bearish",
    "affected_sectors": ["Metals", "IT", "Export-oriented"],
    "urgency": 4,
    "summary": "Tariff escalation negative for metal exporters and global trade-exposed sectors"
  }
]
```

## Cost Estimate
~500-1000 tokens input per batch, ~200-500 output. At $3/1M tokens (Sonnet): ~$0.005 per classification batch.
