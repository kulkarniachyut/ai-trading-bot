# Prompt: Central Bank Speech / Statement Tone Classification

## Used By
`india/ingestion/central_banks.py` and `us/ingestion/fed_policy.py`

## User Prompt Template
```
Analyze the following central bank statement/speech excerpt.

Classify:
- tone: "hawkish" | "dovish" | "neutral"
- key_signals: [list of 2-3 key takeaways]
- rate_direction: "hike_likely" | "cut_likely" | "hold_likely"
- market_impact: brief one-line impact on {market} equities
- affected_sectors: [list of sectors most impacted]

Statement:
{statement_text}

Central bank: {bank_name}
Speaker: {speaker_name}
Date: {date}
```

## Variables
- `{market}`: "Indian" or "US"
- `{statement_text}`: The speech/statement text (max 2000 chars, truncated)
- `{bank_name}`: "RBI" | "Fed" | "ECB" | "BoE" | "BoJ"
- `{speaker_name}`: Name of speaker
- `{date}`: Date of statement

## Expected Output
```json
{
  "tone": "dovish",
  "key_signals": [
    "Emphasized growth concerns over inflation",
    "Hinted at liquidity easing measures",
    "No mention of rate hike timeline"
  ],
  "rate_direction": "cut_likely",
  "market_impact": "Positive for rate-sensitive sectors, banks and real estate could rally",
  "affected_sectors": ["Banking", "Real Estate", "Auto", "NBFCs"]
}
```
