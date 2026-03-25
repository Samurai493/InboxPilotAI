"""Review queue endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.review import Review
from app.models.thread import Thread
import uuid
from datetime import datetime

router = APIRouter()


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


@router.get("/reviews/pending", response_model=ReviewListResponse)
async def get_pending_reviews(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get pending reviews."""
    query = db.query(Review).filter(Review.status == "pending")
    
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.filter(Review.user_id == user_uuid)
        except ValueError:
            pass
    
    reviews = query.order_by(Review.created_at.desc()).all()
    
    review_responses = [
        ReviewResponse(
            id=str(r.id),
            thread_id=str(r.thread_id),
            user_id=str(r.user_id),
            draft_reply=r.draft_reply,
            risk_flags=r.risk_flags,
            confidence_score=float(r.confidence_score) if r.confidence_score else None,
            intent=r.intent,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else ""
        )
        for r in reviews
    ]
    
    return ReviewListResponse(reviews=review_responses, total=len(review_responses))


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str, db: Session = Depends(get_db)):
    """Get a specific review."""
    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID")
    
    review = db.query(Review).filter(Review.id == review_uuid).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return ReviewResponse(
        id=str(review.id),
        thread_id=str(review.thread_id),
        user_id=str(review.user_id),
        draft_reply=review.draft_reply,
        risk_flags=review.risk_flags,
        confidence_score=float(review.confidence_score) if review.confidence_score else None,
        intent=review.intent,
        status=review.status,
        created_at=review.created_at.isoformat() if review.created_at else ""
    )


@router.post("/reviews/{review_id}/approve")
async def approve_review(
    review_id: str,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db)
):
    """Approve a review."""
    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review ID")
    
    review = db.query(Review).filter(Review.id == review_uuid).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
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
    from app.services.graph_service import GraphService
    from app.graphs.main_graph import graph
    
    config = {
        "configurable": {
            "thread_id": str(review.thread_id)
        }
    }
    
    # Resume with the decision
    try:
        from langgraph.types import Command
        result = graph.invoke(Command(resume=request.approved), config=config)
        return {
            "review_id": review_id,
            "status": "approved" if request.approved else "rejected",
            "workflow_resumed": True,
            "result": result
        }
    except Exception as e:
        return {
            "review_id": review_id,
            "status": "approved" if request.approved else "rejected",
            "workflow_resumed": False,
            "error": str(e)
        }


@router.post("/reviews/{review_id}/reject")
async def reject_review(
    review_id: str,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db)
):
    """Reject a review (alias for approve with approved=false)."""
    request.approved = False
    return await approve_review(review_id, request, db)
