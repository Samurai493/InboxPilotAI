"""Scheduling specialist agent."""
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.graphs.kg_email_insights import build_draft_user_message
from app.services.llm_utils import get_chat_model_for_state, get_text_content


def scheduling_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for scheduling messages."""
    model = get_chat_model_for_state(state, temperature=0.7)

    user_body = build_draft_user_message(state, "Draft a scheduling reply:")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to a scheduling request.
        Guidelines:
        - Be clear about your availability
        - Suggest specific times if possible
        - If declining, offer alternative times
        - Be concise and direct
        - Use a professional but friendly tone"""),
        ("user", "{user_body}"),
    ])

    chain = prompt | model
    response = chain.invoke({"user_body": user_body})

    return {
        "draft_reply": get_text_content(response).strip(),
        "audit_log": [{"node": "scheduling_agent", "action": "specialist_reply_drafted"}]
    }


def scheduling_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for scheduling messages."""
    model = get_chat_model_for_state(state, temperature=0, model_tier="fast")

    message = state.get("normalized_message", state.get("raw_message", ""))

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Scheduling tasks: meetings, invites, time confirmations, RSVPs.
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
        "audit_log": [{"node": "scheduling_agent", "action": "specialist_tasks_extracted"}]
    }
