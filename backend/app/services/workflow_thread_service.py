"""Persist LangGraph workflow runs to the threads table for durable history."""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.thread import Thread
from app.services.gmail_oauth import require_user_uuid

logger = logging.getLogger(__name__)


def state_snapshot_for_db(state: dict[str, Any] | None) -> dict[str, Any] | None:
    """JSON-serializable copy (datetimes → strings)."""
    if not state:
        return None
    try:
        return json.loads(json.dumps(state, default=str))
    except (TypeError, ValueError) as e:
        logger.warning("Could not serialize state snapshot: %s", e)
        return {"_serialization_error": str(e)}


def persist_workflow_thread(
    db: Session,
    *,
    user_id: str,
    thread_id: str,
    status: str,
    state: dict[str, Any] | None,
    trace_id: str | None = None,
    gmail_message_id: str | None = None,
    error_message: str | None = None,
) -> Thread:
    """Insert a row for this workflow run (one row per process invocation)."""
    uid = require_user_uuid(user_id)
    snap = state_snapshot_for_db(state)
    row = Thread(
        user_id=uid,
        thread_id=thread_id,
        status=status,
        state_snapshot=snap,
        trace_id=trace_id,
        gmail_message_id=(gmail_message_id.strip() if gmail_message_id else None),
        error_message=error_message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_thread_row_by_langgraph_id(db: Session, thread_id: str) -> Thread | None:
    return db.query(Thread).filter(Thread.thread_id == thread_id).first()


def list_threads_for_user(
    db: Session,
    user_id: str,
    *,
    limit: int = 50,
) -> list[Thread]:
    uid = require_user_uuid(user_id)
    return (
        db.query(Thread)
        .filter(Thread.user_id == uid)
        .order_by(Thread.created_at.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )


def latest_thread_for_gmail_message(
    db: Session,
    user_id: str,
    gmail_message_id: str,
) -> Thread | None:
    uid = require_user_uuid(user_id)
    mid = gmail_message_id.strip()
    if not mid:
        return None
    return (
        db.query(Thread)
        .filter(Thread.user_id == uid, Thread.gmail_message_id == mid)
        .order_by(Thread.created_at.desc())
        .first()
    )
