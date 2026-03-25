"""Service for executing LangGraph workflows."""
import uuid
from typing import Dict, Any
from langsmith import traceable
from app.graphs.main_graph import graph
from app.graphs.state import InboxPilotState
from app.services.tracing import trace_message_processing


class GraphService:
    """Service for managing graph execution."""
    
    @staticmethod
    def process_message(
        user_id: str,
        raw_message: str,
        message_id: str = None
    ) -> Dict[str, Any]:
        """
        Process a message through the workflow.
        
        Args:
            user_id: User identifier
            raw_message: Raw message text
            message_id: Optional external message ID
            
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
            "audit_log": []
        }
        
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
            return {
                "thread_id": thread_id,
                "state": None,
                "status": "error",
                "error": str(e)
            }
