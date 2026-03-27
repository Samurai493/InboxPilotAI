"""Knowledge graph entity model."""
import uuid

from sqlalchemy import Column, Float, ForeignKey, Index, String, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class KnowledgeEntity(Base, TimestampMixin):
    """Canonical entity for persistent graph memory."""

    __tablename__ = "knowledge_entities"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "entity_type",
            "normalized_key",
            name="uq_knowledge_entities_user_type_key",
        ),
        Index("ix_knowledge_entities_user_updated", "user_id", "updated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    canonical_name = Column(String(500), nullable=False)
    normalized_key = Column(String(500), nullable=False)
    confidence = Column(Float, nullable=False, default=0.8)
    extra_metadata = Column("metadata", JSON, nullable=True)
