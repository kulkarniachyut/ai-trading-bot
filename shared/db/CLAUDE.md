# shared/db/ — Database Layer

SQLite via aiosqlite. Single file: `db/trading.db`.

## Rules
1. Raw SQL only. NO ORM (no SQLAlchemy, no Peewee).
2. ALL queries MUST use parameterized inputs (`?` placeholders). NEVER use f-strings or .format() for SQL.
3. Schema defined in `docs/tech-design-v1.md` Section 6.
4. Tables use `system` column ('india' | 'us') to separate data. Both systems share one DB file.
5. Timestamps stored as ISO 8601 TEXT (SQLite doesn't have native datetime).
6. JSON blobs stored as TEXT. Use `json.dumps()` on write, `json.loads()` on read.
7. Always use `async with aiosqlite.connect(DB_PATH) as db:` — never leave connections open.

## Table Summary
| Table | Retention | Key |
|-------|-----------|-----|
| trades | Forever | system + date + symbol |
| signals | 90 days | system + date + signal_type |
| daily_kpis | Forever | system + date (UNIQUE) |
| weight_history | Forever | system + date |
| ingestion_log | 30 days | system + timestamp + provider |
| alerts_sent | 60 days | system + timestamp + alert_type |

## Migrations
For V1: `init_db()` creates all tables if not exist. No migration framework.
Future: if schema changes, add migration scripts in `db/migrations/`.
