# ADR-003: SQLite with Raw SQL, No ORM

**Date:** 2026-03-07
**Status:** Accepted

## Context
Need a database for trade journal, signals, KPIs, ingestion health, and alert logging.

## Decision
Use SQLite via aiosqlite with raw parameterized SQL. No ORM.

## Reasoning
- Single-instance system (one VPS, one process) — no need for PostgreSQL
- ~50-100 rows/day — SQLite handles this trivially
- Zero ops — no database server to install/manage/monitor
- File-based — trivial Docker volume mount, trivial backup (just copy the file)
- Raw SQL is more explicit and debuggable than ORM-generated queries
- aiosqlite provides async interface consistent with the rest of the codebase

## Consequences
- Must write SQL manually (acceptable for ~6 tables)
- No migration framework in V1 (init_db creates tables with IF NOT EXISTS)
- No foreign key enforcement (application-level integrity)
- If we ever need multi-instance or heavy concurrent writes, migrate to PostgreSQL

## Alternatives Considered
- PostgreSQL: Overkill for single-instance, adds ops burden
- SQLAlchemy: Adds abstraction layer we don't need for 6 simple tables
- TinyDB/JSON files: Not queryable enough for KPI computation
