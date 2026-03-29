"""Authentication: Google ID tokens and signed guest session tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

GUEST_TOKEN_TYP = "guest"


def _verify_google_token(token: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID is not configured")
    try:
        return google_id_token.verify_oauth2_token(
            token,
            GoogleRequest(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google ID token")


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


def create_guest_access_token(user_id: UUID) -> str:
    """
    HS256 JWT for browser guests (bootstrap users). Not a Google token.

    Tokens are returned in JSON today (typical SPA + localStorage). For stronger XSS resistance,
    move to an httpOnly, Secure, SameSite cookie on bootstrap and stop exposing the raw JWT to
    JavaScript; the backend would read the cookie and validate like Bearer.
    """
    exp = datetime.now(timezone.utc) + timedelta(days=settings.GUEST_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "typ": GUEST_TOKEN_TYP,
        "exp": exp,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def user_from_guest_token(db: Session, token: str) -> User | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("typ") != GUEST_TOKEN_TYP:
            return None
        uid = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        return None
    return db.query(User).filter(User.id == uid).first()


def get_current_user_optional(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if creds:
        token = creds.credentials
        user = user_from_guest_token(db, token)
        if user:
            return user
        try:
            return upsert_user_from_google_token(db, token)
        except HTTPException:
            return None

    cookie_token = request.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    if cookie_token:
        return user_from_guest_token(db, cookie_token)
    return None


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_user_context(current_user: User, user_id: str | None) -> str:
    """
    Authenticated identity is always current_user. Optional user_id must match (client sanity check).
    """
    if user_id:
        try:
            uid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be a UUID")
        if uid != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot access another user's data")
    return str(current_user.id)


def resolve_user_id_or_current(user_id: str | None, current_user: User | None) -> str:
    """
    Deprecated for secured routes: use get_current_user + require_user_context.
    Kept for gradual migration / tests.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return require_user_context(current_user, user_id)
