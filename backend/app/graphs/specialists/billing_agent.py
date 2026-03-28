"""Billing specialist agent."""
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.graphs.kg_email_insights import build_draft_user_message
from app.services.llm_utils import get_chat_model_for_state, get_text_content


def billing_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for billing messages."""
    model = get_chat_model_for_state(state, temperature=0.7)

    user_body = build_draft_user_message(state, "Draft a billing reply:")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to a billing or invoice message.
        Guidelines:
        - Be professional and clear
        - Address payment or invoice questions directly
        - If confirming payment, be specific about amounts and dates
        - If there's an issue, acknowledge it and provide next steps
        - Use a formal, business-appropriate tone"""),
        ("user", "{user_body}"),
    ])

    chain = prompt | model
    response = chain.invoke({"user_body": user_body})

    return {
        "draft_reply": get_text_content(response).strip(),
        "audit_log": [{"node": "billing_agent", "action": "specialist_reply_drafted"}]
    }


def billing_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for billing messages."""
    model = get_chat_model_for_state(state, temperature=0, model_tier="fast")

    message = state.get("normalized_message", state.get("raw_message", ""))

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Billing tasks: payments, invoices, disputes, refunds, confirmations.
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
        "audit_log": [{"node": "billing_agent", "action": "specialist_tasks_extracted"}]
    }
