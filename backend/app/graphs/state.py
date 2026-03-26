"""Shared state schema for InboxPilot AI workflow."""
from typing import TypedDict, Optional, List, Dict, Any, NotRequired
from datetime import datetime


class InboxPilotState(TypedDict):
    """State schema for the inbox processing workflow."""
    
    # User and thread identifiers
    user_id: Optional[str]
    thread_id: Optional[str]
    message_id: Optional[str]
    
    # Message content
    raw_message: str
    normalized_message: Optional[str]
    
    # Sender information
    sender_profile: Optional[Dict[str, Any]]
    
    # Classification and routing
    intent: Optional[str]  # recruiter, scheduling, academic, support, billing, personal, spam
    urgency_score: Optional[str]  # low, medium, high
    # When False, skip specialist nodes and use generate_draft + extract_tasks (benchmarks / A-B)
    use_specialist: NotRequired[bool]
    
    # Risk and safety
    risk_flags: Optional[List[str]]
    human_review_required: Optional[bool]
    
    # Memory and context
    memory_hits: Optional[List[Dict[str, Any]]]
    
    # Outputs
    draft_reply: Optional[str]
    extracted_tasks: Optional[List[Dict[str, Any]]]
    due_dates: Optional[List[datetime]]
    
    # Quality metrics
    confidence_score: Optional[float]
    
    # Workflow status
    final_status: Optional[str]  # pending, processing, completed, failed, interrupted
    
    # Observability
    trace_id: Optional[str]
    audit_log: Optional[List[Dict[str, Any]]]
