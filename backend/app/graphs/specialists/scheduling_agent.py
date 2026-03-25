"""Scheduling specialist agent."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.config import settings


def scheduling_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for scheduling messages."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to a scheduling request.
        Guidelines:
        - Be clear about your availability
        - Suggest specific times if possible
        - If declining, offer alternative times
        - Be concise and direct
        - Use a professional but friendly tone"""),
        ("user", f"Original message:\n{message}\n\nDraft a scheduling reply:")
    ])
    
    chain = prompt | model
    response = chain.invoke({})
    
    return {
        "draft_reply": response.content.strip(),
        "audit_log": [{"node": "scheduling_agent", "action": "specialist_reply_drafted"}]
    }


def scheduling_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for scheduling messages."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract scheduling-related tasks:
        - Meeting confirmations
        - Calendar invites to send
        - Time confirmations needed
        
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
        "audit_log": [{"node": "scheduling_agent", "action": "specialist_tasks_extracted"}]
    }
