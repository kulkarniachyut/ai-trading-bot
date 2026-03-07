# shared/db/ — Database Layer

SQLite via aiosqlite. Single file: `db/trading.db`. WAL mode enabled.

## Status: ✅ Built

`models.py` contains all DDL, init, query, and prune functions.

## Available Functions
```python
from shared.db.models import init_db, get_db, log_ingestion, prune_old_data

await init_db("/path/to/trading.db")   # Creates tables + indexes (idempotent)

async with get_db() as db:             # Context manager for queries
    cursor = await db.execute("SELECT ...", (param,))

await log_ingestion(system="india", timestamp=..., provider="yfinance", ...)

await prune_old_data()                 # Cleans stale data per retention policy
```

## Rules
1. Raw SQL only. NO ORM (no SQLAlchemy, no Peewee).
2. ALL queries MUST use parameterized inputs (`?` placeholders). NEVER use f-strings or .format() for SQL.
3. Schema defined in `docs/tech-design-v1.md` Section 6.
4. Tables use `system` column ('india' | 'us') to separate data. Both systems share one DB file.
5. Timestamps stored as ISO 8601 TEXT (SQLite doesn't have native datetime).
6. JSON blobs stored as TEXT. Use `json.dumps()` on write, `json.loads()` on read.
7. Use `async with get_db() as db:` — never call `aiosqlite.connect()` directly.

## Table Summary
| Table | Retention | Indexes |
|-------|-----------|---------|
| trades | Forever | system+date, symbol, status |
| signals | 90 days | system+date, signal_type |
| daily_kpis | Forever | UNIQUE(system, date) |
| weight_history | Forever | — |
| ingestion_log | 30 days | system+timestamp, status |
| alerts_sent | 60 days | — |

## Migrations
For V1: `init_db()` creates all tables with IF NOT EXISTS. No migration framework.
Future: if schema changes, add migration scripts in `db/migrations/`.
