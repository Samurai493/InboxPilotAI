"""LangSmith tracing configuration."""
from langsmith import traceable
from app.config import settings
import os


def setup_langsmith():
    """Set up LangSmith tracing."""
    if settings.LANGSMITH_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT or "inboxpilot-ai"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        # Reduce secret/PII leakage in exported traces (graph state may hold user content).
        os.environ.setdefault("LANGCHAIN_HIDE_INPUTS", "true")
        os.environ.setdefault("LANGCHAIN_HIDE_OUTPUTS", "true")
    else:
        print("Warning: LangSmith API key not set. Tracing disabled.")


# Initialize on import
setup_langsmith()


@traceable(name="process_message_workflow")
def trace_message_processing(thread_id: str, user_id: str, intent: str):
    """Trace message processing workflow."""
    pass


@traceable(name="classify_intent")
def trace_intent_classification(message: str, intent: str):
    """Trace intent classification."""
    pass


@traceable(name="draft_reply")
def trace_reply_drafting(intent: str, confidence: float):
    """Trace reply drafting."""
    pass
