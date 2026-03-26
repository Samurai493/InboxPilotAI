"""Google ID token authentication helpers."""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def _verify_google_token(token: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID is not configured")
    try:
        return google_id_token.verify_oauth2_token(
            token,
            GoogleRequest(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {e}")


def upsert_user_from_google_token(db: Session, token: str) -> User:
    claims = _verify_google_token(token)
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google token missing email claim")
    name = claims.get("name")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name)
        db.add(user)
    elif name and user.name != name:
        user.name = name

    db.commit()
    db.refresh(user)
    return user


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if not creds:
        return None
    return upsert_user_from_google_token(db, creds.credentials)


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def resolve_user_id_or_current(user_id: str | None, current_user: User | None) -> str:
    if user_id:
        try:
            uid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be a UUID")
        if current_user and uid != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot access another user's data")
        return str(uid)
    if current_user:
        return str(current_user.id)
    raise HTTPException(
        status_code=401,
        detail="Provide user_id or authenticate with Bearer Google ID token",
    )
