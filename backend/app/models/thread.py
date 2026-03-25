"""Thread model."""
from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base, TimestampMixin


class Thread(Base, TimestampMixin):
    """Thread model for tracking message processing workflows."""
    __tablename__ = "threads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)  # LangGraph thread_id
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed, interrupted
    state_snapshot = Column(JSON, nullable=True)  # Last state snapshot
    trace_id = Column(String(255), nullable=True, index=True)  # LangSmith trace ID
    
    # Relationships
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="thread", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="thread", cascade="all, delete-orphan")
