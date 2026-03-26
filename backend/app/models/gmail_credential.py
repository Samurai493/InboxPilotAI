"""Stored Gmail OAuth tokens per user."""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin


class GmailCredential(Base, TimestampMixin):
    """One row per user with Google OAuth tokens for Gmail API."""

    __tablename__ = "gmail_credentials"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    refresh_token = Column(Text, nullable=False)
    access_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)
    google_account_email = Column(String(320), nullable=True)
