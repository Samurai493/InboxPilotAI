"""Recruiter and networking specialist agent."""
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.graphs.kg_email_insights import build_draft_user_message
from app.services.llm_utils import get_chat_model_for_state, get_text_content


def recruiter_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for recruiter/networking messages."""
    model = get_chat_model_for_state(state, temperature=0.7)

    # Get user preferences
    memory_hits = state.get("memory_hits", [])
    user_prefs = None
    for hit in memory_hits:
        if hit.get("type") == "user_preferences":
            user_prefs = hit.get("data")
            break

    tone = user_prefs.get("tone", "professional") if user_prefs else "professional"
    signature = user_prefs.get("signature", "") if user_prefs else ""

    user_body = build_draft_user_message(state, "Draft a professional reply:")
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are drafting a professional reply to a recruiter or networking contact.
        Guidelines:
        - Be polite, concise, and show genuine interest if applicable
        - If declining, be gracious and leave the door open for future opportunities
        - If interested, express enthusiasm and suggest next steps
        - Match the professional tone of the original message
        - Keep it to 2-3 short paragraphs
        - Use a {tone} tone"""),
        ("user", "{user_body}"),
    ])

    chain = prompt | model
    response = chain.invoke({"user_body": user_body})

    draft = get_text_content(response).strip()
    if signature:
        draft += f"\n\n{signature}"

    return {
        "draft_reply": draft,
        "audit_log": [{"node": "recruiter_agent", "action": "specialist_reply_drafted"}]
    }


def recruiter_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for recruiter messages."""
    model = get_chat_model_for_state(state, temperature=0, model_tier="fast")

    message = state.get("normalized_message", state.get("raw_message", ""))

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Recruiter/networking tasks only (interviews, applications, follow-ups, info requests).
Return ONLY JSON array: [{{"description":str,"due_date":str|null,"priority":"low"|"medium"|"high"}}] or [].""",
        ),
        ("user", f"Message:\n{message}")
    ])

    chain = prompt | model
    response = chain.invoke({})

    import json
    try:
        tasks = json.loads(get_text_content(response).strip())
        if not isinstance(tasks, list):
            tasks = []
    except json.JSONDecodeError:
        tasks = []

    return {
        "extracted_tasks": tasks,
        "audit_log": [{"node": "recruiter_agent", "action": "specialist_tasks_extracted"}]
    }
