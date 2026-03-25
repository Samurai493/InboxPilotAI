"""PostgreSQL checkpointer for LangGraph."""
from typing import Any, Dict, Iterator, List, Optional, Tuple
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import create_engine
from app.config import settings


def create_postgres_checkpointer() -> BaseCheckpointSaver:
    """Create a PostgreSQL-backed checkpointer."""
    # Use LangGraph's built-in PostgresSaver
    checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
    return checkpointer


# For MVP, we can still use MemorySaver but prepare for PostgreSQL
def get_checkpointer():
    """Get the appropriate checkpointer based on configuration."""
    # In production, use PostgreSQL
    if settings.DATABASE_URL and "postgresql" in settings.DATABASE_URL:
        try:
            return create_postgres_checkpointer()
        except Exception as e:
            print(f"Warning: Could not create PostgreSQL checkpointer: {e}")
            print("Falling back to MemorySaver")
            from langgraph.checkpoint.memory import MemorySaver
            return MemorySaver()
    else:
        # For development/testing, use MemorySaver
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
