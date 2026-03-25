"""User preferences model."""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base, TimestampMixin


class UserPreference(Base, TimestampMixin):
    """User preferences for tone, signature, and reply style."""
    __tablename__ = "user_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Tone preferences
    tone = Column(String(50), default="professional", nullable=False)  # professional, casual, friendly, formal
    reply_style = Column(String(50), default="concise", nullable=False)  # concise, detailed, brief
    
    # Signature
    signature = Column(Text, nullable=True)
    
    # Additional preferences
    auto_reply_enabled = Column(String(10), default="false", nullable=False)  # "true" or "false" as string for JSON compatibility
    review_threshold = Column(String(10), default="0.7", nullable=False)  # Confidence threshold for auto-approval
