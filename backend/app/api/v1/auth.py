"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user, upsert_user_from_google_token

router = APIRouter()


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthUserResponse(BaseModel):
    user_id: str
    email: str
    name: str | None = None


class PublicAuthConfigResponse(BaseModel):
    google_client_id: str | None = None


def _to_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(user_id=str(user.id), email=user.email, name=user.name)


@router.post("/auth/google", response_model=AuthUserResponse)
async def auth_google(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Verify Google ID token and create/update user row."""
    user = upsert_user_from_google_token(db, payload.id_token)
    return _to_response(user)


@router.get("/auth/me", response_model=AuthUserResponse)
async def auth_me(current_user: User = Depends(get_current_user)):
    """Return current user from Bearer Google ID token."""
    return _to_response(current_user)


@router.get("/auth/config", response_model=PublicAuthConfigResponse)
async def auth_config(response: Response):
    """Public auth config for frontend runtime environments."""
    # Safe to cache: static client id; reduces repeat cold-load latency on sign-in page.
    response.headers["Cache-Control"] = "public, max-age=300"
    return PublicAuthConfigResponse(google_client_id=settings.GOOGLE_CLIENT_ID)
