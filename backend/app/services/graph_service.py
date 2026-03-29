"""Service for executing LangGraph workflows."""
import logging
import uuid
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
from app.graphs.main_graph import graph
from app.graphs.state import InboxPilotState
from app.services.llm_request_context import LlmRequestSecrets
from app.services.llm_token_usage import WorkflowTokenUsageCallback
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
            "knowledge_hits": None,
            "email_context": None,
            "email_summary": None,
            "email_substance": None,
            "sender_request": None,
            "response_thinking": None,
            "follow_ups": None,
            "knowledge_written": None,
            "draft_reply": None,
            "extracted_tasks": None,
            "due_dates": None,
            "confidence_score": None,
            "final_status": "pending",
            "trace_id": None,
            "llm_token_usage": None,
            "audit_log": [],
            "use_specialist": use_specialist,
        }
        if llm_provider is not None:
            t = llm_provider.strip()
            initial_state["llm_provider"] = t if t else None
        if llm_model is not None:
            t = llm_model.strip()
            initial_state["llm_model"] = t if t else None

        # Configure graph execution
        token_cb = WorkflowTokenUsageCallback()
        config = {
            "configurable": {
                "thread_id": thread_id
            },
            "callbacks": [token_cb],
        }
        
        # Execute graph with tracing (API keys only in context — never in checkpoint state)
        try:
            intent = initial_state.get("intent", "unknown")
            trace_message_processing(thread_id, user_id, intent)

            with LlmRequestSecrets(
                openai_api_key=openai_api_key,
                anthropic_api_key=anthropic_api_key,
                gemini_api_key=gemini_api_key,
            ):
                final_state = graph.invoke(initial_state, config=config)
            usage_summary = token_cb.get_summary()
            merged_state = dict(final_state)
            merged_state["llm_token_usage"] = usage_summary
            try:
                graph.update_state(
                    config,
                    {"llm_token_usage": usage_summary},
                    as_node="finalize_output",
                )
            except Exception:
                logger.debug(
                    "Could not persist llm_token_usage to checkpointer",
                    exc_info=True,
                )

            trace_id = merged_state.get("trace_id")

            return {
                "thread_id": thread_id,
                "state": merged_state,
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
    def get_thread_state(
        thread_id: str,
        db: "Session | None" = None,
        request_user_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Get the current state of a thread.

        Prefer the in-process LangGraph checkpointer; if missing (e.g. after restart),
        fall back to ``threads.state_snapshot`` when ``db`` is provided.
        """
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        try:
            state = graph.get_state(config)
            values = state.values if state else None
            if values and request_user_id:
                uid_in_state = values.get("user_id")
                if uid_in_state is None or str(uid_in_state).strip() == "":
                    return {
                        "thread_id": thread_id,
                        "state": None,
                        "status": "forbidden",
                        "error": "Thread does not belong to this user",
                    }
                if str(uid_in_state) != str(request_user_id):
                    return {
                        "thread_id": thread_id,
                        "state": None,
                        "status": "forbidden",
                        "error": "Thread does not belong to this user",
                    }
            if values:
                return {
                    "thread_id": thread_id,
                    "state": values,
                    "status": "found",
                }

            if db is not None:
                from app.services.workflow_thread_service import get_thread_row_by_langgraph_id
                from app.services.gmail_oauth import require_user_uuid

                row = get_thread_row_by_langgraph_id(db, thread_id)
                if row:
                    if request_user_id:
                        try:
                            req = require_user_uuid(request_user_id)
                        except Exception:
                            return {
                                "thread_id": thread_id,
                                "state": None,
                                "status": "forbidden",
                                "error": "Invalid user_id",
                            }
                        if row.user_id != req:
                            return {
                                "thread_id": thread_id,
                                "state": None,
                                "status": "forbidden",
                                "error": "Thread does not belong to this user",
                            }
                    return {
                        "thread_id": thread_id,
                        "state": row.state_snapshot,
                        "status": row.status or "found",
                        "source": "database",
                    }

            return {
                "thread_id": thread_id,
                "state": None,
                "status": "not_found",
            }
        except Exception as e:
            logger.exception("Failed to retrieve thread state", extra={"thread_id": thread_id})
            return {
                "thread_id": thread_id,
                "state": None,
                "status": "error",
                "error": str(e),
            }
