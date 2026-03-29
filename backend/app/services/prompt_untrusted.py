"""Delimited wrapping for untrusted text in LLM prompts (email, KG, synthesis)."""
from __future__ import annotations


def wrap_untrusted(label: str, text: str | None, *, max_chars: int) -> str:
    """
    Mark a block as data-only. Models may still be manipulated; this is defense-in-depth.
    ``label`` must be a short internal identifier (not user-controlled).
    """
    safe_label = label.replace("]", "").replace("[", "")[:64] or "content"
    body = (text or "")[:max_chars]
    if len(text or "") > max_chars:
        body += "\n…[truncated]"
    return (
        f"[BEGIN_UNTRUSTED name={safe_label}]\n"
        f"{body}\n"
        f"[END_UNTRUSTED name={safe_label}]"
    )
