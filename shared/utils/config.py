"""
Centralized configuration loader.

ALL env vars flow through this module. No inline os.getenv() anywhere else.
Config is loaded once at startup, validated, and exposed as a frozen object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ─── Load .env at import time ───
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT_DIR / ".env")


def _env(key: str, default: str | None = None, required: bool = False) -> str:
    """Get env var with validation."""
    value = os.environ.get(key, default)
    if required and not value:
        raise EnvironmentError(f"Required env var {key} is not set")
    return value or ""


def _env_float(key: str, default: float) -> float:
    """Get env var as float."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    return float(raw)


def _env_int(key: str, default: int) -> int:
    """Get env var as int."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    return int(raw)


# ─── Dataclass configs ───


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    india_chat_id: str
    us_chat_id: str


@dataclass(frozen=True)
class LLMConfig:
    anthropic_api_key: str
    openai_api_key: str


@dataclass(frozen=True)
class SharedProviderConfig:
    newsapi_key: str
    fred_api_key: str
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    apify_token: str
    openweather_api_key: str


@dataclass(frozen=True)
class IndiaBrokerConfig:
    broker: str  # "dhan" | "breeze" | "kite" | "yfinance_fallback"
    api_key: str
    api_secret: str
    capital: float


@dataclass(frozen=True)
class USBrokerConfig:
    polygon_api_key: str
    robinhood_username: str
    robinhood_password: str
    capital: float


@dataclass(frozen=True)
class RiskConfig:
    max_loss_per_trade_pct: float
    max_concurrent_trades: int
    min_rr_ratio: float
    # Additional risk params loaded from YAML per-system
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DBConfig:
    path: str


@dataclass(frozen=True)
class AppConfig:
    telegram: TelegramConfig
    llm: LLMConfig
    shared_providers: SharedProviderConfig
    india_broker: IndiaBrokerConfig
    us_broker: USBrokerConfig
    risk: RiskConfig
    db: DBConfig
    root_dir: Path


def _load_yaml(path: Path) -> dict:
    """Load a YAML file. Returns empty dict if file doesn't exist."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config() -> AppConfig:
    """Load full application config from env vars and YAML files.

    Call once at startup. Pass the returned AppConfig to modules that need it.
    """
    db_path = str(_ROOT_DIR / "db" / "trading.db")

    # Load risk overrides from YAML if available
    india_risk_yaml = _load_yaml(_ROOT_DIR / "india" / "config" / "risk_params.yaml")

    risk_extra = {}
    if india_risk_yaml:
        risk_extra = india_risk_yaml

    return AppConfig(
        telegram=TelegramConfig(
            bot_token=_env("TELEGRAM_BOT_TOKEN"),
            india_chat_id=_env("TELEGRAM_INDIA_CHAT_ID"),
            us_chat_id=_env("TELEGRAM_US_CHAT_ID"),
        ),
        llm=LLMConfig(
            anthropic_api_key=_env("ANTHROPIC_API_KEY"),
            openai_api_key=_env("OPENAI_API_KEY"),
        ),
        shared_providers=SharedProviderConfig(
            newsapi_key=_env("NEWSAPI_KEY"),
            fred_api_key=_env("FRED_API_KEY"),
            reddit_client_id=_env("REDDIT_CLIENT_ID"),
            reddit_client_secret=_env("REDDIT_CLIENT_SECRET"),
            reddit_user_agent=_env("REDDIT_USER_AGENT", "trading-system/1.0"),
            apify_token=_env("APIFY_TOKEN"),
            openweather_api_key=_env("OPENWEATHER_API_KEY"),
        ),
        india_broker=IndiaBrokerConfig(
            broker=_env("INDIA_BROKER", "yfinance_fallback"),
            api_key=_env("INDIA_BROKER_API_KEY"),
            api_secret=_env("INDIA_BROKER_API_SECRET"),
            capital=_env_float("INDIA_CAPITAL", 500000.0),
        ),
        us_broker=USBrokerConfig(
            polygon_api_key=_env("POLYGON_API_KEY"),
            robinhood_username=_env("ROBINHOOD_USERNAME"),
            robinhood_password=_env("ROBINHOOD_PASSWORD"),
            capital=_env_float("US_CAPITAL", 0.0),
        ),
        risk=RiskConfig(
            max_loss_per_trade_pct=_env_float("MAX_LOSS_PER_TRADE_PCT", 0.02),
            max_concurrent_trades=_env_int("MAX_CONCURRENT_TRADES", 3),
            min_rr_ratio=_env_float("MIN_RR_RATIO", 2.0),
            extra=risk_extra,
        ),
        db=DBConfig(path=db_path),
        root_dir=_ROOT_DIR,
    )


def load_system_config(system: str) -> dict:
    """Load system-specific settings.yaml.

    Args:
        system: "india" or "us"

    Returns:
        Dict from the system's settings.yaml
    """
    settings_path = _ROOT_DIR / system / "config" / "settings.yaml"
    return _load_yaml(settings_path)


def load_sources_config(system: str) -> dict:
    """Load system-specific sources.yaml (API endpoints, URLs, etc).

    Args:
        system: "india" or "us"

    Returns:
        Dict from the system's sources.yaml
    """
    sources_path = _ROOT_DIR / system / "config" / "sources.yaml"
    return _load_yaml(sources_path)
