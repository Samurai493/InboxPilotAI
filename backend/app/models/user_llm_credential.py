"""Encrypted per-user LLM provider API keys (optional; env keys remain fallback)."""
from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class UserLlmCredential(Base, TimestampMixin):
    """At most one row per user; ciphertext columns are Fernet tokens."""

    __tablename__ = "user_llm_credentials"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    encrypted_openai_key = Column(Text, nullable=True)
    encrypted_anthropic_key = Column(Text, nullable=True)
    encrypted_gemini_key = Column(Text, nullable=True)
