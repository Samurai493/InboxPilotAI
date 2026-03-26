"""Main LangGraph workflow for inbox processing."""
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langgraph.graph.graph import START, END

from app.graphs.state import InboxPilotState
from app.graphs.checkpoint import get_checkpointer
from app.config import settings
from app.services.tracing import setup_langsmith

# Setup LangSmith tracing
setup_langsmith()


def ingest_message(state: InboxPilotState) -> InboxPilotState:
    """Accept raw message input."""
    # In MVP, message is already in state. This node validates and logs.
    return {
        "final_status": "processing",
        "audit_log": [{"node": "ingest_message", "action": "message_received"}]
    }


def normalize_message(state: InboxPilotState) -> InboxPilotState:
    """Clean and structure message text."""
    raw = state.get("raw_message", "")
    
    # Basic normalization: strip whitespace, remove excessive newlines
    normalized = " ".join(raw.split())
    
    # Extract basic metadata (in MVP, simple parsing)
    # In production, this would use more sophisticated parsing
    lines = raw.split("\n")
    subject = ""
    sender_email = ""
    sender_name = ""
    
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
        elif line.lower().startswith("from:"):
            from_line = line.split(":", 1)[1].strip()
            # Simple email extraction
            if "<" in from_line and ">" in from_line:
                sender_email = from_line.split("<")[1].split(">")[0].strip()
                sender_name = from_line.split("<")[0].strip()
            else:
                sender_email = from_line
    
    return {
        "normalized_message": normalized,
        "sender_profile": {
            "email": sender_email,
            "name": sender_name,
            "subject": subject
        },
        "audit_log": [{"node": "normalize_message", "action": "message_normalized"}]
    }


def classify_intent(state: InboxPilotState) -> InboxPilotState:
    """Classify message intent using LLM."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at classifying email messages. 
        Classify the following message into one of these categories:
        - recruiter: Job opportunities, networking, recruitment
        - scheduling: Meeting requests, calendar invites, appointment scheduling
        - academic: School-related, assignments, academic administration
        - support: Technical support, customer service inquiries
        - billing: Invoices, payments, financial transactions
        - personal: Personal messages, casual communication
        - spam: Unsolicited, promotional, or suspicious messages
        
        Respond with ONLY the category name, nothing else."""),
        ("user", "Message:\n{message}")
    ])
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    chain = prompt | model
    response = chain.invoke({"message": message})
    
    intent = response.content.strip().lower()
    
    # Validate intent
    valid_intents = ["recruiter", "scheduling", "academic", "support", "billing", "personal", "spam"]
    if intent not in valid_intents:
        intent = "personal"  # Default fallback
    
    # Simple urgency scoring
    urgency_keywords = {
        "high": ["urgent", "asap", "immediately", "deadline", "due"],
        "medium": ["soon", "please", "when", "schedule"]
    }
    message_lower = message.lower()
    urgency = "low"
    for level, keywords in urgency_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            urgency = level
            break
    
    return {
        "intent": intent,
        "urgency_score": urgency,
        "audit_log": [{"node": "classify_intent", "action": "intent_classified", "intent": intent}]
    }


def retrieve_memory(state: InboxPilotState) -> InboxPilotState:
    """Retrieve user preferences and context."""
    from app.database import SessionLocal
    from app.services.memory_service import MemoryService
    
    user_id = state.get("user_id")
    if not user_id:
        return {
            "memory_hits": [],
            "audit_log": [{"node": "retrieve_memory", "action": "no_user_id"}]
        }
    
    db = SessionLocal()
    try:
        preferences = MemoryService.get_user_preferences(db, user_id)
        memory_hits = []
        
        if preferences:
            memory_hits.append({
                "type": "user_preferences",
                "data": preferences
            })
        
        return {
            "memory_hits": memory_hits,
            "audit_log": [{"node": "retrieve_memory", "action": "memory_retrieved", "count": len(memory_hits)}]
        }
    finally:
        db.close()


