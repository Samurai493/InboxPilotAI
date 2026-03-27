"""Database connection and session management."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.models.base import Base

# Fail fast when Postgres is unreachable (e.g. wrong DATABASE_URL on Cloud Run).
_connect_args = {}
if settings.DATABASE_URL.startswith("postgresql"):
    _connect_args["connect_timeout"] = 10

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL query logging
    connect_args=_connect_args,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_threads_history_columns() -> None:
    """Align legacy ``threads`` rows with the ORM (create_all never ALTERs existing tables)."""
    if not settings.DATABASE_URL.startswith("postgresql"):
        return
    try:
        insp = inspect(engine)
    except Exception:
        return
    if not insp.has_table("threads"):
        return
    col_names = {c["name"] for c in insp.get_columns("threads")}
    with engine.begin() as conn:
        if "gmail_message_id" not in col_names:
            conn.execute(text("ALTER TABLE threads ADD COLUMN gmail_message_id VARCHAR(255)"))
        if "error_message" not in col_names:
            conn.execute(text("ALTER TABLE threads ADD COLUMN error_message TEXT"))
    insp = inspect(engine)
    index_names = {i["name"] for i in insp.get_indexes("threads")}
    with engine.begin() as conn:
        if "ix_threads_user_gmail_message" not in index_names:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_threads_user_gmail_message "
                    "ON threads (user_id, gmail_message_id)"
                )
            )
        if "ix_threads_gmail_message_id" not in index_names:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_threads_gmail_message_id ON threads (gmail_message_id)"
                )
            )


def init_db():
    """Initialize database tables."""
    import app.models  # noqa: F401 — register models on Base.metadata

    Base.metadata.create_all(bind=engine)
    _ensure_threads_history_columns()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
