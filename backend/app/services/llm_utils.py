"""Unified chat model factory for OpenAI, Anthropic Claude, and Google Gemini."""
from __future__ import annotations

from typing import Any, Literal, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.config import settings
from app.graphs.state import InboxPilotState

ModelTier = Literal["default", "fast"]


def get_text_content(message: Union[BaseMessage, Any]) -> str:
    """Normalize AIMessage.content to str (OpenAI/Anthropic string; Gemini may use parts)."""
    raw = getattr(message, "content", message)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for block in raw:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
        return "".join(parts)
    return str(raw)


def _norm_opt(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None


def _fast_model_for_provider(provider: str) -> str:
    """Default low-cost model per provider when ``LLM_FAST_MODEL`` is unset."""
    if provider == "openai":
        return (settings.OPENAI_MODEL or "gpt-4o-mini").strip()
    if provider in ("anthropic", "claude"):
        return "claude-3-5-haiku-20241022"
    if provider in ("google_genai", "google", "gemini"):
        return "gemini-2.5-flash"
    return "gpt-4o-mini"


def get_chat_model(
    *,
    temperature: float = 0.0,
    provider: str | None = None,
    model: str | None = None,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    gemini_api_key: str | None = None,
    model_tier: ModelTier = "default",
) -> BaseChatModel:
    """
    Build the configured chat model.

    Optional ``provider`` / ``model`` override ``settings.LLM_PROVIDER`` / ``LLM_MODEL`` (e.g. from UI).

    ``model_tier="fast"``: uses ``settings.LLM_FAST_MODEL`` if set, else a provider-specific
    cheaper default; ignores the ``model`` argument so UI “main” model stays for drafts only.

    LLM_PROVIDER:
      - openai (default): requires OPENAI_API_KEY
      - anthropic: requires ANTHROPIC_API_KEY
      - google_genai: requires GEMINI_API_KEY (Google AI Studio / Gemini API)

    Model name: ``model`` param, else settings.LLM_MODEL, else provider defaults.
    """
    p = _norm_opt(provider) or (settings.LLM_PROVIDER or "openai")
    provider = p.lower().strip()

    if model_tier == "fast":
        fast = _norm_opt(settings.LLM_FAST_MODEL)
        model_name = fast if fast else _fast_model_for_provider(provider)
    else:
        m_override = _norm_opt(model)
        if m_override:
            model_name = m_override
        elif settings.LLM_MODEL and settings.LLM_MODEL.strip():
            model_name = settings.LLM_MODEL.strip()
        elif provider == "openai":
            model_name = (settings.OPENAI_MODEL or "gpt-4o-mini").strip()
        elif provider in ("anthropic", "claude"):
            model_name = "claude-3-5-sonnet-20241022"
        elif provider in ("google_genai", "google", "gemini"):
            # Google retires older IDs; use current stable names (see ai.google.dev Gemini API models).
            model_name = "gemini-2.5-flash"
        else:
            model_name = "gpt-4o-mini"

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        okey = _norm_opt(openai_api_key) or settings.OPENAI_API_KEY
        if not okey:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER is openai "
                "(set in backend/.env or save it in app Settings)"
            )
        return ChatOpenAI(model=model_name, temperature=temperature, api_key=okey)

    if provider in ("anthropic", "claude"):
        from langchain_anthropic import ChatAnthropic

        akey = _norm_opt(anthropic_api_key) or settings.ANTHROPIC_API_KEY
        if not akey:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER is anthropic "
                "(set in backend/.env or save it in app Settings)"
            )
        return ChatAnthropic(model=model_name, temperature=temperature, api_key=akey)

    if provider in ("google_genai", "google", "gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = _norm_opt(gemini_api_key) or settings.GEMINI_API_KEY
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is required when LLM_PROVIDER is google_genai "
                "(create a key in Google AI Studio, set GEMINI_API_KEY in backend/.env, or save it in app Settings)"
            )
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=key,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER={provider!r}. "
        "Use: openai, anthropic, or google_genai"
    )


def get_chat_model_for_state(
    state: InboxPilotState,
    *,
    temperature: float = 0.0,
    model_tier: ModelTier = "default",
) -> BaseChatModel:
    """Like ``get_chat_model`` but reads provider/model from state and API keys from request context."""
    from app.services.llm_request_context import get_request_llm_api_keys

    co, ca, cg = get_request_llm_api_keys()
    lp = state.get("llm_provider")
    lm = state.get("llm_model")
    p = lp.strip() if isinstance(lp, str) and lp.strip() else None
    m = lm.strip() if isinstance(lm, str) and lm.strip() else None
    return get_chat_model(
        temperature=temperature,
        provider=p,
        model=m if model_tier == "default" else None,
        openai_api_key=_norm_opt(co),
        anthropic_api_key=_norm_opt(ca),
        gemini_api_key=_norm_opt(cg),
        model_tier=model_tier,
    )
