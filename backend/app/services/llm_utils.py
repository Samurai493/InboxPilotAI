"""Unified chat model factory for OpenAI, Anthropic Claude, and Google Gemini."""
from __future__ import annotations

from typing import Any, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.config import settings


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


def get_chat_model(*, temperature: float = 0.0) -> BaseChatModel:
    """
    Build the configured chat model.

    LLM_PROVIDER:
      - openai (default): requires OPENAI_API_KEY
      - anthropic: requires ANTHROPIC_API_KEY
      - google_genai: requires GEMINI_API_KEY (Google AI Studio / Gemini API)

    Model name uses LLM_MODEL, or falls back to OPENAI_MODEL for backward compatibility.
    """
    provider = (settings.LLM_PROVIDER or "openai").lower().strip()

    if settings.LLM_MODEL and settings.LLM_MODEL.strip():
        model_name = settings.LLM_MODEL.strip()
    elif provider == "openai":
        model_name = (settings.OPENAI_MODEL or "gpt-4o-mini").strip()
    elif provider in ("anthropic", "claude"):
        model_name = "claude-3-5-sonnet-20241022"
    elif provider in ("google_genai", "google", "gemini"):
        model_name = "gemini-1.5-flash"
    else:
        model_name = "gpt-4o-mini"

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER is openai")
        return ChatOpenAI(model=model_name, temperature=temperature, api_key=settings.OPENAI_API_KEY)

    if provider in ("anthropic", "claude"):
        from langchain_anthropic import ChatAnthropic

        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is required when LLM_PROVIDER is anthropic")
        return ChatAnthropic(model=model_name, temperature=temperature, api_key=settings.ANTHROPIC_API_KEY)

    if provider in ("google_genai", "google", "gemini"):
        try:
            from langchain_community.chat_models import ChatGoogleGenerativeAI
        except ImportError:  # pragma: no cover
            from langchain_google_genai import ChatGoogleGenerativeAI

        key = settings.GEMINI_API_KEY
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is required when LLM_PROVIDER is google_genai "
                "(create a key in Google AI Studio)"
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
