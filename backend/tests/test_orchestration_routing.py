"""Routing without LLM when ORCHESTRATION_USE_LLM is false."""
from unittest.mock import patch

from app.graphs.specialists.orchestration_agent import orchestrate_email


def test_orchestration_maps_intent_without_llm():
    with patch("app.graphs.specialists.orchestration_agent.settings") as s:
        s.ORCHESTRATION_USE_LLM = False
        out = orchestrate_email(
            {
                "intent": "billing",
                "use_specialist": True,
                "audit_log": [],
            }
        )
    assert out["selected_agent"] == "billing"
    assert "billing" in (out.get("orchestration_rationale") or "")


def test_orchestration_general_for_personal():
    with patch("app.graphs.specialists.orchestration_agent.settings") as s:
        s.ORCHESTRATION_USE_LLM = False
        out = orchestrate_email(
            {
                "intent": "personal",
                "use_specialist": True,
                "audit_log": [],
            }
        )
    assert out["selected_agent"] == "general"
