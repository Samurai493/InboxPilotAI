"""Synthesize email context, summary, and follow-ups using knowledge graph + memory."""
import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.graphs.state import InboxPilotState
from app.services.llm_utils import get_chat_model_for_state, get_text_content


def _compact_kg_for_prompt(knowledge_hits: dict[str, Any] | None) -> str:
    if not knowledge_hits:
        return "(no prior graph memory)"
    entities = knowledge_hits.get("entities") or []
    relations = knowledge_hits.get("relations") or []
    lines: list[str] = []
    for e in entities[:12]:
        lines.append(
            f"- [{e.get('type', '?')}] {e.get('name', '')} (id={e.get('id', '')[:8]}…)"
        )
    for r in relations[:14]:
        lines.append(
            f"- {r.get('type', '?')}: {r.get('source_entity_id', '')[:8]}… → "
            f"{r.get('target_entity_id', '')[:8]}…"
        )
    return "\n".join(lines) if lines else "(empty graph)"


def build_draft_user_message(state: InboxPilotState, reply_instruction: str) -> str:
    """User message for draft nodes: optional KG insights + original email + instruction."""
    message = state.get("normalized_message", state.get("raw_message", ""))
    insights = format_kg_insights_for_prompt(state)
    tail = f"Original message:\n{message}\n\n{reply_instruction}"
    if insights:
        return f"{insights}\n\n{tail}"
    return tail


def format_kg_insights_for_prompt(state: InboxPilotState) -> str:
    """Appendable block for draft/specialist prompts when synthesis ran."""
    ctx = state.get("email_context")
    summary = state.get("email_summary")
    follow = state.get("follow_ups") or []
    if not ctx and not summary and not (isinstance(follow, list) and follow):
        return ""
    parts: list[str] = []
    if summary:
        parts.append(f"Summary: {summary}")
    if ctx:
        parts.append(f"Context (memory/graph): {ctx}")
    if isinstance(follow, list) and follow:
        parts.append("Suggested follow-ups: " + "; ".join(str(x) for x in follow[:8]))
    return "\n".join(parts)


def synthesize_email_insights(state: InboxPilotState) -> InboxPilotState:
    """
    After memory + KG retrieval: produce structured context, follow-ups, and summary.
    """
    model = get_chat_model_for_state(state, temperature=0.2)
    message = state.get("normalized_message", state.get("raw_message", ""))
    intent = state.get("intent", "personal")
    urgency = state.get("urgency_score", "low")
    sender = state.get("sender_profile") or {}
    kg_text = _compact_kg_for_prompt(state.get("knowledge_hits"))

    prefs_text = "(none)"
    for hit in state.get("memory_hits") or []:
        if hit.get("type") == "user_preferences":
            prefs_text = json.dumps(hit.get("data") or {}, ensure_ascii=False)[:1200]
            break

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You help an inbox assistant. Using the email text, classification, user preferences,
and recent knowledge-graph memory, produce three outputs.

Return ONLY valid JSON with this exact schema:
{{
  "email_context": "<2-5 sentences: who/what/why, grounded in graph memory when relevant>",
  "email_summary": "<1-3 sentences: neutral summary of the email>",
  "follow_ups": ["<action 1>", "<action 2>"]
}}

follow_ups should be concrete next steps for the recipient (max 6 items). If none, use [].
Do not include markdown or code fences.""",
            ),
            (
                "user",
                "Intent: {intent}\nUrgency: {urgency}\nSender profile: {sender}\n"
                "User preferences (JSON): {prefs}\n\n"
                "Recent knowledge graph (entities/relations):\n{kg}\n\n"
                "Email:\n{message}",
            ),
        ]
    )

    chain = prompt | model
    response = chain.invoke(
        {
            "intent": intent,
            "urgency": urgency,
            "sender": json.dumps(sender, ensure_ascii=False)[:800],
            "prefs": prefs_text,
            "kg": kg_text,
            "message": message[:12000],
        }
    )
    raw = get_text_content(response).strip()

    email_context: str | None = None
    email_summary: str | None = None
    follow_ups: list[str] = []

    try:
        parsed = json.loads(raw)
        if isinstance(parsed.get("email_context"), str) and parsed["email_context"].strip():
            email_context = parsed["email_context"].strip()
        if isinstance(parsed.get("email_summary"), str) and parsed["email_summary"].strip():
            email_summary = parsed["email_summary"].strip()
        fu = parsed.get("follow_ups")
        if isinstance(fu, list):
            follow_ups = [str(x).strip() for x in fu if str(x).strip()][:8]
    except (json.JSONDecodeError, TypeError, ValueError):
        email_summary = message[:400] + ("…" if len(message) > 400 else "")
        email_context = (
            f"Intent={intent}; urgency={urgency}. Graph memory available but JSON parse failed; "
            "use raw email and listed entities for reasoning."
        )

    return {
        "email_context": email_context,
        "email_summary": email_summary,
        "follow_ups": follow_ups or None,
        "audit_log": [
            {
                "node": "synthesize_email_insights",
                "action": "insights_ready",
                "has_summary": bool(email_summary),
                "follow_ups_count": len(follow_ups),
            }
        ],
    }
