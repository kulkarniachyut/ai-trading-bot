# Technical Design Document — V1
## Two-Market Day Trading Intelligence System

**Version:** 1.0
**Last Updated:** 2026-03-07
**Status:** Draft — iterates as we build

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Design](#2-high-level-design)
3. [System Architecture](#3-system-architecture)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [Data Models & Schemas](#5-data-models--schemas)
6. [Database Design](#6-database-design)
7. [Internal API Contracts](#7-internal-api-contracts)
8. [Provider Abstraction Layer](#8-provider-abstraction-layer)
9. [Storage Strategy](#9-storage-strategy)
10. [Scheduling & Timing](#10-scheduling--timing)
11. [Error Handling & Resilience](#11-error-handling--resilience)
12. [Logging & Observability](#12-logging--observability)
13. [Security & Secrets](#13-security--secrets)
14. [Deployment Architecture](#14-deployment-architecture)
15. [Appendix: Nifty 200 Sector Map](#appendix-a-sector-mapping)
16. [Changelog](#changelog)

---

## 1. System Overview

### 1.1 What This System Does

Two independent day trading intelligence systems running in one monorepo:

| System | Market | Broker | Telegram Time | Real-Time Data |
|--------|--------|--------|---------------|----------------|
| **India** | NSE/BSE (Nifty 200) | TBD (Dhan/Breeze/Kite) | 9:00 AM IST | Indian stocks only (broker API, free) |
| **US** | NYSE/NASDAQ | Robinhood | ~9:00 AM ET | US stocks (Polygon.io, $29/mo) |

Each system independently:
1. **Ingests** market data, news, flows, policy signals
2. **Analyzes** technical indicators, fundamentals, sentiment
3. **Screens & ranks** stocks using composite scoring
4. **Generates** 2-3 trade plans with entry/SL/TP
5. **Delivers** via Telegram (morning briefing + trade alerts)
6. **Monitors** intraday positions (SL/TP triggers)
7. **Journals** every trade, computes KPIs
8. **Self-tunes** scoring weights weekly based on results

### 1.2 Design Principles

1. **Independence** — India and US systems never import from each other. Breaking one cannot break the other.
2. **Vendor abstraction** — Every external API goes through Provider → Transformer → Standard Output. Swap vendor = swap one file.
3. **Fail gracefully** — No single API failure crashes the pipeline. Use fallbacks, log errors, send partial data.
4. **Config-driven** — Thresholds, watchlists, risk rules live in YAML. No magic numbers in code.
5. **Audit trail** — Every decision logged. Every trade journaled. Every API call recorded.

### 1.3 Non-Goals (V1)

- No auto-execution of trades (advisory only — user places orders manually)
- No options trading (equities only)
- No backtesting engine (future iteration)
- No web dashboard (Telegram only for V1)
- No multi-user support (single user)

---

## 2. High-Level Design

### 2.1 India System — Daily Pipeline

```
                        ┌─────────────────────────────────────┐
                        │         PRE-MARKET (8:45 AM IST)     │
                        └──────────────┬──────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ OVERNIGHT GLOBAL │    │   INDIA-SPECIFIC  │    │   INTELLIGENCE   │
│                  │    │                   │    │                  │
│ • US close       │    │ • FII/DII flows   │    │ • NewsAPI        │
│ • Asia morning   │    │ • India VIX       │    │ • GDELT          │
│ • Europe close   │    │ • SGX Nifty       │    │ • Reddit (ISB)   │
│ • Crude/Gold     │    │ • NSE OHLCV (D-1) │    │ • Twitter/X      │
│ • USD/INR        │    │ • F&O ban list    │    │ • RBI/SEBI/GOI   │
│ • US 10Y/DXY     │    │ • Earnings cal    │    │ • Climate/weather│
│                  │    │                   │    │ • FOMC/MPC cal   │
│ Source: yfinance │    │ Source: Broker    │    │ Source: Mixed    │
│ Cost: FREE       │    │ + jugaad + NSE    │    │ Cost: ~$15/mo    │
│                  │    │ Cost: FREE        │    │                  │
└────────┬─────────┘    └────────┬──────────┘    └────────┬─────────┘
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 │
                                 ▼
                   ┌──────────────────────────┐
                   │    ANALYSIS (8:55 AM)     │
                   │                          │
                   │  Technical (pandas-ta)   │──→ Score 0-100
                   │  Fundamental (quick)     │──→ Score 0-100
                   │  Sentiment (LLM)         │──→ Score 0-100
                   │  Correlation (mapping)   │──→ Sector alignment
                   │  Risk (hard rules)       │──→ Pass/Reject
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │    STRATEGY (8:58 AM)     │
                   │                          │
                   │  Screener: 200 → ~30     │
                   │  Ranker: composite score │
                   │  Trade Plan: entry/SL/TP │
                   │  Risk Gate: final check  │
                   │                          │
                   │  Output: 2-3 picks       │
                   │  OR "NO TRADE TODAY"      │
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │    DELIVERY (9:00 AM)     │
                   │                          │
                   │  Morning Briefing → TG   │
                   │  Trade Alerts → TG       │
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │  INTRADAY (9:15-3:30 PM) │
                   │                          │
                   │  Poll prices every 5 min │
                   │  SL/TP trigger alerts    │
                   │  Breaking news alerts    │
                   │  EOD exit reminders      │
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │      EOD (6:00 PM)       │
                   │                          │
                   │  Journal trades          │
                   │  Compute daily KPIs      │
                   └──────────────────────────┘
                                │
                         (Saturday 10 AM)
                                │
                                ▼
                   ┌──────────────────────────┐
                   │     WEEKLY REVIEW        │
                   │                          │
                   │  Performance report      │
                   │  Auto-tune weights       │
                   │  Safety checks           │
                   └──────────────────────────┘
```

### 2.2 US System — Daily Pipeline

Same architecture, different data sources and timing:
- Pre-market analysis: ~8:30 AM ET
- Telegram delivery: ~9:00 AM ET
- Intraday: 9:30 AM - 4:00 PM ET
- Uses Polygon.io (real-time) + Robinhood (portfolio)

*(Full US HLD to be detailed when we start US build)*

---

## 3. System Architecture

### 3.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEDULING LAYER                         │
│                    (APScheduler, IST/ET cron)                    │
├──────────────────────┬──────────────────────────────────────────┤
│                      │                                          │
│   INDIA SYSTEM       │           US SYSTEM                      │
│   ┌──────────────┐   │   ┌──────────────┐                      │
│   │  Scheduler   │   │   │  Scheduler   │                      │
│   │  Main.py     │   │   │  Main.py     │                      │
│   ├──────────────┤   │   ├──────────────┤                      │
│   │  Delivery    │   │   │  Delivery    │                      │
│   │  (formatter, │   │   │  (formatter, │                      │
│   │   notifier)  │   │   │   notifier)  │                      │
│   ├──────────────┤   │   ├──────────────┤                      │
│   │  Strategy    │   │   │  Strategy    │                      │
│   │  (screener,  │   │   │  (screener,  │                      │
│   │   ranker,    │   │   │   ranker,    │                      │
│   │   trade_plan)│   │   │   trade_plan)│                      │
│   ├──────────────┤   │   ├──────────────┤                      │
│   │  Analysis    │   │   │  Analysis    │                      │
│   │  (tech, fun, │   │   │  (tech, fun, │                      │
│   │   sentiment, │   │   │   sentiment, │                      │
│   │   risk)      │   │   │   risk)      │                      │
│   ├──────────────┤   │   ├──────────────┤                      │
│   │  Ingestion   │   │   │  Ingestion   │                      │
│   │  (7 modules) │   │   │  (6 modules) │                      │
│   ├──────────────┤   │   ├──────────────┤                      │
│   │  Transformers│   │   │  Transformers│                      │
│   ├──────────────┤   │   ├──────────────┤                      │
│   │  Providers   │   │   │  Providers   │                      │
│   │  (broker,    │   │   │  (polygon,   │                      │
│   │   jugaad,    │   │   │   robinhood) │                      │
│   │   nse)       │   │   │              │                      │
│   └──────────────┘   │   └──────────────┘                      │
│                      │                                          │
├──────────────────────┴──────────────────────────────────────────┤
│                       SHARED LAYER                              │
│                                                                 │
│  ┌────────────┐ ┌────────────┐ ┌──────┐ ┌──────┐ ┌──────────┐ │
│  │ Providers  │ │  Delivery  │ │  DB  │ │Utils │ │Transformers│ │
│  │ (yfinance, │ │ (telegram, │ │      │ │(cfg, │ │ (news)   │ │
│  │  newsapi,  │ │  formatter)│ │      │ │ log) │ │          │ │
│  │  gdelt,    │ │            │ │      │ │      │ │          │ │
│  │  reddit,   │ │            │ │      │ │      │ │          │ │
│  │  llm, fred,│ │            │ │      │ │      │ │          │ │
│  │  rss, etc) │ │            │ │      │ │      │ │          │ │
│  └────────────┘ └────────────┘ └──────┘ └──────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     INFRASTRUCTURE                              │
│           SQLite (aiosqlite) │ Docker │ VPS │ .env              │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Module Dependency Graph

```
shared/utils/config ──────────────────────────────→ (everything imports this)
shared/utils/logger ──────────────────────────────→ (everything imports this)
shared/db/models ─────────────────────────────────→ (ingestion, review, main)

shared/providers/* ───→ {india,us}/transformers/* ───→ {india,us}/ingestion/*
                                                            │
                                                            ▼
                                                   {india,us}/analysis/*
                                                            │
                                                            ▼
                                                   {india,us}/strategy/*
                                                            │
                                                            ▼
shared/delivery/telegram ←── {india,us}/delivery/formatter
                                                            │
                                                            ▼
                                                   {india,us}/review/*
                                                            │
                                                            ▼
                                                   {india,us}/scheduler
                                                            │
                                                            ▼
                                                   {india,us}/main.py
```

**Rule:** Arrows point in one direction. No circular dependencies. Lower layers never import from higher layers.

---

## 4. Data Flow Diagrams

### 4.1 Provider → Transformer → Ingestion Flow

```
                   PROVIDER LAYER              TRANSFORMER LAYER         INGESTION LAYER
                   (vendor-specific)           (normalization)           (orchestration)

  yfinance ──────→ raw: {                    ┌──────────────┐
                     "Close": 5892.34,       │              │     ┌──────────────────┐
                     "Volume": 3.2B,   ────→ │  market.py   │────→│ overnight_global │
                     ...                     │  normalize() │     │                  │
                   }                         └──────────────┘     │  • calls provider│
                                                                  │  • calls xformer │
  jugaad-data ───→ raw: {                    ┌──────────────┐     │  • handles error │
                     "FII_Buy": 12500,       │              │     │  • returns typed │
                     "FII_Sell": 11255, ───→ │  flows.py    │────→│    standard dict │
                     ...                     │  normalize() │     │                  │
                   }                         └──────────────┘     └──────────────────┘
```

### 4.2 Analysis → Strategy Flow

```
  ingestion outputs
        │
        ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  technical   │     │   macro     │     │ fundamental │
  │  score: 78   │     │  score: 65  │     │  score: 82  │
  │  dir: LONG   │     │  (from FII, │     │  (PE, D/E,  │
  │  reasons: [] │     │   commodity,│     │   ROE, etc) │
  └──────┬───────┘     │   geopol)   │     └──────┬──────┘
         │             └──────┬──────┘            │
         │                    │                   │
         └────────────────────┼───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     SCREENER      │
                    │                   │
                    │  Nifty 200        │
                    │  → Volume filter  │
                    │  → F&O ban filter │
                    │  → Earnings filter│
                    │  → Market cap     │
                    │  ≈ 30-40 stocks   │
                    └────────┬──────────┘
                             │
                             ▼
                    ┌───────────────────┐
                    │      RANKER       │
                    │                   │
                    │  composite =      │
                    │   0.55 * tech     │
                    │ + 0.30 * macro    │
                    │ + 0.15 * fund     │
                    │                   │
                    │  Filter > 70      │
                    │  Top 2-3 picks    │
                    └────────┬──────────┘
                             │
                             ▼
                    ┌───────────────────┐
                    │    TRADE PLAN     │
                    │                   │
                    │  Entry, SL, TP    │
                    │  Position size    │
                    │  R:R validation   │
                    │                   │
                    │  RISK GATE:       │
                    │  • R:R ≥ 2.0?    │
                    │  • SL ≤ 3%?      │
                    │  • VIX ok?       │
                    │  • Sector conc?  │
                    │  • Friday rule?  │
                    └────────┬──────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
                    ▼                  ▼
            2-3 TradePlans     "NO TRADE TODAY"
```

---

## 5. Data Models & Schemas

### 5.1 Standard Output Schemas (what flows between modules)

All schemas use Python dataclasses. These are the **contracts** — every module producing or consuming data must conform to these.

#### MarketSnapshot

```python
@dataclass
class MarketSnapshot:
    """Output of overnight_global ingestion"""
    market: str              # "S&P 500", "Nikkei 225", etc.
    close: float             # Closing price
    change_pct: float        # % change as decimal (0.0082 = 0.82%)
    direction: str           # "bullish" | "bearish" | "neutral"
    signal: str              # Human-readable: "Risk-on, positive for IT"
    source: str              # "yfinance"
    fetched_at: str          # ISO 8601 timestamp
```

#### CommoditySnapshot

```python
@dataclass
class CommoditySnapshot:
    """Output of commodities ingestion"""
    commodity: str           # "Brent Crude", "Gold", etc.
    ticker: str              # "BZ=F", "GC=F", etc.
    price: float             # Current/last price in USD
    change_pct: float        # % change as decimal
    trend_5d: str            # "up" | "down" | "flat"
    affected_sectors: list[str]  # ["OMC", "Aviation", "Paints"]
    impact_summary: str      # "Crude down 1.2% — positive for OMCs"
    source: str
    fetched_at: str
```

#### FlowData

```python
@dataclass
class FlowData:
    """Output of FII/DII ingestion"""
    date: str                # YYYY-MM-DD
    fii_buy: float           # In crores (₹)
    fii_sell: float
    fii_net: float
    dii_buy: float
    dii_sell: float
    dii_net: float
    fii_5d_trend: str        # "net_buyer" | "net_seller" | "mixed"
    fii_10d_trend: str
    dii_5d_trend: str
    signal: str              # "STRONG_BULLISH" | "CAUTIOUS_BULLISH" |
                             # "BEARISH" | "ROTATION" | "NEUTRAL"
    interpretation: str      # Human-readable explanation
    source: str
    fetched_at: str
```

#### GeoSignal

```python
@dataclass
class GeoSignal:
    """Output of geopolitics ingestion (per signal)"""
    headline: str
    summary: str             # 1-line LLM summary
    source: str              # "newsapi", "gdelt", "reddit", etc.
    source_url: str          # Original article/post URL
    published_at: str        # ISO 8601
    market_impact: str       # "high" | "medium"
    sentiment: str           # "bullish" | "bearish" | "neutral"
    affected_sectors: list[str]
    urgency: int             # 1-5 (5 = act now)
    fetched_at: str
```

#### CentralBankEvent

```python
@dataclass
class CentralBankEvent:
    """Output of central_banks ingestion"""
    bank: str                # "RBI", "Fed", "ECB", etc.
    event_type: str          # "rate_decision" | "speech" | "minutes" |
                             # "circular" | "policy_statement"
    title: str
    date: str
    tone: str | None         # "hawkish" | "dovish" | "neutral" | None
    impact_summary: str
    affected_sectors: list[str]
    is_scheduled: bool       # From calendar vs breaking
    source: str
    fetched_at: str
```

#### EarningsInfo

```python
@dataclass
class EarningsInfo:
    """Output of earnings ingestion"""
    blackout_stocks: list[str]        # Symbols reporting in next 2 days
    domestic_upcoming: list[dict]     # [{symbol, date, quarter}]
    international_relevant: list[dict] # [{company, date, indian_proxies}]
    fetched_at: str
```

#### EquityOHLCV

```python
@dataclass
class EquityOHLCV:
    """Output of indian_equities ingestion (per stock)"""
    symbol: str              # "RELIANCE", "TCS", etc.
    exchange: str            # "NSE" | "BSE"
    ohlcv: pd.DataFrame      # Columns: date, open, high, low, close, volume
                             # Last 200 trading days
    latest_quote: dict | None  # Real-time: {price, bid, ask, volume, timestamp}
    in_fno_ban: bool
    sector: str
    market_cap_cr: float     # In crores
    source: str              # "broker_api" | "yfinance" | "jugaad"
    fetched_at: str
```

#### TechnicalSignal

```python
@dataclass
class TechnicalSignal:
    """Output of technical analysis (per stock)"""
    symbol: str
    score: int               # 0-100
    direction: str           # "LONG" | "SHORT" | "NEUTRAL"
    reasons: list[str]       # ["MACD bullish crossover", "RSI bouncing from oversold"]
    indicators: dict         # Full indicator values for reference
    atr: float               # Latest ATR value (used for SL/TP)
    support_levels: list[float]
    resistance_levels: list[float]
```

#### FundamentalScore

```python
@dataclass
class FundamentalScore:
    """Output of fundamental quick-check (per stock)"""
    symbol: str
    score: int               # 0-100
    pe_ratio: float | None
    pe_vs_sector: str        # "below" | "in_range" | "above"
    promoter_holding_pct: float | None
    promoter_change_qoq: float | None  # +/- percentage points
    debt_to_equity: float | None
    roe: float | None
    reasons: list[str]
```

#### MacroScore

```python
@dataclass
class MacroScore:
    """Computed from FII/DII + commodities + geopolitics + central bank"""
    symbol: str
    sector: str
    score: int               # 0-100
    components: dict         # {fii_dii: 25, sector_tailwind: 20, geo_risk: 25, ...}
    reasons: list[str]
```

#### CompositeScore

```python
@dataclass
class CompositeScore:
    """Output of ranker — final scored stock"""
    symbol: str
    sector: str
    technical_score: int
    macro_score: int
    fundamental_score: int
    composite: float         # Weighted combination
    direction: str           # "LONG" | "SHORT"
    reasons: list[str]       # Aggregated from all analyses
    rank: int                # 1, 2, 3...
```

#### TradePlan

```python
@dataclass
class TradePlan:
    """Output of trade plan generator — the final recommendation"""
    symbol: str
    direction: str           # "LONG" | "SHORT"
    sector: str

    # Price levels
    entry_price: float
    stop_loss: float
    stop_loss_pct: float     # As decimal (0.0275 = 2.75%)
    target_1: float
    target_2: float
    rr_ratio: float          # Risk:Reward

    # Position sizing
    position_size: int       # Number of shares
    position_value: float    # ₹ total
    max_loss: float          # ₹ max risk

    # Meta
    confidence: str          # "HIGH" | "MEDIUM"
    max_hold_days: int       # Default 3
    exit_rules: list[str]    # Human-readable exit conditions

    # Scoring breakdown
    technical_score: int
    macro_score: int
    fundamental_score: int
    composite_score: float
    reasons: list[str]       # Why this trade

    # Timestamps
    generated_at: str
```

#### DailyBriefing

```python
@dataclass
class DailyBriefing:
    """Aggregated output — everything needed for morning Telegram message"""
    date: str
    markets: list[MarketSnapshot]
    commodities: list[CommoditySnapshot]
    flows: FlowData
    central_bank: list[CentralBankEvent]
    geo_signals: list[GeoSignal]
    climate_alerts: list[dict]   # Any active weather/disaster alerts
    trade_plans: list[TradePlan] # 0-3 trades (0 = no trade day)
    no_trade_reason: str | None  # If 0 trades, why
    generated_at: str
```

---

## 6. Database Design

### 6.1 Database Choice

**SQLite via aiosqlite.** Reasons:
- Single-instance system (one VPS, one process)
- No need for concurrent writes from multiple services
- Zero ops — no database server to manage
- File-based — easy backup, easy Docker volume mount
- Sufficient for the data volume (~50-100 rows/day)

**File location:** `db/trading.db` (mounted as Docker volume)

### 6.2 Schema

#### Table: `trades`

The trade journal. Every trade the system recommends, whether taken or not.

```sql
CREATE TABLE trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    system          TEXT NOT NULL,          -- 'india' | 'us'
    date            TEXT NOT NULL,          -- YYYY-MM-DD (trade date)
    symbol          TEXT NOT NULL,
    sector          TEXT,
    direction       TEXT NOT NULL,          -- 'LONG' | 'SHORT'
    status          TEXT NOT NULL DEFAULT 'planned',
                    -- 'planned' | 'entered' | 'partial_exit' | 'closed' | 'cancelled' | 'skipped'

    -- Plan (generated by system)
    entry_price     REAL NOT NULL,
    stop_loss       REAL NOT NULL,
    stop_loss_pct   REAL NOT NULL,
    target_1        REAL NOT NULL,
    target_2        REAL,
    rr_ratio        REAL NOT NULL,
    position_size   INTEGER NOT NULL,
    position_value  REAL NOT NULL,
    max_risk        REAL NOT NULL,
    confidence      TEXT NOT NULL,          -- 'HIGH' | 'MEDIUM'
    max_hold_days   INTEGER NOT NULL DEFAULT 3,

    -- Execution (filled when trade is taken/closed)
    actual_entry    REAL,
    entry_time      TEXT,                   -- ISO 8601
    actual_exit     REAL,
    exit_time       TEXT,
    exit_reason     TEXT,
                    -- 'target_1' | 'target_2' | 'stop_loss' | 'trailing_sl'
                    -- | 'eod_exit' | 'manual' | 'time_expiry'

    -- Result (computed on close)
    pnl             REAL,                   -- ₹ profit/loss
    pnl_pct         REAL,                   -- As decimal
    hold_hours      REAL,                   -- Duration in hours

    -- Scores (what drove the pick)
    technical_score  INTEGER,
    macro_score      INTEGER,
    fundamental_score INTEGER,
    composite_score  REAL,
    reasons          TEXT,                   -- JSON array of strings

    -- Timestamps
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_trades_system_date ON trades(system, date);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
```

#### Table: `signals`

Daily snapshot of all signals the system processed. For audit trail and feedback loop accuracy computation.

```sql
CREATE TABLE signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    system          TEXT NOT NULL,          -- 'india' | 'us'
    date            TEXT NOT NULL,          -- YYYY-MM-DD
    signal_type     TEXT NOT NULL,
                    -- 'market' | 'commodity' | 'fii_dii' | 'geopolitics'
                    -- | 'central_bank' | 'earnings' | 'technical' | 'sentiment'
                    -- | 'climate'
    symbol          TEXT,                   -- NULL for macro signals
    direction       TEXT,                   -- 'bullish' | 'bearish' | 'neutral' | NULL
    score           INTEGER,               -- 0-100 or NULL
    data            TEXT NOT NULL,          -- Full JSON payload
    source          TEXT NOT NULL,          -- Provider name
    was_correct     INTEGER,               -- 1/0/NULL — filled retroactively
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_signals_system_date ON signals(system, date);
CREATE INDEX idx_signals_type ON signals(signal_type);
```

#### Table: `daily_kpis`

Computed metrics per trading day.

```sql
CREATE TABLE daily_kpis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    system          TEXT NOT NULL,
    date            TEXT NOT NULL,
    trades_taken    INTEGER NOT NULL DEFAULT 0,
    wins            INTEGER NOT NULL DEFAULT 0,
    losses          INTEGER NOT NULL DEFAULT 0,
    no_trade        INTEGER NOT NULL DEFAULT 0,   -- 1 if no trade day
    net_pnl         REAL NOT NULL DEFAULT 0,
    net_pnl_pct     REAL NOT NULL DEFAULT 0,
    win_rate        REAL,
    profit_factor   REAL,                          -- gross_profit / gross_loss
    max_drawdown    REAL,                          -- Peak-to-trough (rolling)
    data            TEXT,                           -- Full KPI JSON blob
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(system, date)
);
```

#### Table: `weight_history`

Track composite scoring weight changes over time.

```sql
CREATE TABLE weight_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    system          TEXT NOT NULL,
    date            TEXT NOT NULL,
    technical_wt    REAL NOT NULL,
    macro_wt        REAL NOT NULL,
    fundamental_wt  REAL NOT NULL,
    trigger         TEXT NOT NULL,          -- 'initial' | 'auto_tune' | 'manual'
    reason          TEXT,                   -- Why weights changed
    prev_technical  REAL,
    prev_macro      REAL,
    prev_fundamental REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

#### Table: `ingestion_log`

Health monitoring for all data providers.

```sql
CREATE TABLE ingestion_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    system          TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    provider        TEXT NOT NULL,          -- 'yfinance' | 'jugaad' | 'newsapi' | etc.
    module          TEXT NOT NULL,          -- 'overnight_global' | 'fii_dii' | etc.
    status          TEXT NOT NULL,          -- 'success' | 'fallback' | 'failure'
    latency_ms      INTEGER,
    data_points     INTEGER,               -- How many records returned
    error           TEXT,                   -- Error message if any
    fallback_used   TEXT,                   -- Which fallback provider was used
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_ingestion_system_date ON ingestion_log(system, timestamp);
CREATE INDEX idx_ingestion_status ON ingestion_log(status);
```

#### Table: `alerts_sent`

Log of all Telegram messages for audit.

```sql
CREATE TABLE alerts_sent (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    system          TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    alert_type      TEXT NOT NULL,
                    -- 'morning_briefing' | 'trade_alert' | 'prep_alert'
                    -- | 'entry_trigger' | 'watchpoint' | 'target_hit'
                    -- | 'sl_hit' | 'exit_reminder' | 'weekly_review'
                    -- | 'system_error' | 'risk_breach'
    symbol          TEXT,                   -- NULL for briefings/reviews
    content_hash    TEXT,                   -- Hash of message content (avoid dupes)
    telegram_msg_id TEXT,                   -- Telegram message ID
    status          TEXT NOT NULL,          -- 'sent' | 'failed'
    error           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 6.3 Entity Relationship Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    trades    │     │   signals    │     │  daily_kpis  │
│              │     │              │     │              │
│ id (PK)      │     │ id (PK)      │     │ id (PK)      │
│ system       │     │ system       │     │ system       │
│ date ────────┼─────│ date         │─────│ date         │
│ symbol ──────┼─┐   │ signal_type  │     │ trades_taken │
│ direction    │ │   │ symbol       │     │ net_pnl      │
│ status       │ │   │ direction    │     │ win_rate     │
│ entry_price  │ │   │ score        │     │ ...          │
│ stop_loss    │ │   │ data (JSON)  │     └──────────────┘
│ target_1/2   │ │   │ was_correct  │
│ pnl          │ │   └──────────────┘     ┌──────────────┐
│ composite    │ │                         │weight_history│
│ reasons(JSON)│ │   ┌──────────────┐     │              │
│ ...          │ │   │ingestion_log │     │ id (PK)      │
└──────────────┘ │   │              │     │ system       │
                 │   │ id (PK)      │     │ date         │
                 │   │ system       │     │ tech_wt      │
                 │   │ provider     │     │ macro_wt     │
                 │   │ module       │     │ fund_wt      │
                 │   │ status       │     │ trigger      │
                 │   │ latency_ms   │     └──────────────┘
                 │   │ error        │
                 │   └──────────────┘     ┌──────────────┐
                 │                         │ alerts_sent  │
                 │                         │              │
                 └─────────────────────────│ symbol       │
                                           │ alert_type   │
                                           │ status       │
                                           └──────────────┘

Relationships:
- trades.date → daily_kpis.date (1:1 per system per day, computed from trades)
- trades.symbol → signals.symbol (many signals per trade)
- signals.date → daily_kpis.date (signals feed KPI accuracy computation)
- No foreign keys enforced (SQLite simplicity) — application-level integrity
```

### 6.4 Data Retention Policy

| Table | Retention | Reason |
|-------|-----------|--------|
| trades | Forever | Core audit trail, never delete |
| signals | 90 days | Feedback loop needs 4 weeks, 90 days gives buffer |
| daily_kpis | Forever | Small rows, valuable for long-term analysis |
| weight_history | Forever | Small rows, track system evolution |
| ingestion_log | 30 days | Health monitoring, prune old entries |
| alerts_sent | 60 days | Audit, prune old entries |

Pruning runs as a weekly scheduled job.

---

## 7. Internal API Contracts

### 7.1 Provider Contract

Every provider implements this interface:

```python
@dataclass
class ProviderResult:
    """Standard return type for all providers"""
    success: bool
    data: Any                # Raw API response (dict, list, DataFrame)
    provider: str            # Provider name for logging
    latency_ms: int          # How long the call took
    error: str | None        # Error message if failed
    metadata: dict | None    # Optional extra info (rate limits, etc.)
```

**Provider method signature pattern:**

```python
class SomeProvider:
    async def fetch_something(self, params...) -> ProviderResult:
        """
        - MUST use httpx with timeout
        - MUST be wrapped in tenacity retry
        - MUST return ProviderResult (never raise to caller)
        - MUST log the call via shared logger
        - Returns raw API data — no normalization
        """
```

### 7.2 Transformer Contract

Every transformer implements:

```python
class SomeTransformer:
    def normalize(self, raw_data: Any, source: str) -> list[SomeSchema]:
        """
        - Input: raw provider data
        - Output: list of typed dataclass instances
        - MUST handle missing/malformed fields gracefully
        - MUST NOT make any API calls
        - MUST NOT raise exceptions (log and skip bad records)
        """
```

### 7.3 Ingestion Contract

Every ingestion module exposes one main async function:

```python
async def fetch_and_process() -> IngestionResult:
    """
    1. Call provider(s) — with fallback chain
    2. Pass raw data through transformer
    3. Log to ingestion_log table
    4. Return standardized output

    Returns:
        IngestionResult with .data (typed schemas) and .metadata
    """
```

```python
@dataclass
class IngestionResult:
    success: bool
    data: list[Any]          # List of typed schema objects
    partial: bool            # True if some sources failed but we got data
    errors: list[str]        # Any error messages
    sources_used: list[str]  # Which providers actually returned data
    fetched_at: str
```

### 7.4 Analysis Contract

```python
# Technical
async def analyze_technicals(equities: list[EquityOHLCV]) -> list[TechnicalSignal]

# Fundamental
async def analyze_fundamentals(symbols: list[str]) -> list[FundamentalScore]

# Sentiment
async def analyze_sentiment(geo_signals: list[GeoSignal],
                            central_bank: list[CentralBankEvent]) -> dict[str, float]
    # Returns: {sector: sentiment_score}

# Correlation / Macro
def compute_macro_scores(flows: FlowData,
                         commodities: list[CommoditySnapshot],
                         geo_signals: list[GeoSignal],
                         central_bank: list[CentralBankEvent],
                         symbols: list[str]) -> list[MacroScore]

# Risk Engine
def validate_trade(plan: TradePlan,
                   current_positions: list[TradePlan],
                   india_vix: float,
                   day_of_week: int) -> tuple[bool, list[str]]
    # Returns: (is_valid, rejection_reasons)
```

### 7.5 Strategy Contract

```python
# Screener
def screen_universe(equities: list[EquityOHLCV],
                    earnings: EarningsInfo) -> list[str]
    # Returns: filtered symbol list

# Ranker
def rank_stocks(technicals: list[TechnicalSignal],
                macros: list[MacroScore],
                fundamentals: list[FundamentalScore],
                weights: dict) -> list[CompositeScore]
    # Returns: sorted by composite score, top N

# Trade Plan
def generate_plan(scored: CompositeScore,
                  technical: TechnicalSignal,
                  capital: float) -> TradePlan | None
    # Returns: None if risk rules reject the trade
```

### 7.6 Delivery Contract

```python
# Telegram
async def send_message(chat_id: str, text: str, parse_mode: str = "MarkdownV2") -> bool

# Formatter
def format_morning_briefing(briefing: DailyBriefing) -> str
def format_trade_alert(plan: TradePlan, trade_number: int) -> str
def format_prep_alert(symbol: str, current_price: float) -> str
def format_entry_trigger(symbol: str, price: float, volume_ratio: float) -> str
def format_target_hit(symbol: str, target: int, price: float) -> str
def format_sl_hit(symbol: str, price: float) -> str
def format_exit_reminder(symbol: str, price: float) -> str
def format_weekly_review(kpis: dict) -> str

# Notifier
async def monitor_positions(positions: list[TradePlan]) -> None
    # Runs in loop during market hours, sends alerts via telegram
```

### 7.7 Review Contract

```python
# Journal
async def log_trade(trade: TradePlan, status: str) -> int  # Returns trade ID
async def update_trade(trade_id: int, **updates) -> None
async def close_trade(trade_id: int, exit_price: float, exit_reason: str) -> None

# KPI Tracker
async def compute_daily_kpis(system: str, date: str) -> dict
async def compute_weekly_kpis(system: str, week_start: str) -> dict
async def compute_rolling_kpis(system: str, weeks: int = 4) -> dict

# Weekly Review
async def generate_weekly_review(system: str) -> str  # Returns formatted message

# Feedback Loop
async def auto_tune_weights(system: str) -> dict  # Returns new weights
```

---

## 8. Provider Abstraction Layer

### 8.1 Fallback Chains

Each ingestion module has a defined fallback chain. If the primary provider fails, it tries the next one.

**India System:**

| Module | Primary | Fallback 1 | Fallback 2 | Degraded |
|--------|---------|------------|------------|----------|
| Overnight Global | yfinance | — | — | Skip (non-critical) |
| Commodities | yfinance | — | — | Skip (non-critical) |
| FII/DII | NSE API | jugaad-data | MoneyControl scrape | ALERT — critical |
| Geopolitics | NewsAPI + GDELT | RSS feeds only | — | Reduced signal set |
| Social (Twitter) | Apify | — | — | Skip social signals |
| Social (Reddit) | PRAW | — | — | Skip social signals |
| Central Banks | FRED + RSS | NewsAPI search | — | Reduced policy data |
| Earnings | Trendlyne scrape | MoneyControl | yfinance cal | Empty blackout list |
| Indian Equities | Broker API | yfinance | jugaad-data | ALERT — critical |

**US System:**

| Module | Primary | Fallback 1 | Fallback 2 | Degraded |
|--------|---------|------------|------------|----------|
| US Markets | Polygon.io | yfinance | — | ALERT — critical |
| Pre-Market | Polygon.io | — | — | ALERT — critical |
| Geopolitics | NewsAPI + GDELT | RSS feeds | — | Reduced signals |
| Earnings | Polygon.io | yfinance | — | Reduced data |
| Fed Policy | FRED + RSS | NewsAPI | — | Reduced data |
| US Equities | Polygon.io | yfinance | — | ALERT — critical |

### 8.2 Provider Registration Pattern

```python
# Each provider registers its capabilities
PROVIDER_REGISTRY = {
    "yfinance": {
        "capabilities": ["market_data", "commodities", "fundamentals", "earnings"],
        "rate_limit": None,  # No formal limit (be respectful)
        "latency": "1-3s",
        "reliability": "medium",
        "cost": "free"
    },
    "newsapi": {
        "capabilities": ["news"],
        "rate_limit": "100/day (free) or 1000/day (paid)",
        "latency": "<1s",
        "reliability": "high",
        "cost": "free tier"
    },
    # ...
}
```

---

## 9. Storage Strategy

### 9.1 What Gets Stored Where

| Data Type | Storage | Format | Reason |
|-----------|---------|--------|--------|
| Trade journal | SQLite `trades` table | Structured rows | Core audit, queries, KPI computation |
| Daily signals | SQLite `signals` table | Row + JSON blob | Audit trail, feedback loop accuracy |
| KPIs | SQLite `daily_kpis` table | Structured rows | Performance tracking |
| Config/settings | YAML files on disk | YAML | Human-editable, version-controlled |
| Risk params | YAML on disk | YAML | Non-negotiable rules, version-controlled |
| API responses (raw) | NOT stored | — | Too much volume, not needed long-term |
| Logs | File on disk (`logs/`) | Structured text | Rotating, 10MB x 5 files |
| Central bank calendar | JSON on disk | JSON | Manual + auto-updated |

### 9.2 Backup Strategy

```
Daily (6:30 PM IST):
  cp db/trading.db db/backups/trading_$(date +%Y%m%d).db

Weekly:
  Keep last 4 daily backups, delete older

Monthly:
  Archive one backup to cloud storage (optional V2)
```

---

## 10. Scheduling & Timing

### 10.1 India System Schedule (All times IST)

```
┌──────────┬────────────────────────────────────────────────────┐
│   Time   │ Job                                                │
├──────────┼────────────────────────────────────────────────────┤
│ 08:45    │ run_all_ingestion()                                │
│          │   → overnight_global, commodities, fii_dii,        │
│          │     geopolitics, central_banks, earnings,           │
│          │     indian_equities (OHLCV)                         │
├──────────┼────────────────────────────────────────────────────┤
│ 08:55    │ run_analysis_and_strategy()                         │
│          │   → technical, fundamental, sentiment, correlation, │
│          │     screener, ranker, trade_plan, risk_gate         │
├──────────┼────────────────────────────────────────────────────┤
│ 09:00    │ send_morning_briefing()                             │
│          │   → Telegram: full market pulse message             │
├──────────┼────────────────────────────────────────────────────┤
│ 09:05    │ send_trade_alerts()                                 │
│          │   → Telegram: individual trade alert per pick       │
├──────────┼────────────────────────────────────────────────────┤
│ 09:25    │ send_prep_alerts()                                  │
│          │   → Telegram: "Get ready, BPCL at ₹342.50"         │
├──────────┼────────────────────────────────────────────────────┤
│ 09:30-   │ monitor_positions() [every 5 min]                  │
│ 15:25    │   → Poll prices, check SL/TP, send alerts          │
├──────────┼────────────────────────────────────────────────────┤
│ 15:15    │ send_exit_reminders()                               │
│          │   → Telegram: "Day 3 exit reminder" for expiring    │
├──────────┼────────────────────────────────────────────────────┤
│ 18:00    │ log_daily_trades()                                  │
│          │   → Journal trades, compute daily KPIs              │
├──────────┼────────────────────────────────────────────────────┤
│ Sat 10:00│ generate_weekly_review()                            │
│          │   → Compile week, send Telegram report              │
├──────────┼────────────────────────────────────────────────────┤
│ Sat 10:30│ run_feedback_loop()                                 │
│          │   → Auto-tune weights, safety checks                │
├──────────┼────────────────────────────────────────────────────┤
│ Sun 02:00│ run_maintenance()                                   │
│          │   → Prune old logs, backup DB, health check         │
└──────────┴────────────────────────────────────────────────────┘

Days: Mon-Fri only (except weekend review/maintenance)
Holidays: Check NSE holiday calendar — skip trading days
```

### 10.2 US System Schedule (All times ET)

```
┌──────────┬────────────────────────────────────────────────────┐
│ Time(ET) │ Job                                                │
├──────────┼────────────────────────────────────────────────────┤
│ 08:30    │ run_all_ingestion()                                │
│          │   → us_markets, pre_market, geopolitics,           │
│          │     earnings, fed_policy, us_equities              │
├──────────┼────────────────────────────────────────────────────┤
│ 08:50    │ run_analysis_and_strategy()                         │
├──────────┼────────────────────────────────────────────────────┤
│ 09:00    │ send_morning_briefing()                             │
├──────────┼────────────────────────────────────────────────────┤
│ 09:05    │ send_trade_alerts()                                 │
├──────────┼────────────────────────────────────────────────────┤
│ 09:25    │ send_prep_alerts()                                  │
├──────────┼────────────────────────────────────────────────────┤
│ 09:30-   │ monitor_positions() [every 5 min]                  │
│ 15:55    │                                                     │
├──────────┼────────────────────────────────────────────────────┤
│ 15:50    │ send_exit_reminders()                               │
├──────────┼────────────────────────────────────────────────────┤
│ 17:00    │ log_daily_trades()                                  │
├──────────┼────────────────────────────────────────────────────┤
│ Sat 10:00│ generate_weekly_review()                            │
├──────────┼────────────────────────────────────────────────────┤
│ Sat 10:30│ run_feedback_loop()                                 │
└──────────┴────────────────────────────────────────────────────┘

Days: Mon-Fri only (check US market holiday calendar)
```

---

## 11. Error Handling & Resilience

### 11.1 Error Hierarchy

```
Level 1 — RECOVERABLE (handle automatically)
  │ Provider timeout → retry with backoff (tenacity)
  │ Provider error → try fallback provider
  │ Malformed data → skip record, log warning
  │ LLM rate limit → exponential backoff, retry
  │
Level 2 — DEGRADED (continue with partial data)
  │ All providers for a non-critical module fail
  │   → Log error, skip module, note in briefing
  │   → Example: Twitter fails → briefing still sends, minus social signals
  │
Level 3 — CRITICAL (alert user, continue cautiously)
  │ Critical module fails (FII/DII, Indian equities, broker API)
  │   → Send Telegram alert: "⚠️ FII/DII data unavailable"
  │   → System still runs but flags reduced confidence
  │   → Consider "NO TRADE TODAY" if too many critical failures
  │
Level 4 — FATAL (alert user, system pauses)
  │ DB failure, Telegram bot crash, scheduler crash
  │   → Send emergency alert (if Telegram works)
  │   → Log to file
  │   → Attempt automatic restart (Docker restart policy)
```

### 11.2 Retry Policy (tenacity)

```python
# Standard retry config for all providers
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=30),
    "retry": retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    "before_sleep": log_retry_attempt,
}
```

### 11.3 Circuit Breaker (Simple)

If a provider fails 5 consecutive times within 1 hour:
- Mark provider as "down"
- Skip it for 15 minutes
- Try again after cooldown
- Alert via Telegram: "Provider X marked down"

---

## 12. Logging & Observability

### 12.1 Log Format

```json
{
  "timestamp": "2026-03-07T08:45:23.456+05:30",
  "level": "INFO",
  "system": "india",
  "module": "ingestion.fii_dii",
  "message": "FII/DII data fetched successfully",
  "provider": "jugaad",
  "latency_ms": 1234,
  "data_points": 1,
  "extra": {}
}
```

### 12.2 What Gets Logged

| Event | Level | Fields |
|-------|-------|--------|
| API call start | DEBUG | provider, endpoint, params |
| API call success | INFO | provider, latency_ms, data_points |
| API call failure | WARNING | provider, error, status_code |
| Fallback activated | WARNING | from_provider, to_provider, reason |
| All providers failed | ERROR | module, providers_tried |
| Signal generated | INFO | type, direction, urgency, sector |
| Stock screened in | DEBUG | symbol, score, reason |
| Stock screened out | DEBUG | symbol, reason |
| Trade plan generated | INFO | symbol, direction, entry, sl, tp, rr |
| Trade plan rejected | INFO | symbol, reason (which risk rule) |
| Risk rule evaluation | DEBUG | rule, value, threshold, pass/fail |
| Telegram sent | INFO | alert_type, symbol, msg_id |
| Telegram failed | ERROR | alert_type, error |
| Weight change | INFO | old_weights, new_weights, trigger |
| KPI computed | INFO | date, net_pnl, win_rate |
| DB operation | DEBUG | table, operation, rows |
| Scheduler job start | INFO | job_name |
| Scheduler job end | INFO | job_name, duration_ms |
| Scheduler job error | ERROR | job_name, error |

### 12.3 Log Destinations

| Destination | Level | Format | Retention |
|-------------|-------|--------|-----------|
| Console (stdout) | INFO+ | Human-readable | Session only |
| File (`logs/trading.log`) | DEBUG+ | JSON | 10MB x 5 rotation |
| Telegram (critical) | ERROR+ | Alert message | Via alerts_sent table |

---

## 13. Security & Secrets

### 13.1 Secret Management

- All secrets in `.env` file (never committed)
- `.env.example` committed with empty values
- `utils/config.py` is the single access point
- No inline `os.getenv()` anywhere in codebase

### 13.2 .env Structure

```env
# ─── SHARED ───
TELEGRAM_BOT_TOKEN=
TELEGRAM_INDIA_CHAT_ID=
TELEGRAM_US_CHAT_ID=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
FRED_API_KEY=
NEWSAPI_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=trading-system/1.0
APIFY_TOKEN=
OPENWEATHER_API_KEY=

# ─── INDIA ───
INDIA_BROKER=dhan              # 'dhan' | 'breeze' | 'kite'
INDIA_BROKER_API_KEY=
INDIA_BROKER_API_SECRET=
INDIA_CAPITAL=500000

# ─── US ───
POLYGON_API_KEY=
ROBINHOOD_USERNAME=
ROBINHOOD_PASSWORD=
ROBINHOOD_MFA_CODE=            # Or TOTP secret
US_CAPITAL=

# ─── RISK (defaults, overridable in config YAML) ───
MAX_LOSS_PER_TRADE_PCT=0.02
MAX_CONCURRENT_TRADES=3
MIN_RR_RATIO=2.0
```

### 13.3 Security Rules

- `.env` in `.gitignore` — never committed
- No API keys in logs (masked in log output)
- No secrets in error messages sent to Telegram
- Robinhood credentials handled with extra care (unofficial API)

---

## 14. Deployment Architecture

### 14.1 V1 — Single VPS

```
┌─────────────────────────────────────────┐
│             VPS (2-4GB RAM)             │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │         Docker Container        │    │
│  │                                 │    │
│  │  main.py (entry point)          │    │
│  │    ├── India scheduler (IST)    │    │
│  │    ├── US scheduler (ET)        │    │
│  │    └── Telegram bot (shared)    │    │
│  │                                 │    │
│  │  Volumes:                       │    │
│  │    /app/db → host db/           │    │
│  │    /app/logs → host logs/       │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                         │
│  SQLite file: db/trading.db             │
│  Logs: logs/trading.log                 │
└─────────────────────────────────────────┘
```

### 14.2 Resource Estimates

| Resource | Estimate | Notes |
|----------|----------|-------|
| RAM idle | ~200MB | Python process + SQLite |
| RAM peak | ~500MB | During Nifty 200 technical analysis |
| CPU | Low | Bursty: 2-3 min every morning, idle rest |
| Disk | < 1GB | DB grows ~5MB/month, logs rotate |
| Network | Low | API calls: ~100-200/day India, more for US |

### 14.3 Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```yaml
# docker-compose.yaml
version: '3.8'
services:
  trading-bot:
    build: .
    env_file: .env
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Appendix A: Sector Mapping

### India — Commodity Impact Map

| Commodity | Direction | Affected Sectors | Impact |
|-----------|-----------|-----------------|--------|
| Crude Oil ↓ | Bullish | OMC (BPCL, HPCL, IOC), Aviation (IndiGo, SpiceJet), Paints (Asian, Berger), Tyres (MRF, Apollo) | Lower input costs |
| Crude Oil ↑ | Bearish | Same sectors | Higher input costs |
| Gold ↑ | Mixed | Jewellery (Titan, Kalyan) — revenue up but margin pressure | Volume vs margin |
| Natural Gas ↑ | Bearish | Fertilizer (Chambal, GNFC), Power, GAIL | Input cost increase |
| Copper ↑ | Bullish | Infra capex signal (Hindalco, Vedanta) | Demand indicator |
| USD/INR ↑ | Bullish IT | IT (TCS, Infy, Wipro), Pharma | Export earners benefit |
| USD/INR ↑ | Bearish | Oil importers, companies with USD debt | Import cost up |
| Steel ↑ | Bullish | Tata Steel, JSW, SAIL | Revenue up |
| Cotton ↑ | Bearish | Textiles (Arvind, Vardhman) | Input cost up |

### India — FII/DII Flow Signal Matrix

| FII | DII | Signal | Interpretation |
|-----|-----|--------|---------------|
| Net Buy > ₹1000 Cr | Net Buy > ₹500 Cr | STRONG_BULLISH | Both buying aggressively |
| Net Buy > ₹1000 Cr | Net Sell > ₹500 Cr | CAUTIOUS_BULLISH | FII buying but DII distributing |
| Net Sell > ₹2000 Cr | Any | BEARISH | Heavy FII selling — risk-off |
| Net Sell > ₹1000 Cr | Net Buy > ₹1000 Cr | ROTATION | FII selling, DII absorbing — sector rotation |
| Mixed | Mixed | NEUTRAL | No strong directional bias |

### India — International Earnings → Indian Proxy Map

| International Company Type | Indian Proxies |
|---------------------------|----------------|
| US Big Tech (MSFT, GOOG, META) | TCS, Infosys, Wipro, HCLTech, LTIMindtree |
| Global Banks (JPM, GS, HSBC) | HDFC Bank, ICICI Bank, Kotak, SBI |
| Oil Majors (XOM, CVX, Shell) | ONGC, Reliance, BPCL, IOC |
| Mining (BHP, Rio Tinto) | Tata Steel, Hindalco, Vedanta |

---

## Appendix B: Risk Rules (Non-Negotiable)

### India System

| Rule | Value | Enforcement |
|------|-------|-------------|
| Max loss per trade | 2% of capital | Position sizing formula |
| Max concurrent trades | 3 | Check before new trade |
| Min risk:reward | 1:2.0 | Reject if R:R < 2.0 |
| Max stop loss width | 3% from entry | Reject if SL > 3% |
| Max hold duration | 3 trading days | Mandatory exit Day 3 EOD |
| No trade first 15 min | Skip 9:15-9:30 AM | Entry window starts 9:30 |
| High VIX block | India VIX > 22 | No longs (shorts allowed) |
| Min qualifying picks | 2 | If < 2, "NO TRADE TODAY" |
| Max sector concentration | 2 trades same sector | Block 3rd same-sector trade |
| Friday position size | 50% normal | Weekend risk reduction |

### US System (To be defined when we build US)

Same framework, US-specific thresholds.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-07 | Initial design document |
