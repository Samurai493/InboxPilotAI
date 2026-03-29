"""Shared state schema for InboxPilot AI workflow."""
from operator import add
from typing import Annotated, TypedDict, Optional, List, Dict, Any, NotRequired
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
    selected_agent: NotRequired[str | None]  # recruiter, scheduling, academic, support, billing, general
    orchestration_rationale: NotRequired[str | None]
    planned_actions: NotRequired[List[str] | None]
    # When False, skip specialist nodes and use generate_draft + extract_tasks (benchmarks / A-B)
    use_specialist: NotRequired[bool]
    # Optional per-request overrides (e.g. from Settings UI); fall back to backend .env when unset
    llm_provider: NotRequired[str | None]
    llm_model: NotRequired[str | None]
    # LLM API keys are supplied via ``LlmRequestSecrets`` context only (never checkpointed).

    # Risk and safety
    risk_flags: Optional[List[str]]
    human_review_required: Optional[bool]
    
    # Memory and context
    memory_hits: Optional[List[Dict[str, Any]]]
    knowledge_hits: NotRequired[Dict[str, Any] | None]
    # Entities/relations written to persistent KG during this run (after persist_knowledge_memory)
    knowledge_written: NotRequired[Dict[str, Any] | None]
    # KG + LLM synthesis (after retrieve_memory)
    email_context: NotRequired[str | None]
    email_summary: NotRequired[str | None]
    follow_ups: NotRequired[List[str] | None]
    
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
    # Filled after graph.invoke (see GraphService) with totals + per-call breakdown
    llm_token_usage: NotRequired[Dict[str, Any] | None]
    audit_log: Annotated[List[Dict[str, Any]], add]
