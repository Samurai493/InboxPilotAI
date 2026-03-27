"""Service for executing LangGraph workflows."""
import logging
import uuid
from typing import Dict, Any
from langsmith import traceable
from app.graphs.main_graph import graph
from app.graphs.state import InboxPilotState
from app.services.tracing import trace_message_processing

logger = logging.getLogger(__name__)


class GraphService:
    """Service for managing graph execution."""
    
    @staticmethod
    def process_message(
        user_id: str,
        raw_message: str,
        message_id: str = None,
        use_specialist: bool = True,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> Dict[str, Any]:
        """
        Process a message through the workflow.
        
        Args:
            user_id: User identifier
            raw_message: Raw message text
            message_id: Optional external message ID
            use_specialist: If False, use general draft/extract nodes only (for A/B vs specialists)
            llm_provider: Optional override for settings.LLM_PROVIDER (openai, anthropic, google_genai)
            llm_model: Optional override for model id when set

        Returns:
            Dictionary with thread_id and initial state
        """
        # Generate thread ID
        thread_id = str(uuid.uuid4())
        
        # Create initial state
        initial_state: InboxPilotState = {
            "user_id": user_id,
            "thread_id": thread_id,
            "message_id": message_id,
            "raw_message": raw_message,
            "normalized_message": None,
            "sender_profile": None,
            "intent": None,
            "urgency_score": None,
            "risk_flags": None,
            "human_review_required": None,
            "memory_hits": None,
            "draft_reply": None,
            "extracted_tasks": None,
            "due_dates": None,
            "confidence_score": None,
            "final_status": "pending",
            "trace_id": None,
            "audit_log": [],
            "use_specialist": use_specialist,
        }
        if llm_provider is not None:
            t = llm_provider.strip()
            initial_state["llm_provider"] = t if t else None
        if llm_model is not None:
            t = llm_model.strip()
            initial_state["llm_model"] = t if t else None
        if openai_api_key is not None:
            t = openai_api_key.strip()
            initial_state["openai_api_key"] = t if t else None
        if anthropic_api_key is not None:
            t = anthropic_api_key.strip()
            initial_state["anthropic_api_key"] = t if t else None
        if gemini_api_key is not None:
            t = gemini_api_key.strip()
            initial_state["gemini_api_key"] = t if t else None
        
        # Configure graph execution
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Execute graph with tracing
        try:
            # Trace the workflow
            intent = initial_state.get("intent", "unknown")
            trace_message_processing(thread_id, user_id, intent)
            
            final_state = graph.invoke(initial_state, config=config)
            
            # Store trace ID if available
            trace_id = final_state.get("trace_id")
            
            return {
                "thread_id": thread_id,
                "state": final_state,
                "status": "completed",
                "trace_id": trace_id
            }
        except Exception as e:
            logger.exception(
                "Graph execution failed",
                extra={
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "use_specialist": use_specialist,
                    "llm_provider": initial_state.get("llm_provider"),
                    "llm_model": initial_state.get("llm_model"),
                },
            )
            return {
                "thread_id": thread_id,
                "state": initial_state,
                "status": "failed",
                "error": str(e)
            }
    
    @staticmethod
    def get_thread_state(thread_id: str) -> Dict[str, Any]:
        """
        Get the current state of a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Current thread state
        """
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        try:
            # Get state from checkpointer
            # In MVP with MemorySaver, we need to track state separately
            # This will be improved with PostgreSQL checkpointer
            state = graph.get_state(config)
            return {
                "thread_id": thread_id,
                "state": state.values if state else None,
                "status": "found" if state else "not_found"
            }
        except Exception as e:
            logger.exception("Failed to retrieve thread state", extra={"thread_id": thread_id})
            return {
                "thread_id": thread_id,
                "state": None,
                "status": "error",
                "error": str(e)
            }
