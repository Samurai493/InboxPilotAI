"""Support specialist agent."""
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.graphs.kg_email_insights import build_draft_user_message
from app.services.llm_utils import get_chat_model_for_state, get_text_content


def support_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for support messages."""
    model = get_chat_model_for_state(state, temperature=0.7)

    user_body = build_draft_user_message(state, "Draft a helpful support reply:")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to a support inquiry.
        Guidelines:
        - Be helpful and empathetic
        - Ask clarifying questions if needed
        - Show you understand the issue
        - Provide step-by-step solutions if applicable
        - Be patient and professional
        - Use a friendly, helpful tone"""),
        ("user", "{user_body}"),
    ])

    chain = prompt | model
    response = chain.invoke({"user_body": user_body})

    return {
        "draft_reply": get_text_content(response).strip(),
        "audit_log": [{"node": "support_agent", "action": "specialist_reply_drafted"}]
    }


def support_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for support messages."""
    model = get_chat_model_for_state(state, temperature=0, model_tier="fast")

    message = state.get("normalized_message", state.get("raw_message", ""))

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Support tasks: follow-ups, info to gather, troubleshooting steps, escalations.
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
        "audit_log": [{"node": "support_agent", "action": "specialist_tasks_extracted"}]
    }
