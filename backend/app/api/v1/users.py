"""User preferences and bootstrap endpoints."""
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from sqlalchemy.orm import Session
from app.services.memory_service import MemoryService
from app.models.user import User

router = APIRouter()


class UserBootstrapResponse(BaseModel):
    """Returned after creating a local / browser-scoped user."""

    id: str
    email: str
    name: Optional[str] = None


@router.post("/users/bootstrap", response_model=UserBootstrapResponse)
async def bootstrap_user(db: Session = Depends(get_db)):
    """
    Create a new user row for this browser session (no password).
    The frontend stores `id` (UUID) and uses it for Gmail OAuth and `/process`.
    """
    guest_email = f"guest-{uuid_lib.uuid4()}@inboxpilot.local"
    user = User(email=guest_email, name="Guest")
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserBootstrapResponse(id=str(user.id), email=user.email, name=user.name)


class UserPreferencesRequest(BaseModel):
    """Request model for user preferences."""
    tone: Optional[str] = None
    reply_style: Optional[str] = None
    signature: Optional[str] = None
    auto_reply_enabled: Optional[bool] = None
    review_threshold: Optional[float] = None


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""
    tone: str
    reply_style: str
    signature: Optional[str]
    auto_reply_enabled: bool
    review_threshold: float


@router.get("/users/{user_id}/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(user_id: str, db: Session = Depends(get_db)):
    """Get user preferences."""
    preferences = MemoryService.get_user_preferences(db, user_id)
    
    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")
    
    return UserPreferencesResponse(**preferences)


@router.put("/users/{user_id}/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    user_id: str,
    request: UserPreferencesRequest,
    db: Session = Depends(get_db)
):
    """Update user preferences."""
    preferences_dict = request.dict(exclude_unset=True)
    
    try:
        preference = MemoryService.create_or_update_preferences(
            db, user_id, preferences_dict
        )
        
        return UserPreferencesResponse(
            tone=preference.tone,
            reply_style=preference.reply_style,
            signature=preference.signature,
            auto_reply_enabled=preference.auto_reply_enabled == "true",
            review_threshold=float(preference.review_threshold)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
