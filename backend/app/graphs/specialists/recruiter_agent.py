"""Recruiter and networking specialist agent."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.config import settings


def recruiter_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for recruiter/networking messages."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    # Get user preferences
    memory_hits = state.get("memory_hits", [])
    user_prefs = None
    for hit in memory_hits:
        if hit.get("type") == "user_preferences":
            user_prefs = hit.get("data")
            break
    
    tone = user_prefs.get("tone", "professional") if user_prefs else "professional"
    signature = user_prefs.get("signature", "") if user_prefs else ""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are drafting a professional reply to a recruiter or networking contact.
        Guidelines:
        - Be polite, concise, and show genuine interest if applicable
        - If declining, be gracious and leave the door open for future opportunities
        - If interested, express enthusiasm and suggest next steps
        - Match the professional tone of the original message
        - Keep it to 2-3 short paragraphs
        - Use a {tone} tone"""),
        ("user", f"Original message:\n{message}\n\nDraft a professional reply:")
    ])
    
    chain = prompt | model
    response = chain.invoke({})
    
    draft = response.content.strip()
    if signature:
        draft += f"\n\n{signature}"
    
    return {
        "draft_reply": draft,
        "audit_log": [{"node": "recruiter_agent", "action": "specialist_reply_drafted"}]
    }


def recruiter_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for recruiter messages."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract action items specific to recruiter/networking messages:
        - Interview scheduling
        - Application deadlines
        - Follow-up dates
        - Information requests
        
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
        "audit_log": [{"node": "recruiter_agent", "action": "specialist_tasks_extracted"}]
    }
