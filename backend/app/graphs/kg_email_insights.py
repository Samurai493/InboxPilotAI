"""Synthesize email context, summary, and follow-ups using knowledge graph + memory."""
import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.graphs.state import InboxPilotState
from app.services.llm_utils import get_chat_model_for_state, get_text_content
from app.services.prompt_untrusted import wrap_untrusted


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
    # Use ``or`` so explicit ``normalized_message: None`` still falls back to ``raw_message``.
    message = state.get("normalized_message") or state.get("raw_message") or ""
    insights = format_kg_insights_for_prompt(state)
    msg_wrapped = wrap_untrusted("incoming_email", message, max_chars=24000)
    tail = f"{msg_wrapped}\n\n{reply_instruction}"
    if insights:
        ins_wrapped = wrap_untrusted("synthesis_and_memory_block", insights, max_chars=12000)
        return f"{ins_wrapped}\n\n{tail}"
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
    kg_raw = _compact_kg_for_prompt(state.get("knowledge_hits"))
    kg_text = wrap_untrusted("kg_compact", kg_raw, max_chars=6000)

    prefs_text = "(none)"
    for hit in state.get("memory_hits") or []:
        if hit.get("type") == "user_preferences":
            prefs_text = wrap_untrusted(
                "user_preferences_json",
                json.dumps(hit.get("data") or {}, ensure_ascii=False)[:1200],
                max_chars=1200,
            )
            break

    sender_wrapped = wrap_untrusted(
        "sender_profile_json",
        json.dumps(sender, ensure_ascii=False)[:800],
        max_chars=800,
    )
    message_wrapped = wrap_untrusted("email_body", message, max_chars=12000)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Inbox assistant: merge email + intent + prefs + graph memory into JSON only (no markdown):
{{"email_context":"2-5 sentences who/what/why (use graph when relevant)","email_summary":"1-3 neutral sentences","follow_ups":["concrete next steps for recipient, max 6"]}}
Use [] for follow_ups if none.""",
            ),
            (
                "user",
                "Intent: {intent}\nUrgency: {urgency}\nSender profile:\n{sender}\n"
                "User preferences:\n{prefs}\n\n"
                "Recent knowledge graph:\n{kg}\n\n"
                "Email:\n{message}",
            ),
        ]
    )

    chain = prompt | model
    response = chain.invoke(
        {
            "intent": intent,
            "urgency": urgency,
            "sender": sender_wrapped,
            "prefs": prefs_text,
            "kg": kg_text,
            "message": message_wrapped,
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
