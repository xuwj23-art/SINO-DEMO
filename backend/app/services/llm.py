"""Anthropic generation wrapper for the demo backend."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from app.config import settings


class LlmConfigurationError(RuntimeError):
    """Raised when the LLM client cannot be configured safely."""


class LlmServiceError(RuntimeError):
    """Raised when the provider call fails."""


@lru_cache(maxsize=1)
def _client() -> Any:
    if not settings.anthropic_api_key:
        raise LlmConfigurationError("ANTHROPIC_API_KEY is required for /debug/llm.")

    try:
        import anthropic
    except ImportError as exc:
        raise LlmConfigurationError(
            "The 'anthropic' package is required for /debug/llm."
        ) from exc

    client_kwargs: dict[str, Any] = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        client_kwargs["base_url"] = settings.anthropic_base_url

    return anthropic.Anthropic(**client_kwargs)


def generate(
    system: str,
    messages: Sequence[Mapping[str, Any]],
    max_tokens: int = 4096,
) -> str:
    """Generate text with the configured Anthropic model.

    Callers pass already-sanitized, non-sensitive demo content only. This
    wrapper returns text blocks and never logs prompts or completions.
    """

    try:
        response = _client().messages.create(
            model=settings.gen_model,
            max_tokens=max_tokens,
            system=system,
            messages=list(messages),
        )
    except LlmConfigurationError:
        raise
    except Exception as exc:  # provider SDK errors vary by version
        raise LlmServiceError("Anthropic generation request failed.") from exc

    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts).strip()
