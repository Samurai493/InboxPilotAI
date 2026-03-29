"""Review queue endpoints."""
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.review import Review
from app.models.thread import Thread
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.llm_request_context import LlmRequestSecrets
from app.services.user_llm_credentials_service import get_decrypted_keys
import uuid
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


class ReviewResponse(BaseModel):
    """Response model for review."""

    id: str
    thread_id: str
    user_id: str
    draft_reply: str
    risk_flags: Optional[List[str]]
    confidence_score: Optional[float]
    intent: Optional[str]
    status: str
    created_at: str


class ReviewListResponse(BaseModel):
    """Response model for review list."""

    reviews: List[ReviewResponse]
    total: int


class ReviewDecisionRequest(BaseModel):
    """Request model for review decision."""

    approved: bool
    edited_draft: Optional[str] = None
    rejection_reason: Optional[str] = None


def _to_review_response(r: Review) -> ReviewResponse:
    return ReviewResponse(
        id=str(r.id),
        thread_id=str(r.thread_id),
        user_id=str(r.user_id),
        draft_reply=r.draft_reply,
        risk_flags=r.risk_flags,
        confidence_score=float(r.confidence_score) if r.confidence_score else None,
        intent=r.intent,
        status=r.status,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


@router.get("/reviews/pending", response_model=ReviewListResponse)
async def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pending reviews for the authenticated user only."""
    reviews = (
        db.query(Review)
        .filter(Review.status == "pending", Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    return ReviewListResponse(
        reviews=[_to_review_response(r) for r in reviews],
        total=len(reviews),
    )


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific review (owner only)."""
    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID")

    review = db.query(Review).filter(Review.id == review_uuid).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return _to_review_response(review)


@router.post("/reviews/{review_id}/approve")
async def approve_review(
    review_id: str,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a review (owner only)."""
    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID")

    review = db.query(Review).filter(Review.id == review_uuid).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if review.status != "pending":
        raise HTTPException(status_code=400, detail="Review already processed")

    # Update review
    review.status = "approved" if request.approved else "rejected"
    review.approved = request.approved
    review.reviewed_at = datetime.utcnow().isoformat()

    if request.edited_draft:
        review.edited_draft = request.edited_draft
        review.status = "edited"

    if request.rejection_reason:
        review.rejection_reason = request.rejection_reason

    db.commit()

    # Resume the workflow
    from app.graphs.main_graph import graph

    config = {
        "configurable": {
            "thread_id": str(review.thread_id),
        }
    }

    try:
        from langgraph.types import Command

        creds = get_decrypted_keys(db, str(review.user_id))
        with LlmRequestSecrets(
            openai_api_key=creds["openai_api_key"],
            anthropic_api_key=creds["anthropic_api_key"],
            gemini_api_key=creds["gemini_api_key"],
        ):
            graph.invoke(Command(resume=request.approved), config=config)
        return {
            "review_id": review_id,
            "status": "approved" if request.approved else "rejected",
            "workflow_resumed": True,
        }
    except Exception:
        logger.exception(
            "Review workflow resume failed",
            extra={"review_id": review_id, "thread_id": str(review.thread_id)},
        )
        return {
            "review_id": review_id,
            "status": "approved" if request.approved else "rejected",
            "workflow_resumed": False,
        }


@router.post("/reviews/{review_id}/reject")
async def reject_review(
    review_id: str,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a review (alias for approve with approved=false)."""
    body = ReviewDecisionRequest(
        approved=False,
        edited_draft=request.edited_draft,
        rejection_reason=request.rejection_reason,
    )
    return await approve_review(review_id, body, db, current_user)
