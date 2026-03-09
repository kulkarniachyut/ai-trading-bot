"""LLM provider — text completions via Anthropic API."""

from __future__ import annotations

import time

import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.providers.base import ProviderResult, make_error_result
from shared.utils.config import AppConfig
from shared.utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

_PROVIDER = "llm_anthropic"
_DEFAULT_MODEL = "claude-3-haiku-20240307"
_DEFAULT_MAX_TOKENS = 512


class LLMProvider:
    """Sends prompts to Anthropic and returns raw text completions."""

    def __init__(self, config: AppConfig) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=config.llm.anthropic_api_key,
        )
        self._model = _DEFAULT_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(anthropic.RateLimitError),
        reraise=True,
    )
    async def complete(
        self,
        prompt: str,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        system: str | None = None,
    ) -> ProviderResult:
        """Send a prompt and return the completion text.

        Args:
            prompt: User message text
            max_tokens: Max tokens in response
            system: Optional system prompt

        Returns:
            ProviderResult.data = {"text": str, "input_tokens": int, "output_tokens": int}
        """
        t0 = time.monotonic()
        try:
            messages = [{"role": "user", "content": prompt}]
            kwargs: dict = {
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system

            response = await self._client.messages.create(**kwargs)
            text = response.content[0].text if response.content else ""
            latency = int((time.monotonic() - t0) * 1000)

            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="messages.create",
                status="success",
                latency_ms=latency,
                data_points=response.usage.output_tokens,
            )
            return ProviderResult(
                success=True,
                data={
                    "text": text,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                provider=_PROVIDER,
                latency_ms=latency,
                metadata={"model": self._model},
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            log_api_call(
                logger,
                provider=_PROVIDER,
                endpoint="messages.create",
                status="failure",
                latency_ms=latency,
                data_points=0,
                error=str(exc),
            )
            return make_error_result(_PROVIDER, str(exc), t0)
