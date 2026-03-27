"""Aggregate LLM token usage across a LangGraph workflow run via LangChain callbacks."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import ChatGeneration, LLMResult


def _as_int(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _merge_usage_dict(target: dict[str, int], data: dict[str, Any]) -> None:
    """Normalize common provider keys into input_tokens / output_tokens / total_tokens."""
    if not isinstance(data, dict):
        return
    inp = (
        _as_int(data.get("input_tokens"))
        or _as_int(data.get("prompt_tokens"))
        or _as_int(data.get("input_token_count"))
    )
    out = (
        _as_int(data.get("output_tokens"))
        or _as_int(data.get("completion_tokens"))
        or _as_int(data.get("output_token_count"))
    )
    tot = _as_int(data.get("total_tokens"))
    if tot <= 0 and (inp > 0 or out > 0):
        tot = inp + out
    target["input_tokens"] = target.get("input_tokens", 0) + inp
    target["output_tokens"] = target.get("output_tokens", 0) + out
    if tot > 0:
        target["total_tokens"] = target.get("total_tokens", 0) + tot
    elif inp or out:
        target["total_tokens"] = target.get("total_tokens", 0) + inp + out


def _extract_from_llm_result(response: LLMResult) -> dict[str, int]:
    acc: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    lo = response.llm_output
    if isinstance(lo, dict):
        _merge_usage_dict(acc, lo.get("token_usage") or {})
        _merge_usage_dict(acc, lo.get("usage") or {})
        # Anthropic-style top-level
        if "input_tokens" in lo or "output_tokens" in lo:
            _merge_usage_dict(acc, lo)

    for gen_list in response.generations or []:
        for gen in gen_list:
            if isinstance(gen, ChatGeneration):
                msg = gen.message
                um = getattr(msg, "usage_metadata", None)
                if isinstance(um, dict):
                    _merge_usage_dict(acc, um)
                rm = getattr(msg, "response_metadata", None)
                if isinstance(rm, dict):
                    _merge_usage_dict(acc, rm.get("token_usage") or {})
            gi = getattr(gen, "generation_info", None)
            if isinstance(gi, dict):
                _merge_usage_dict(acc, gi.get("token_usage") or {})
                _merge_usage_dict(acc, gi.get("usage_metadata") or {})
    return acc


class WorkflowTokenUsageCallback(BaseCallbackHandler):
    """Records per-LLM-call and summed token usage for one graph.invoke."""

    def __init__(self) -> None:
        super().__init__()
        self._seen_run_ids: set[str] = set()
        self.calls: list[dict[str, Any]] = []
        self.totals: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
        }

    def _record(self, response: LLMResult, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        rid = str(run_id) if run_id is not None else ""
        if rid and rid in self._seen_run_ids:
            return
        if rid:
            self._seen_run_ids.add(rid)

        usage = _extract_from_llm_result(response)
        if not any(usage.values()):
            return

        tags = kwargs.get("tags")
        name = kwargs.get("name")
        meta = kwargs.get("metadata") or {}
        model = None
        if isinstance(meta, dict):
            model = meta.get("ls_model_name") or meta.get("model_name")
        if not model and isinstance(lo := response.llm_output, dict):
            model = lo.get("model_name")

        call_entry = {
            "run_id": rid or None,
            "name": name,
            "tags": list(tags) if isinstance(tags, list) else tags,
            "model": model,
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "total_tokens": usage["total_tokens"]
            or (usage["input_tokens"] + usage["output_tokens"]),
        }
        self.calls.append(call_entry)
        self.totals["input_tokens"] += call_entry["input_tokens"]
        self.totals["output_tokens"] += call_entry["output_tokens"]
        self.totals["total_tokens"] += call_entry["total_tokens"]
        self.totals["llm_calls"] += 1

    def on_chat_model_end(self, response: LLMResult, **kwargs: Any) -> None:
        """ChatOpenAI / ChatAnthropic / ChatGoogleGenerativeAI emit usage here."""
        self._record(response, **kwargs)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Fallback when a provider only reports via the LLM callback (dedupe by run_id)."""
        self._record(response, **kwargs)

    def get_summary(self) -> dict[str, Any]:
        """Shape stored on workflow state and returned to clients."""
        return {
            "totals": {
                "input_tokens": self.totals["input_tokens"],
                "output_tokens": self.totals["output_tokens"],
                "total_tokens": self.totals["total_tokens"],
                "llm_calls": self.totals["llm_calls"],
            },
            "calls": list(self.calls),
        }
