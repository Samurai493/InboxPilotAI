"""Trace inspection endpoints for admin."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.models.user import User
from app.services.auth_service import require_admin

router = APIRouter()


class TraceResponse(BaseModel):
    """Response model for trace."""

    trace_id: str
    thread_id: Optional[str]
    status: str
    url: Optional[str]


@router.get("/traces")
async def list_traces(
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    _: User = Depends(require_admin),
):
    """List traces (placeholder - would integrate with LangSmith API)."""
    # In production, this would query LangSmith API
    return {
        "traces": [],
        "total": 0,
        "message": "Trace inspection requires LangSmith API integration",
    }


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    _: User = Depends(require_admin),
):
    """Get a specific trace."""
    # In production, this would fetch from LangSmith
    langsmith_url = f"https://smith.langchain.com/public/{settings.LANGSMITH_PROJECT}/runs/{trace_id}"

    return TraceResponse(
        trace_id=trace_id,
        thread_id=None,
        status="found",
        url=langsmith_url,
    )
