"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.config import settings
from app.models.base import Base

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    import app.models  # noqa: F401 — register models on Base.metadata

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
