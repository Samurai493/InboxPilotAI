"""Per-request LLM API keys — never stored in LangGraph checkpoint state."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

_var: ContextVar[_Secrets | None] = ContextVar("llm_request_secrets", default=None)


@dataclass
class _Secrets:
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None


def _norm(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None


class LlmRequestSecrets:
    """Bind decrypted keys for the current call stack (e.g. one ``graph.invoke``)."""

    __slots__ = ("_token", "_payload",)

    def __init__(
        self,
        *,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        self._token: Token | None = None
        self._payload = _Secrets(
            openai_api_key=_norm(openai_api_key),
            anthropic_api_key=_norm(anthropic_api_key),
            gemini_api_key=_norm(gemini_api_key),
        )

    def __enter__(self) -> LlmRequestSecrets:
        self._token = _var.set(self._payload)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _var.reset(self._token)
            self._token = None


def get_request_llm_api_keys() -> tuple[str | None, str | None, str | None]:
    """Return (openai, anthropic, gemini) for the active request context."""
    s = _var.get()
    if not s:
        return (None, None, None)
    return (s.openai_api_key, s.anthropic_api_key, s.gemini_api_key)
