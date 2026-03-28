"""User preferences and bootstrap endpoints."""
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter
from app.services.auth_service import create_guest_access_token, get_current_user, require_user_context
from app.services.memory_service import MemoryService

router = APIRouter()


class UserBootstrapResponse(BaseModel):
    """Returned after creating a local / browser-scoped user."""

    id: str
    email: str
    name: Optional[str] = None
    guest_access_token: str


@router.post("/users/bootstrap", response_model=UserBootstrapResponse)
@limiter.limit("30/minute")
async def bootstrap_user(request: Request, db: Session = Depends(get_db)):
    """
    Create a new user row for this browser session (no password).
    Store guest_access_token and send it as Bearer for API calls until Google sign-in.
    """
    guest_email = f"guest-{uuid_lib.uuid4()}@inboxpilot.local"
    user = User(email=guest_email, name="Guest")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_guest_access_token(user.id)
    return UserBootstrapResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        guest_access_token=token,
    )


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
async def get_user_preferences(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user preferences for the authenticated user only."""
    require_user_context(current_user, user_id)
    preferences = MemoryService.get_user_preferences(db, user_id)

    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return UserPreferencesResponse(**preferences)


@router.put("/users/{user_id}/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    user_id: str,
    request: UserPreferencesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user preferences for the authenticated user only."""
    require_user_context(current_user, user_id)
    preferences_dict = request.model_dump(exclude_unset=True)

    try:
        preference = MemoryService.create_or_update_preferences(
            db, user_id, preferences_dict
        )

        return UserPreferencesResponse(
            tone=preference.tone,
            reply_style=preference.reply_style,
            signature=preference.signature,
            auto_reply_enabled=preference.auto_reply_enabled == "true",
            review_threshold=float(preference.review_threshold),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
