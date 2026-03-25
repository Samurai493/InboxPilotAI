"""Analytics endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.thread import Thread
from app.models.draft import Draft
from datetime import datetime, timedelta

router = APIRouter()


class UserAnalyticsResponse(BaseModel):
    """Response model for user analytics."""
    user_id: str
    total_messages: int
    messages_this_week: int
    draft_acceptance_rate: float
    average_confidence: float
    time_saved_estimate: int  # in minutes


@router.get("/analytics/user/{user_id}", response_model=UserAnalyticsResponse)
async def get_user_analytics(user_id: str, db: Session = Depends(get_db)):
    """Get analytics for a specific user."""
    # Get total messages
    total_threads = db.query(Thread).filter(Thread.user_id == user_id).count()
    
    # Get messages this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    threads_this_week = db.query(Thread).filter(
        Thread.user_id == user_id,
        Thread.created_at >= week_ago
    ).count()
    
    # Get draft acceptance rate (simplified - in production would track actual acceptances)
    approved_drafts = db.query(Draft).filter(
        Draft.thread_id.in_(
            db.query(Thread.id).filter(Thread.user_id == user_id)
        ),
        Draft.is_approved == True
    ).count()
    
    total_drafts = db.query(Draft).filter(
        Draft.thread_id.in_(
            db.query(Thread.id).filter(Thread.user_id == user_id)
        )
    ).count()
    
    acceptance_rate = (approved_drafts / total_drafts * 100) if total_drafts > 0 else 0.0
    
    # Get average confidence
    avg_confidence_result = db.query(
        func.avg(func.cast(Draft.confidence_score, db.Float))
    ).filter(
        Draft.thread_id.in_(
            db.query(Thread.id).filter(Thread.user_id == user_id)
        )
    ).scalar()
    
    avg_confidence = float(avg_confidence_result) if avg_confidence_result else 0.0
    
    # Estimate time saved (5 minutes per message processed)
    time_saved = total_threads * 5
    
    return UserAnalyticsResponse(
        user_id=user_id,
        total_messages=total_threads,
        messages_this_week=threads_this_week,
        draft_acceptance_rate=acceptance_rate,
        average_confidence=avg_confidence,
        time_saved_estimate=time_saved
    )