def route_to_specialist(state: InboxPilotState) -> InboxPilotState:
    """Route to appropriate specialist subgraph based on intent."""
    intent = state.get("intent", "personal")
    
    # Map intents to specialist agents
    specialist_map = {
        "recruiter": "recruiter_agent",
        "scheduling": "scheduling_agent",
        "academic": "academic_agent",
        "support": "support_agent",
        "billing": "billing_agent"
    }
    
    specialist = specialist_map.get(intent)
    
    return {
        "audit_log": [{"node": "route_to_specialist", "action": "routed", "specialist": specialist or "general"}]
    }


def draft_reply(state: InboxPilotState) -> InboxPilotState:
    """Generate context-aware reply draft."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY
    )
    
    intent = state.get("intent", "personal")
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    # Get user preferences from memory
    memory_hits = state.get("memory_hits", [])
    user_prefs = None
    for hit in memory_hits:
        if hit.get("type") == "user_preferences":
            user_prefs = hit.get("data")
            break
    
    tone = user_prefs.get("tone", "professional") if user_prefs else "professional"
    signature = user_prefs.get("signature", "") if user_prefs else ""
    
    # Intent-specific prompts
    prompt_templates = {
        "recruiter": """You are drafting a professional reply to a recruiter or networking contact.
        Be polite, concise, and show interest. If declining, be gracious. If interested, express enthusiasm.
        Keep it to 2-3 short paragraphs.""",
        "scheduling": """You are drafting a reply to a scheduling request.
        Be clear about your availability. Suggest specific times if possible. Be concise.""",
        "academic": """You are drafting a reply to an academic or school-related message.
        Be respectful and professional. Address any questions directly. Keep it concise.""",
        "support": """You are drafting a reply to a support inquiry.
        Be helpful and clear. Ask clarifying questions if needed. Show you understand the issue.""",
        "billing": """You are drafting a reply to a billing or invoice message.
        Be professional and clear. Address payment or invoice questions directly.""",
        "personal": """You are drafting a friendly personal reply.
        Match the tone of the original message. Be warm and conversational.""",
        "spam": """You are drafting a brief, polite decline or unsubscribe request.
        Be professional but firm. Do not engage with the content."""
    }
    
    system_prompt = prompt_templates.get(intent, prompt_templates["personal"])
    
    # Add tone instruction
    if tone and tone != "professional":
        system_prompt += f"\n\nUse a {tone} tone in your reply."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Original message:\n{message}\n\nDraft a reply:")
    ])
    
    chain = prompt | model
    response = chain.invoke({"message": message})
    
    draft = response.content.strip()
    
    # Append signature if provided
    if signature:
        draft += f"\n\n{signature}"
    
    return {
        "draft_reply": draft,
        "audit_log": [{"node": "draft_reply", "action": "reply_drafted", "tone": tone}]
    }


def score_confidence(state: InboxPilotState) -> InboxPilotState:
    """Score confidence in the draft reply."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    draft = state.get("draft_reply", "")
    message = state.get("normalized_message", state.get("raw_message", ""))
    intent = state.get("intent", "personal")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Rate the confidence score (0.0 to 1.0) for this draft reply.
        Consider:
        - Appropriateness for the message type
        - Clarity and completeness
        - Professionalism
        - Risk of misunderstanding
        
        Respond with ONLY a number between 0.0 and 1.0, nothing else."""),
        ("user", f"Message Type: {intent}\n\nOriginal Message:\n{message}\n\nDraft Reply:\n{draft}\n\nConfidence Score:")
    ])
    
    chain = prompt | model
    response = chain.invoke({})
    
    try:
        confidence = float(response.content.strip())
        # Clamp to 0.0-1.0
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, AttributeError):
        confidence = 0.5  # Default if parsing fails
    
    return {
        "confidence_score": confidence,
        "audit_log": [{"node": "score_confidence", "action": "confidence_scored", "score": confidence}]
    }


def risk_gate(state: InboxPilotState) -> InboxPilotState:
    """Check for risks and determine if human review is required."""
    risk_flags = []
    human_review_required = False
    
    # Check confidence score
    confidence = state.get("confidence_score", 1.0)
    if confidence < settings.CONFIDENCE_THRESHOLD:
        risk_flags.append("low_confidence")
        human_review_required = True
    
    # Check for sensitive content
    message = state.get("normalized_message", state.get("raw_message", "")).lower()
    draft = state.get("draft_reply", "").lower()
    
    sensitive_keywords = {
        "financial": ["payment", "invoice", "refund", "charge", "credit card", "bank", "money", "price", "cost"],
        "legal": ["contract", "agreement", "lawsuit", "legal", "attorney", "lawyer", "sue"],
        "personal": ["ssn", "social security", "password", "pin", "account number"]
    }
    
    for category, keywords in sensitive_keywords.items():
        if any(keyword in message or keyword in draft for keyword in keywords):
            risk_flags.append(f"sensitive_{category}")
            human_review_required = True
    
    # Check intent
    intent = state.get("intent", "")
    if intent in ["billing", "spam"]:
        risk_flags.append("sensitive_intent")
        human_review_required = True
    
    # Check sender (unknown senders might need review)
    sender_profile = state.get("sender_profile", {})
    sender_email = sender_profile.get("email", "")
    if not sender_email or "@" not in sender_email:
        risk_flags.append("unknown_sender")
        # Don't auto-require review for unknown sender, but flag it
    
    return {
        "risk_flags": risk_flags,
        "human_review_required": human_review_required,
        "audit_log": [{"node": "risk_gate", "action": "risk_assessed", "flags": risk_flags, "review_required": human_review_required}]
    }


def human_review_interrupt(state: InboxPilotState):
    """Interrupt for human review when required."""
    from langgraph.types import interrupt, Command
    
    if state.get("human_review_required", False):
        # Interrupt and wait for human decision
        decision = interrupt({
            "message": "This message requires human review",
            "draft_reply": state.get("draft_reply", ""),
            "risk_flags": state.get("risk_flags", []),
            "confidence_score": state.get("confidence_score", 0.0),
            "intent": state.get("intent", ""),
            "thread_id": state.get("thread_id", "")
        })
        
        # When resumed, decision will contain the human's choice
        # For now, we'll assume approval if decision is truthy
        return {
            "human_review_required": False,
            "audit_log": [{"node": "human_review_interrupt", "action": "review_completed", "approved": bool(decision)}]
        }
    
    return {
        "audit_log": [{"node": "human_review_interrupt", "action": "review_skipped"}]
    }


def extract_tasks(state: InboxPilotState) -> InboxPilotState:
    """Extract action items and deadlines."""
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    message = state.get("normalized_message", state.get("raw_message", ""))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract action items and deadlines from this message.
        Return a JSON array of tasks, each with:
        - description: what needs to be done
        - due_date: ISO format date if mentioned, null otherwise
        - priority: low, medium, or high
        
        If no tasks are found, return an empty array [].
        Return ONLY valid JSON, no other text."""),
        ("user", "Message:\n{message}")
    ])
    
    chain = prompt | model
    response = chain.invoke({"message": message})
    
    import json
    try:
        tasks = json.loads(response.content.strip())
        if not isinstance(tasks, list):
            tasks = []
    except json.JSONDecodeError:
        tasks = []
    
    # Extract due dates separately
    from datetime import datetime
    due_dates = []
    for task in tasks:
        if task.get("due_date"):
            try:
                # Try parsing various date formats
                due_dates.append(task["due_date"])
            except:
                pass
    
    return {
        "extracted_tasks": tasks,
        "due_dates": due_dates,
        "audit_log": [{"node": "extract_tasks", "action": "tasks_extracted", "count": len(tasks)}]
    }


