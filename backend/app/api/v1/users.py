"""User preferences and bootstrap endpoints."""
import logging
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter
from app.services.auth_service import create_guest_access_token, get_current_user, require_user_context
from app.services.memory_service import MemoryService
from app.services.user_llm_credentials_service import (
    get_public_status,
    save_credentials,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class UserBootstrapResponse(BaseModel):
    """Returned after creating a local / browser-scoped user."""

    id: str
    email: str
    name: Optional[str] = None
    # Deprecated for clients that can use httpOnly cookie; null when cookie is set.
    guest_access_token: Optional[str] = None


@router.post("/users/bootstrap", response_model=UserBootstrapResponse)
@limiter.limit("30/minute")
async def bootstrap_user(request: Request, db: Session = Depends(get_db)):
    """
    Create a new user row for this browser session (no password).
    Sets an httpOnly guest session cookie; optional legacy Bearer token is no longer returned in JSON.
    """
    guest_email = f"guest-{uuid_lib.uuid4()}@inboxpilot.local"
    user = User(email=guest_email, name="Guest")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_guest_access_token(user.id)
    logger.info("user_bootstrap", extra={"user_id": str(user.id), "guest": True})
    secure = settings.ENVIRONMENT.lower() == "production"
    max_age = max(60, settings.GUEST_TOKEN_EXPIRE_DAYS * 24 * 3600)
    resp = JSONResponse(
        content={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "guest_access_token": None,
        }
    )
    resp.set_cookie(
        key=settings.GUEST_SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return resp


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


class UserLlmCredentialsStatusResponse(BaseModel):
    """Whether each provider slot has a stored secret (no key material)."""

    has_openai: bool
    has_anthropic: bool
    has_gemini: bool


class UserLlmCredentialsPutRequest(BaseModel):
    """Omit a field to leave it unchanged; send empty string to clear that slot."""

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


@router.get(
    "/users/{user_id}/llm-credentials/status",
    response_model=UserLlmCredentialsStatusResponse,
)
async def get_llm_credentials_status(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_user_context(current_user, user_id)
    st = get_public_status(db, user_id)
    return UserLlmCredentialsStatusResponse(**st)


@router.put(
    "/users/{user_id}/llm-credentials",
    response_model=UserLlmCredentialsStatusResponse,
)
async def put_llm_credentials(
    user_id: str,
    body: UserLlmCredentialsPutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Encrypt and store per-user LLM API keys (Fernet at rest)."""
    require_user_context(current_user, user_id)
    data = body.model_dump(exclude_unset=True)
    kwargs: dict = {}
    if "openai_api_key" in data:
        v = data["openai_api_key"]
        if v is None or (isinstance(v, str) and not v.strip()):
            kwargs["clear_openai"] = True
        else:
            kwargs["openai_api_key"] = str(v).strip()
    if "anthropic_api_key" in data:
        v = data["anthropic_api_key"]
        if v is None or (isinstance(v, str) and not v.strip()):
            kwargs["clear_anthropic"] = True
        else:
            kwargs["anthropic_api_key"] = str(v).strip()
    if "gemini_api_key" in data:
        v = data["gemini_api_key"]
        if v is None or (isinstance(v, str) and not v.strip()):
            kwargs["clear_gemini"] = True
        else:
            kwargs["gemini_api_key"] = str(v).strip()

    try:
        save_credentials(db, user_id, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    st = get_public_status(db, user_id)
    return UserLlmCredentialsStatusResponse(**st)
