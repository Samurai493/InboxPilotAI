"""Support specialist agent."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.config import settings


def support_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for support messages."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to a support inquiry.
        Guidelines:
        - Be helpful and empathetic
        - Ask clarifying questions if needed
        - Show you understand the issue
        - Provide step-by-step solutions if applicable
        - Be patient and professional
        - Use a friendly, helpful tone"""),
        ("user", f"Original message:\n{message}\n\nDraft a helpful support reply:")
    ])
    
    chain = prompt | model
    response = chain.invoke({})
    
    return {
        "draft_reply": response.content.strip(),
        "audit_log": [{"node": "support_agent", "action": "specialist_reply_drafted"}]
    }


def support_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for support messages."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract support-related tasks:
        - Follow-up actions needed
        - Information to gather
        - Escalation requirements
        
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
        tasks = json.loads(response.content.strip())
        if not isinstance(tasks, list):
            tasks = []
    except json.JSONDecodeError:
        tasks = []
    
    return {
        "extracted_tasks": tasks,
        "audit_log": [{"node": "support_agent", "action": "specialist_tasks_extracted"}]
    }