def finalize_output(state: InboxPilotState) -> InboxPilotState:
    """Prepare final output structure."""
    return {
        "final_status": "completed",
        "audit_log": [{"node": "finalize_output", "action": "workflow_completed"}]
    }


def should_continue(state: InboxPilotState) -> Literal["draft_reply", "extract_tasks", "finalize_output"]:
    """Conditional routing logic."""
    # Simple linear flow for MVP
    if not state.get("draft_reply"):
        return "draft_reply"
    elif not state.get("extracted_tasks"):
        return "extract_tasks"
    else:
        return "finalize_output"


# Build the graph
def create_graph():
    """Create and compile the main workflow graph."""
    builder = StateGraph(InboxPilotState)
    
    # Import specialist agents
    from app.graphs.specialists.recruiter_agent import recruiter_draft_reply, recruiter_extract_tasks
    from app.graphs.specialists.scheduling_agent import scheduling_draft_reply, scheduling_extract_tasks
    from app.graphs.specialists.academic_agent import academic_draft_reply, academic_extract_tasks
    from app.graphs.specialists.support_agent import support_draft_reply, support_extract_tasks
    from app.graphs.specialists.billing_agent import billing_draft_reply, billing_extract_tasks
    
    # Add nodes
    builder.add_node("ingest_message", ingest_message)
    builder.add_node("normalize_message", normalize_message)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("retrieve_memory", retrieve_memory)
    builder.add_node("route_to_specialist", route_to_specialist)
    
    # Specialist nodes
    builder.add_node("recruiter_draft", recruiter_draft_reply)
    builder.add_node("recruiter_extract", recruiter_extract_tasks)
    builder.add_node("scheduling_draft", scheduling_draft_reply)
    builder.add_node("scheduling_extract", scheduling_extract_tasks)
    builder.add_node("academic_draft", academic_draft_reply)
    builder.add_node("academic_extract", academic_extract_tasks)
    builder.add_node("support_draft", support_draft_reply)
    builder.add_node("support_extract", support_extract_tasks)
    builder.add_node("billing_draft", billing_draft_reply)
    builder.add_node("billing_extract", billing_extract_tasks)
    
    # General nodes (fallback)
    builder.add_node("generate_draft", draft_reply)
    builder.add_node("extract_tasks", extract_tasks)
    
    # Quality and review nodes
    builder.add_node("score_confidence", score_confidence)
    builder.add_node("risk_gate", risk_gate)
    builder.add_node("human_review_interrupt", human_review_interrupt)
    builder.add_node("finalize_output", finalize_output)
    
    # Add edges
    builder.add_edge(START, "ingest_message")
    builder.add_edge("ingest_message", "normalize_message")
    builder.add_edge("normalize_message", "classify_intent")
    builder.add_edge("classify_intent", "retrieve_memory")
    builder.add_edge("retrieve_memory", "route_to_specialist")
    
    # Conditional routing based on intent
    def route_after_classify(state: InboxPilotState) -> str:
        intent = state.get("intent", "personal")
        specialist_map = {
            "recruiter": "recruiter_draft",
            "scheduling": "scheduling_draft",
            "academic": "academic_draft",
            "support": "support_draft",
            "billing": "billing_draft"
        }
        return specialist_map.get(intent, "generate_draft")
    
    builder.add_conditional_edges(
        "route_to_specialist",
        route_after_classify,
        {
            "recruiter_draft": "recruiter_draft",
            "scheduling_draft": "scheduling_draft",
            "academic_draft": "academic_draft",
            "support_draft": "support_draft",
            "billing_draft": "billing_draft",
            "generate_draft": "generate_draft"
        }
    )
    
    # Specialist draft -> specialist extract -> score_confidence
    builder.add_edge("recruiter_draft", "recruiter_extract")
    builder.add_edge("recruiter_extract", "score_confidence")
    builder.add_edge("scheduling_draft", "scheduling_extract")
    builder.add_edge("scheduling_extract", "score_confidence")
    builder.add_edge("academic_draft", "academic_extract")
    builder.add_edge("academic_extract", "score_confidence")
    builder.add_edge("support_draft", "support_extract")
    builder.add_edge("support_extract", "score_confidence")
    builder.add_edge("billing_draft", "billing_extract")
    builder.add_edge("billing_extract", "score_confidence")
    
    # General draft -> extract -> score_confidence
    builder.add_edge("generate_draft", "extract_tasks")
    builder.add_edge("extract_tasks", "score_confidence")
    
    # Continue with quality and review
    builder.add_edge("score_confidence", "risk_gate")
    builder.add_edge("risk_gate", "human_review_interrupt")
    builder.add_edge("human_review_interrupt", "finalize_output")
    builder.add_edge("finalize_output", END)
    
    # Compile with checkpointer
    checkpointer = get_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
    
    return graph


# Create graph instance
graph = create_graph()
