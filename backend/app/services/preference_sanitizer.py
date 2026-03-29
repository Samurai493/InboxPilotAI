"""Allowlist and sanitize user preference fields before DB / LLM use."""
from __future__ import annotations

import re
from typing import Any

ALLOWED_TONES = frozenset({"professional", "friendly", "formal", "casual", "neutral"})
ALLOWED_REPLY_STYLES = frozenset({"concise", "detailed", "brief", "balanced"})

_DEFAULT_TONE = "professional"
_DEFAULT_REPLY_STYLE = "concise"

_MAX_SIGNATURE_LEN = 2000


def _strip_controls(s: str) -> str:
    return "".join(ch for ch in s if ch >= " " or ch in "\n\r\t")


def sanitize_tone(value: str | None) -> str:
    if not value or not isinstance(value, str):
        return _DEFAULT_TONE
    key = value.strip().lower()
    return key if key in ALLOWED_TONES else _DEFAULT_TONE


def sanitize_reply_style(value: str | None) -> str:
    if not value or not isinstance(value, str):
        return _DEFAULT_REPLY_STYLE
    key = value.strip().lower()
    return key if key in ALLOWED_REPLY_STYLES else _DEFAULT_REPLY_STYLE


def sanitize_signature(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    t = _strip_controls(value).strip()
    if not t:
        return None
    t = re.sub(r"\r\n", "\n", t)
    return t[:_MAX_SIGNATURE_LEN]


def sanitize_preferences_dict(prefs: dict[str, Any]) -> dict[str, Any]:
    """Return a copy safe for persistence and later prompt use."""
    out = dict(prefs)
    if "tone" in out:
        out["tone"] = sanitize_tone(out.get("tone"))
    if "reply_style" in out:
        out["reply_style"] = sanitize_reply_style(out.get("reply_style"))
    if "signature" in out:
        out["signature"] = sanitize_signature(out.get("signature"))
    return out


def tone_for_system_prompt(tone: str | None) -> str:
    """Safe fragment for static system prompts (never raw user text)."""
    return sanitize_tone(tone)
