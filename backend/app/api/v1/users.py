"""User preferences endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from sqlalchemy.orm import Session
from app.services.memory_service import MemoryService

router = APIRouter()


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
