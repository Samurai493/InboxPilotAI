"""Knowledge graph relation model."""
import uuid

from sqlalchemy import Column, Float, ForeignKey, Index, String, JSON
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class KnowledgeRelation(Base, TimestampMixin):
    """Directed relation between two entities for persistent graph memory."""

    __tablename__ = "knowledge_relations"
    __table_args__ = (
        Index("ix_knowledge_relations_user_updated", "user_id", "updated_at"),
        Index("ix_knowledge_relations_source_target", "source_entity_id", "target_entity_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    relation_type = Column(String(80), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.75)
    evidence_message_id = Column(String(255), nullable=True, index=True)
    evidence_thread_id = Column(String(255), nullable=True, index=True)
    extra_metadata = Column("metadata", JSON, nullable=True)
