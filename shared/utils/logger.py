"""
Structured logging via loguru.

Every module imports `get_logger(__name__)` and uses the returned logger.
Output is structured JSON for machine parsing + human-readable for console.

Usage:
    from shared.utils.logger import get_logger
    logger = get_logger(__name__)

    logger.info("Fetched FII/DII data", provider="jugaad", latency_ms=342, data_points=5)
    logger.warning("Falling back", from_provider="jugaad", to_provider="nse_scraper", reason="timeout")
    logger.error("Provider failed", provider="yfinance", error=str(e))
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as _loguru_logger

# ─── Remove default loguru handler ───
_loguru_logger.remove()

# ─── Paths ───
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _ROOT_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

# ─── Structured format for file output ───
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS ZZ} | "
    "{level: <8} | "
    "{extra[module_name]} | "
    "{message} | "
    "{extra}"
)

# ─── Human-readable format for console ───
_CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[module_name]}</cyan> | "
    "{message}"
)

# ─── Console handler (stderr, human-readable) ───
_loguru_logger.add(
    sys.stderr,
    format=_CONSOLE_FORMAT,
    level="INFO",
    colorize=True,
    filter=lambda record: record["extra"].get("module_name") is not None,
)

# ─── File handler (structured, all levels) ───
_loguru_logger.add(
    str(_LOG_DIR / "trading_{time:YYYY-MM-DD}.log"),
    format=_FILE_FORMAT,
    level="DEBUG",
    rotation="00:00",  # New file every midnight
    retention="30 days",
    compression="gz",
    serialize=False,
    filter=lambda record: record["extra"].get("module_name") is not None,
)

# ─── Error-only file (quick scanning for issues) ───
_loguru_logger.add(
    str(_LOG_DIR / "errors_{time:YYYY-MM-DD}.log"),
    format=_FILE_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="gz",
    serialize=False,
    filter=lambda record: record["extra"].get("module_name") is not None,
)


def get_logger(name: str) -> _loguru_logger.__class__:
    """Get a logger bound to a module name.

    Args:
        name: Module name, typically __name__

    Returns:
        Loguru logger instance with module_name bound in extras.

    Example:
        logger = get_logger(__name__)
        logger.info("Data fetched", provider="yfinance", symbols=5, latency_ms=230)
    """
    return _loguru_logger.bind(module_name=name)


def log_api_call(
    logger,
    *,
    provider: str,
    endpoint: str = "",
    status: str,
    latency_ms: int,
    data_points: int = 0,
    error: str | None = None,
) -> None:
    """Standardized API call logging.

    Every external API call MUST be logged through this helper.

    Args:
        logger: Logger instance from get_logger()
        provider: Name of the data provider (e.g., "yfinance", "jugaad")
        endpoint: API endpoint or method called
        status: "success" | "fallback" | "failure"
        latency_ms: Round-trip time in milliseconds
        data_points: Number of data points returned
        error: Error message if status is "failure"
    """
    if status == "failure":
        logger.error(
            "API call failed",
            provider=provider,
            endpoint=endpoint,
            status=status,
            latency_ms=latency_ms,
            error=error,
        )
    elif status == "fallback":
        logger.warning(
            "API call used fallback",
            provider=provider,
            endpoint=endpoint,
            status=status,
            latency_ms=latency_ms,
            data_points=data_points,
        )
    else:
        logger.info(
            "API call succeeded",
            provider=provider,
            endpoint=endpoint,
            status=status,
            latency_ms=latency_ms,
            data_points=data_points,
        )


def log_fallback(
    logger,
    *,
    from_provider: str,
    to_provider: str,
    reason: str,
) -> None:
    """Standardized fallback logging.

    Every fallback activation MUST be logged through this helper.
    """
    logger.warning(
        "Provider fallback activated",
        from_provider=from_provider,
        to_provider=to_provider,
        reason=reason,
    )


def log_trade_decision(
    logger,
    *,
    symbol: str,
    score: float,
    direction: str,
    accepted: bool,
    rejection_reasons: list[str] | None = None,
) -> None:
    """Standardized trade decision logging.

    Every trade accept/reject MUST be logged through this helper.
    """
    if accepted:
        logger.info(
            "Trade accepted",
            symbol=symbol,
            score=score,
            direction=direction,
            accepted=True,
        )
    else:
        logger.info(
            "Trade rejected",
            symbol=symbol,
            score=score,
            direction=direction,
            accepted=False,
            rejection_reasons=rejection_reasons or [],
        )


def log_risk_check(
    logger,
    *,
    rule: str,
    value: float,
    threshold: float,
    passed: bool,
    symbol: str = "",
) -> None:
    """Standardized risk rule evaluation logging.

    Every risk rule check MUST be logged through this helper.
    """
    level = "info" if passed else "warning"
    getattr(logger, level)(
        "Risk rule evaluated",
        rule=rule,
        value=value,
        threshold=threshold,
        passed=passed,
        symbol=symbol,
    )
