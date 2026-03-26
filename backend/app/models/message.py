"""Message model."""
from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """Message model."""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False, index=True)
    message_id = Column(String(255), nullable=True)  # External message ID (e.g., Gmail)
    raw_message = Column(Text, nullable=False)
    normalized_message = Column(Text, nullable=True)
    sender_email = Column(String(255), nullable=True, index=True)
    sender_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    intent = Column(String(50), nullable=True)  # recruiter, scheduling, academic, support, billing, personal, spam
    urgency_score = Column(String(10), nullable=True)  # low, medium, high
    extra_metadata = Column("metadata", JSON, nullable=True)
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
