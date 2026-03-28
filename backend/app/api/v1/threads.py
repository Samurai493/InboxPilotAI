"""Thread endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user, require_user_context
from app.services.graph_service import GraphService
from app.services.workflow_thread_service import (
    get_thread_row_by_langgraph_id,
    latest_thread_for_gmail_message,
    list_threads_for_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ThreadStateResponse(BaseModel):
    """Response model for thread state."""

    thread_id: str
    state: dict | None = None
    status: str
    error: str | None = None
    source: str | None = None


class ThreadSummaryItem(BaseModel):
    """One persisted workflow run for history UI."""

    id: str
    thread_id: str
    status: str
    gmail_message_id: str | None = None
    created_at: str | None = None
    intent: str | None = None
    subject: str | None = None
    selected_agent: str | None = None


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummaryItem]


class LatestForMessageResponse(BaseModel):
    thread_id: str
    status: str
    created_at: str | None = None


def _row_to_summary(row) -> ThreadSummaryItem:
    snap = row.state_snapshot or {}
    sp = snap.get("sender_profile") or {}
    return ThreadSummaryItem(
        id=str(row.id),
        thread_id=row.thread_id,
        status=row.status,
        gmail_message_id=row.gmail_message_id,
        created_at=row.created_at.isoformat() if row.created_at else None,
        intent=snap.get("intent"),
        subject=sp.get("subject"),
        selected_agent=snap.get("selected_agent"),
    )


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    user_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List persisted workflow runs for the user (newest first)."""
    uid = require_user_context(current_user, user_id)
    try:
        rows = list_threads_for_user(db, uid, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ThreadListResponse(threads=[_row_to_summary(r) for r in rows])


@router.get("/threads/by-gmail/{gmail_message_id}", response_model=LatestForMessageResponse)
async def get_latest_thread_for_gmail_message(
    gmail_message_id: str,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recent persisted run for this Gmail message id (same user)."""
    uid = require_user_context(current_user, user_id)
    try:
        row = latest_thread_for_gmail_message(db, uid, gmail_message_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=404, detail="No saved run for this message")
    return LatestForMessageResponse(
        thread_id=row.thread_id,
        status=row.status,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/threads/{thread_id}", response_model=ThreadStateResponse)
async def get_thread(
    thread_id: str,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get thread state from the LangGraph checkpointer when available, else from the database snapshot.
    """
    uid = require_user_context(current_user, user_id)

    try:
        result = GraphService.get_thread_state(thread_id, db=db, request_user_id=uid)
    except Exception as e:
        logger.exception(
            "Unhandled error in GET /api/v1/threads/{thread_id}",
            extra={"thread_id": thread_id},
        )
        raise HTTPException(status_code=500, detail=str(e)) from e

    if result.get("status") == "forbidden":
        raise HTTPException(status_code=403, detail=result.get("error") or "Forbidden")

    return ThreadStateResponse(
        thread_id=result["thread_id"],
        state=result.get("state"),
        status=result.get("status", "not_found"),
        error=result.get("error"),
        source=result.get("source"),
    )


def _assert_thread_owned(db: Session, thread_id: str, current_user: User) -> None:
    """Ensure checkpoint or DB row belongs to current_user."""
    from app.graphs.main_graph import graph

    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
    except Exception:
        state = None

    if state and getattr(state, "values", None):
        uid_in_state = state.values.get("user_id")
        if uid_in_state is not None:
            if str(uid_in_state) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Forbidden")
            return

    row = get_thread_row_by_langgraph_id(db, thread_id)
    if row:
        if row.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return

    # No state and no row — let handler return not_found without leaking existence
    return


@router.get("/threads/{thread_id}/history")
async def get_thread_history(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get thread execution history (checkpoint history).
    """
    _assert_thread_owned(db, thread_id, current_user)

    from app.graphs.main_graph import graph

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        history = []
        state = graph.get_state(config)

        if state:
            history.append(
                {
                    "checkpoint_id": getattr(state, "id", None),
                    "values": state.values if hasattr(state, "values") else None,
                    "metadata": state.metadata if hasattr(state, "metadata") else None,
                    "parent_checkpoint_id": getattr(state, "parent_checkpoint_id", None),
                }
            )

        return {
            "thread_id": thread_id,
            "history": history,
            "status": "found" if history else "not_found",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unhandled error in GET /api/v1/threads/{thread_id}/history",
            extra={"thread_id": thread_id},
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
