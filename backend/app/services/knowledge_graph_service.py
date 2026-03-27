"""Persistent knowledge graph service for user memory."""
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.knowledge_entity import KnowledgeEntity
from app.models.knowledge_relation import KnowledgeRelation


def _normalize_key(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text[:500]


def _user_uuid(user_id: str | None) -> uuid.UUID | None:
    if not user_id:
        return None
    try:
        return uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None


class KnowledgeGraphService:
    """Read/write operations for a lightweight persistent knowledge graph."""

    @staticmethod
    def upsert_entity(
        db: Session,
        *,
        user_id: str,
        entity_type: str,
        canonical_name: str,
        metadata: dict[str, Any] | None = None,
        confidence: float = 0.8,
    ) -> KnowledgeEntity | None:
        uid = _user_uuid(user_id)
        name = (canonical_name or "").strip()
        etype = (entity_type or "").strip().lower()
        if not uid or not name or not etype:
            return None

        key = _normalize_key(name)
        row = (
            db.query(KnowledgeEntity)
            .filter(
                KnowledgeEntity.user_id == uid,
                KnowledgeEntity.entity_type == etype,
                KnowledgeEntity.normalized_key == key,
            )
            .first()
        )
        if row:
            row.canonical_name = name
            row.confidence = max(row.confidence or 0.0, confidence)
            if metadata:
                merged = dict(row.extra_metadata or {})
                merged.update(metadata)
                row.extra_metadata = merged
            db.flush()
            return row

        row = KnowledgeEntity(
            user_id=uid,
            entity_type=etype,
            canonical_name=name,
            normalized_key=key,
            confidence=confidence,
            extra_metadata=metadata or None,
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def add_relation(
        db: Session,
        *,
        user_id: str,
        source: KnowledgeEntity,
        target: KnowledgeEntity,
        relation_type: str,
        confidence: float = 0.75,
        evidence_message_id: str | None = None,
        evidence_thread_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeRelation | None:
        uid = _user_uuid(user_id)
        rtype = (relation_type or "").strip().upper()
        if not uid or not rtype:
            return None

        existing = (
            db.query(KnowledgeRelation)
            .filter(
                KnowledgeRelation.user_id == uid,
                KnowledgeRelation.source_entity_id == source.id,
                KnowledgeRelation.target_entity_id == target.id,
                KnowledgeRelation.relation_type == rtype,
                KnowledgeRelation.evidence_thread_id == evidence_thread_id,
            )
            .first()
        )
        if existing:
            existing.confidence = max(existing.confidence or 0.0, confidence)
            if metadata:
                merged = dict(existing.extra_metadata or {})
                merged.update(metadata)
                existing.extra_metadata = merged
            db.flush()
            return existing

        rel = KnowledgeRelation(
            user_id=uid,
            source_entity_id=source.id,
            target_entity_id=target.id,
            relation_type=rtype,
            confidence=confidence,
            evidence_message_id=evidence_message_id,
            evidence_thread_id=evidence_thread_id,
            extra_metadata=metadata or None,
        )
        db.add(rel)
        db.flush()
        return rel

    @staticmethod
    def get_recent_context(
        db: Session,
        *,
        user_id: str,
        limit_entities: int = 10,
        limit_relations: int = 12,
    ) -> dict[str, Any]:
        uid = _user_uuid(user_id)
        if not uid:
            return {"entities": [], "relations": []}

        entities = (
            db.query(KnowledgeEntity)
            .filter(KnowledgeEntity.user_id == uid)
            .order_by(KnowledgeEntity.updated_at.desc())
            .limit(limit_entities)
            .all()
        )
        relations = (
            db.query(KnowledgeRelation)
            .filter(KnowledgeRelation.user_id == uid)
            .order_by(KnowledgeRelation.updated_at.desc())
            .limit(limit_relations)
            .all()
        )

        return {
            "entities": [
                {
                    "id": str(row.id),
                    "type": row.entity_type,
                    "name": row.canonical_name,
                    "confidence": row.confidence,
                    "metadata": row.extra_metadata or {},
                }
                for row in entities
            ],
            "relations": [
                {
                    "source_entity_id": str(row.source_entity_id),
                    "target_entity_id": str(row.target_entity_id),
                    "type": row.relation_type,
                    "confidence": row.confidence,
                    "thread_id": row.evidence_thread_id,
                    "message_id": row.evidence_message_id,
                    "metadata": row.extra_metadata or {},
                }
                for row in relations
            ],
        }

    @staticmethod
    def persist_from_state(db: Session, state: dict[str, Any]) -> dict[str, Any]:
        """Extract minimal entities/relations from workflow state and persist them."""
        user_id = state.get("user_id")
        if not isinstance(user_id, str) or not user_id.strip():
            return {
                "persisted_entities": 0,
                "persisted_relations": 0,
                "written_entities": [],
                "written_relations": [],
            }

        thread_id = state.get("thread_id")
        message_id = state.get("message_id")
        sender_profile = state.get("sender_profile") or {}
        sender_email = (sender_profile.get("email") or "").strip()
        sender_name = (sender_profile.get("name") or "").strip()
        subject = (sender_profile.get("subject") or "").strip()
        intent = (state.get("intent") or "").strip().lower()
        tasks = state.get("extracted_tasks") or []

        persisted_entities = 0
        persisted_relations = 0
        written_entity_rows: dict[str, dict[str, Any]] = {}
        written_relation_rows: list[dict[str, Any]] = []

        def _note_entity(row: KnowledgeEntity | None) -> None:
            if not row:
                return
            written_entity_rows[str(row.id)] = {
                "id": str(row.id),
                "type": row.entity_type,
                "name": row.canonical_name,
            }

        sender = None
        if sender_email or sender_name:
            sender = KnowledgeGraphService.upsert_entity(
                db,
                user_id=user_id,
                entity_type="person",
                canonical_name=sender_email or sender_name,
                metadata={"email": sender_email or None, "name": sender_name or None},
                confidence=0.9 if sender_email else 0.75,
            )
            if sender:
                persisted_entities += 1
                _note_entity(sender)

        intent_entity = None
        if intent:
            intent_entity = KnowledgeGraphService.upsert_entity(
                db,
                user_id=user_id,
                entity_type="intent",
                canonical_name=intent,
                metadata=None,
                confidence=0.85,
            )
            if intent_entity:
                persisted_entities += 1
                _note_entity(intent_entity)

        if sender and intent_entity:
            rel = KnowledgeGraphService.add_relation(
                db,
                user_id=user_id,
                source=sender,
                target=intent_entity,
                relation_type="HAS_INTENT",
                evidence_message_id=message_id if isinstance(message_id, str) else None,
                evidence_thread_id=thread_id if isinstance(thread_id, str) else None,
            )
            if rel:
                persisted_relations += 1
                written_relation_rows.append(
                    {
                        "type": rel.relation_type,
                        "source_id": str(sender.id),
                        "target_id": str(intent_entity.id),
                        "source_name": sender.canonical_name,
                        "target_name": intent_entity.canonical_name,
                    }
                )

        if subject:
            subject_entity = KnowledgeGraphService.upsert_entity(
                db,
                user_id=user_id,
                entity_type="topic",
                canonical_name=subject,
                metadata={"source": "email_subject"},
                confidence=0.8,
            )
            if subject_entity:
                persisted_entities += 1
                _note_entity(subject_entity)
                if sender:
                    rel = KnowledgeGraphService.add_relation(
                        db,
                        user_id=user_id,
                        source=sender,
                        target=subject_entity,
                        relation_type="CONTACTED_ABOUT",
                        evidence_message_id=message_id if isinstance(message_id, str) else None,
                        evidence_thread_id=thread_id if isinstance(thread_id, str) else None,
                    )
                    if rel:
                        persisted_relations += 1
                        written_relation_rows.append(
                            {
                                "type": rel.relation_type,
                                "source_id": str(sender.id),
                                "target_id": str(subject_entity.id),
                                "source_name": sender.canonical_name,
                                "target_name": subject_entity.canonical_name,
                            }
                        )

        if isinstance(tasks, list):
            for task in tasks[:15]:
                if not isinstance(task, dict):
                    continue
                desc = (task.get("description") or "").strip()
                if not desc:
                    continue
                task_entity = KnowledgeGraphService.upsert_entity(
                    db,
                    user_id=user_id,
                    entity_type="task_item",
                    canonical_name=desc[:500],
                    metadata={
                        "priority": task.get("priority"),
                        "due_date": task.get("due_date"),
                    },
                    confidence=0.8,
                )
                if not task_entity:
                    continue
                persisted_entities += 1
                _note_entity(task_entity)
                if sender:
                    rel = KnowledgeGraphService.add_relation(
                        db,
                        user_id=user_id,
                        source=sender,
                        target=task_entity,
                        relation_type="REQUESTED_ACTION",
                        evidence_message_id=message_id if isinstance(message_id, str) else None,
                        evidence_thread_id=thread_id if isinstance(thread_id, str) else None,
                    )
                    if rel:
                        persisted_relations += 1
                        written_relation_rows.append(
                            {
                                "type": rel.relation_type,
                                "source_id": str(sender.id),
                                "target_id": str(task_entity.id),
                                "source_name": sender.canonical_name,
                                "target_name": task_entity.canonical_name,
                            }
                        )

        db.commit()
        return {
            "persisted_entities": persisted_entities,
            "persisted_relations": persisted_relations,
            "written_entities": list(written_entity_rows.values()),
            "written_relations": written_relation_rows,
        }
