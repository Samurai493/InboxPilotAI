"""Academic specialist agent."""
from langchain_core.prompts import ChatPromptTemplate
from app.graphs.state import InboxPilotState
from app.services.llm_utils import get_chat_model, get_text_content


def academic_draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Specialist reply drafting for academic messages."""
    model = get_chat_model(temperature=0.7)
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are drafting a reply to an academic or school-related message.
        Guidelines:
        - Be respectful and professional
        - Address any questions directly
        - If it's about assignments, be clear about deadlines
        - If it's administrative, be concise and helpful
        - Use a formal but friendly tone"""),
        ("user", f"Original message:\n{message}\n\nDraft an academic reply:")
    ])
    
    chain = prompt | model
    response = chain.invoke({})
    
    return {
        "draft_reply": get_text_content(response).strip(),
        "audit_log": [{"node": "academic_agent", "action": "specialist_reply_drafted"}]
    }


def academic_extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Specialist task extraction for academic messages."""
    model = get_chat_model(temperature=0)
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract academic-related tasks:
        - Assignment deadlines
        - Exam dates
        - Submission requirements
        - Registration deadlines
        
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
        "audit_log": [{"node": "academic_agent", "action": "specialist_tasks_extracted"}]
    }
