"""Billing specialist agent."""
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.services.llm_utils import get_chat_model, get_text_content


def billing_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for billing messages."""
    model = get_chat_model(temperature=0.7)

    message = state.get("normalized_message", state.get("raw_message", ""))

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to a billing or invoice message.
        Guidelines:
        - Be professional and clear
        - Address payment or invoice questions directly
        - If confirming payment, be specific about amounts and dates
        - If there's an issue, acknowledge it and provide next steps
        - Use a formal, business-appropriate tone"""),
        ("user", f"Original message:\n{message}\n\nDraft a billing reply:")
    ])

    chain = prompt | model
    response = chain.invoke({})

    return {
        "draft_reply": get_text_content(response).strip(),
        "audit_log": [{"node": "billing_agent", "action": "specialist_reply_drafted"}]
    }


def billing_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for billing messages."""
    model = get_chat_model(temperature=0)

    message = state.get("normalized_message", state.get("raw_message", ""))

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract billing-related tasks:
        - Payment deadlines
        - Invoice reviews needed
        - Payment confirmations
        - Dispute resolutions

        Return a JSON array of tasks, each with:
        - description: what needs to be done
        - due_date: ISO format date if mentioned, null otherwise
        - priority: low, medium, or high

        Return ONLY valid JSON, no other text."""),
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
