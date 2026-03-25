"""Draft reply model."""
from sqlalchemy import Column, Text, ForeignKey, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base, TimestampMixin


class Draft(Base, TimestampMixin):
    """Draft reply model."""
    __tablename__ = "drafts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    human_edited = Column(Boolean, default=False, nullable=False)
    edited_content = Column(Text, nullable=True)
    
    # Relationships
    thread = relationship("Thread", back_populates="drafts")
