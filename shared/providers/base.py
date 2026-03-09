"""Base types for all providers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResult:
    """Uniform return type for every provider call."""

    success: bool
    data: Any
    provider: str
    latency_ms: int
    error: str | None = None
    metadata: dict | None = None


def make_error_result(provider: str, error: str, t0: float) -> ProviderResult:
    """Build a failed ProviderResult from an exception."""
    return ProviderResult(
        success=False,
        data=None,
        provider=provider,
        latency_ms=int((time.monotonic() - t0) * 1000),
        error=error,
    )
