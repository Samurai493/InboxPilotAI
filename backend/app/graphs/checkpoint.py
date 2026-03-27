"""LangGraph checkpointer: Postgres when `langgraph-checkpoint-postgres` is installed, else MemorySaver."""
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    PostgresSaver = None  # type: ignore[misc, assignment]

from app.config import settings


def create_postgres_checkpointer() -> Optional[BaseCheckpointSaver]:
    """Create a PostgreSQL-backed checkpointer when the optional package is installed."""
    if PostgresSaver is None:
        return None
    checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
    return checkpointer


def get_checkpointer():
    """Get the appropriate checkpointer based on configuration."""
    if (
        settings.DATABASE_URL
        and "postgresql" in settings.DATABASE_URL
        and PostgresSaver is not None
    ):
        try:
            pg = create_postgres_checkpointer()
            if pg is not None:
                return pg
        except Exception as e:
            print(f"Warning: Could not create PostgreSQL checkpointer: {e}")
            print("Falling back to MemorySaver")

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()
