"""Validate LLM task JSON before knowledge-graph persistence."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

_MAX_DESC = 2000
_MAX_DUE = 120


class ExtractedTaskItem(BaseModel):
    description: str = Field(..., max_length=_MAX_DESC)
    due_date: str | None = None
    priority: str = "medium"

    @field_validator("description", mode="before")
    @classmethod
    def _desc(cls, v: Any) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        return s[:_MAX_DESC]

    @field_validator("due_date", mode="before")
    @classmethod
    def _due(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return s[:_MAX_DUE]

    @field_validator("priority", mode="before")
    @classmethod
    def _pri(cls, v: Any) -> str:
        if v is None:
            return "medium"
        p = str(v).strip().lower()
        return p if p in ("low", "medium", "high") else "medium"


def validate_extracted_tasks(raw: Any, *, max_items: int = 25) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:max_items]:
        if not isinstance(item, dict):
            continue
        try:
            m = ExtractedTaskItem.model_validate(item)
        except Exception:
            continue
        if not m.description.strip():
            continue
        out.append(
            {
                "description": m.description.strip(),
                "due_date": m.due_date,
                "priority": m.priority,
            }
        )
    return out
