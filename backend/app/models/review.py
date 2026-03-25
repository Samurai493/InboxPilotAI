"""Review queue model."""
from sqlalchemy import Column, String, Text, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    """Review queue entry for human-in-the-loop approval."""
    __tablename__ = "reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Review data
    draft_reply = Column(Text, nullable=False)
    risk_flags = Column(JSON, nullable=True)  # List of risk flags
    confidence_score = Column(String(10), nullable=True)
    intent = Column(String(50), nullable=True)
    
    # Review status
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected, edited
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(String(50), nullable=True)  # ISO timestamp string
    
    # Review decision
    approved = Column(Boolean, nullable=True)
    edited_draft = Column(Text, nullable=True)  # If user edited the draft
    rejection_reason = Column(Text, nullable=True)
