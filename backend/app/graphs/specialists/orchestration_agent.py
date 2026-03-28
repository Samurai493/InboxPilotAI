"""Orchestration agent that picks the best specialist and next actions."""
import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.graphs.state import InboxPilotState
from app.services.llm_utils import get_chat_model_for_state, get_text_content

ALLOWED_AGENTS = {"recruiter", "scheduling", "academic", "support", "billing", "general"}


def _fallback_agent(intent: str | None) -> str:
    specialist_map = {
        "recruiter": "recruiter",
        "scheduling": "scheduling",
        "academic": "academic",
        "support": "support",
        "billing": "billing",
    }
    return specialist_map.get((intent or "").strip().lower(), "general")


def _safe_actions(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                cleaned.append(text)
    return cleaned[:6]


def _deterministic_orchestration(state: InboxPilotState) -> InboxPilotState:
    intent = state.get("intent", "personal")
    selected_agent = _fallback_agent(intent)
    return {
        "selected_agent": selected_agent,
        "orchestration_rationale": f"Routed from classified intent ({intent!r}).",
        "planned_actions": ["Draft a reply", "Extract action items and deadlines"],
        "audit_log": [
            {
                "node": "orchestration_agent",
                "action": "routing_deterministic",
                "selected_agent": selected_agent,
            }
        ],
    }


def orchestrate_email(state: InboxPilotState) -> InboxPilotState:
    """Choose the best specialist based on message content and intent."""
    use_specialist = state.get("use_specialist", True)

    if use_specialist is False:
        return {
            "selected_agent": "general",
            "orchestration_rationale": "Specialist routing disabled for this run.",
            "planned_actions": ["Draft a general reply", "Extract any follow-up tasks"],
            "audit_log": [
                {
                    "node": "orchestration_agent",
                    "action": "specialist_disabled",
                    "selected_agent": "general",
                }
            ],
        }

    if not settings.ORCHESTRATION_USE_LLM:
        return _deterministic_orchestration(state)

    model = get_chat_model_for_state(state, temperature=0, model_tier="fast")
    message = state.get("normalized_message", state.get("raw_message", ""))
    intent = state.get("intent", "personal")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Pick one agent: recruiter|scheduling|academic|support|billing|general.
Return ONLY JSON: {"selected_agent":"…","rationale":"short","planned_actions":["…","…"]}
Use general for personal, spam, mixed, or unclear. Max 6 planned_actions; no markdown.""",
            ),
            ("user", "Intent: {intent}\n\nEmail:\n{message}"),
        ]
    )

    chain = prompt | model
    response = chain.invoke({"intent": intent, "message": message[:8000]})
    raw = get_text_content(response).strip()

    selected_agent = _fallback_agent(intent)
    rationale = f"Fallback route based on intent={intent!r}."
    actions = ["Draft a reply", "Extract action items and deadlines"]

    try:
        parsed = json.loads(raw)
        candidate = str(parsed.get("selected_agent", "")).strip().lower()
        if candidate in ALLOWED_AGENTS:
            selected_agent = candidate
        rationale_candidate = parsed.get("rationale")
        if isinstance(rationale_candidate, str) and rationale_candidate.strip():
            rationale = rationale_candidate.strip()
        parsed_actions = _safe_actions(parsed.get("planned_actions"))
        if parsed_actions:
            actions = parsed_actions
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return {
        "selected_agent": selected_agent,
        "orchestration_rationale": rationale,
        "planned_actions": actions,
        "audit_log": [
            {
                "node": "orchestration_agent",
                "action": "agent_selected",
                "selected_agent": selected_agent,
            }
        ],
    }
