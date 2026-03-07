# Skill: Code Review for Trading System

## Purpose
Review code changes for correctness, safety, and alignment with project rules — especially trading-specific risks.

## When to Use
- Before every PR merge
- After writing any strategy, risk, or trade plan logic

## Checklist

### Trading Safety
- [ ] Risk rules from `config/risk_params.yaml` are enforced, never bypassed
- [ ] Position sizing uses the 2% capital risk formula
- [ ] Stop-loss and take-profit are always set (never None)
- [ ] R:R ratio is validated before trade plan is emitted
- [ ] No hardcoded prices, thresholds, or magic numbers — all from config

### Data Integrity
- [ ] Provider returns are checked for `success` before using `data`
- [ ] Fallback chain is implemented (not just primary provider)
- [ ] Transformer handles missing/None fields gracefully
- [ ] Dates are timezone-aware (IST for India, ET for US, UTC for storage)

### Code Quality
- [ ] No `print()` — use loguru
- [ ] No `os.getenv()` — use `shared/utils/config.py`
- [ ] No wildcard imports
- [ ] All async HTTP calls have timeout + retry
- [ ] Error handling: log and return partial data, never crash pipeline
- [ ] SQL queries are parameterized (no f-strings or .format())

### Architecture
- [ ] India and US systems don't import from each other
- [ ] Shared code is genuinely shared (used by both systems)
- [ ] Provider only returns raw data (no business logic)
- [ ] Transformer only normalizes (no API calls)

### Logging
- [ ] External API calls are logged (provider, latency, status)
- [ ] Fallback activations are logged (from, to, reason)
- [ ] Trade decisions are logged (accepted/rejected + reasons)
