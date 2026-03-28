"""Metrics endpoints for admin dashboard."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.thread import Thread
from app.models.draft import Draft
from app.models.review import Review
from datetime import datetime, timedelta

router = APIRouter()


class MetricsResponse(BaseModel):
    """Response model for metrics."""
    total_threads: int
    successful_threads: int
    failed_threads: int
    average_confidence: Optional[float]
    total_reviews: int
    pending_reviews: int
    approved_reviews: int
    rejected_reviews: int


@router.get("/metrics/summary", response_model=MetricsResponse)
async def get_metrics_summary(db: Session = Depends(get_db)):
    """Get summary metrics."""
    # Thread metrics
    total_threads = db.query(Thread).count()
    successful_threads = db.query(Thread).filter(Thread.status == "completed").count()
    failed_threads = db.query(Thread).filter(Thread.status == "failed").count()
    
    # Confidence metrics (Draft.confidence_score is already Float; avoid invalid db.Float cast)
    avg_confidence_result = db.query(func.avg(Draft.confidence_score)).scalar()
    avg_confidence = float(avg_confidence_result) if avg_confidence_result is not None else None
    
    # Review metrics
    total_reviews = db.query(Review).count()
    pending_reviews = db.query(Review).filter(Review.status == "pending").count()
    approved_reviews = db.query(Review).filter(Review.status == "approved").count()
    rejected_reviews = db.query(Review).filter(Review.status == "rejected").count()
    
    return MetricsResponse(
        total_threads=total_threads,
        successful_threads=successful_threads,
        failed_threads=failed_threads,
        average_confidence=avg_confidence,
        total_reviews=total_reviews,
        pending_reviews=pending_reviews,
        approved_reviews=approved_reviews,
        rejected_reviews=rejected_reviews
    )


@router.get("/metrics/timeline")
async def get_metrics_timeline(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get metrics over time."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily counts
    daily_threads = db.query(
        func.date(Thread.created_at).label("date"),
        func.count(Thread.id).label("count")
    ).filter(
        Thread.created_at >= start_date
    ).group_by(
        func.date(Thread.created_at)
    ).all()
    
    daily_reviews = db.query(
        func.date(Review.created_at).label("date"),
        func.count(Review.id).label("count")
    ).filter(
        Review.created_at >= start_date
    ).group_by(
        func.date(Review.created_at)
    ).all()
    
    return {
        "threads": [{"date": str(d[0]), "count": d[1]} for d in daily_threads],
        "reviews": [{"date": str(d[0]), "count": d[1]} for d in daily_reviews]
    }
