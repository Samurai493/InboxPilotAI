"""Gmail OAuth: signed state, token exchange, stored credentials per user UUID."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import List
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.config import settings
from app.models.gmail_credential import GmailCredential
from app.models.user import User

GMAIL_SCOPES: List[str] = [
    # Identity scopes often come back in the token response (especially when users have
    # previously authorized the app); include them to avoid "Scope has changed" errors.
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

_STATE_TTL_SECONDS = 900


def _client_config() -> dict:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _sign_oauth_state(user_id: uuid.UUID) -> str:
    payload = {"uid": str(user_id), "exp": int(time.time()) + _STATE_TTL_SECONDS}
    raw = json.dumps(payload, sort_keys=True).encode()
    data_b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        data_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{data_b64}.{sig}"


def verify_oauth_state(state: str) -> uuid.UUID:
    if not state or "." not in state:
        raise ValueError("Invalid OAuth state")
    data_b64, sig = state.rsplit(".", 1)
    expected = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        data_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid OAuth state signature")
    pad = "=" * (-len(data_b64) % 4)
    raw = base64.urlsafe_b64decode(data_b64 + pad)
    payload = json.loads(raw.decode("utf-8"))
    if int(time.time()) > int(payload["exp"]):
        raise ValueError("OAuth state expired")
    return uuid.UUID(payload["uid"])


def create_authorization_url(user_id: uuid.UUID) -> str:
    signed = _sign_oauth_state(user_id)
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=signed,
    )
    return url


def complete_oauth(db: Session, authorization_response_url: str) -> GmailCredential:
    parsed = urlparse(authorization_response_url)
    q = parse_qs(parsed.query)
    if "error" in q:
        raise ValueError(q["error"][0])
    code = (q.get("code") or [None])[0]
    state = (q.get("state") or [None])[0]
    if not code or not state:
        raise ValueError("Missing code or state")
    user_id = verify_oauth_state(state)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    flow = Flow.from_client_config(
        _client_config(),
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    if not creds.refresh_token:
        raise ValueError("No refresh token returned; try revoking app access in Google and reconnect")

    scope_str = ",".join(creds.scopes or GMAIL_SCOPES)
    row = db.query(GmailCredential).filter(GmailCredential.user_id == user_id).first()
    if not row:
        row = GmailCredential(user_id=user_id)
        db.add(row)
    row.refresh_token = creds.refresh_token
    row.access_token = creds.token
    row.token_expiry = creds.expiry
    row.scopes = scope_str

    svc = build("gmail", "v1", credentials=creds)
    profile = svc.users().getProfile(userId="me").execute()
    row.google_account_email = profile.get("emailAddress")

    db.commit()
    db.refresh(row)
    return row


def delete_gmail_connection(db: Session, user_id: uuid.UUID) -> bool:
    row = db.query(GmailCredential).filter(GmailCredential.user_id == user_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def get_gmail_credentials(db: Session, user_id: uuid.UUID) -> Credentials | None:
    row = db.query(GmailCredential).filter(GmailCredential.user_id == user_id).first()
    if not row:
        return None
    scopes = (row.scopes.split(",") if row.scopes else None) or GMAIL_SCOPES
    creds = Credentials(
        token=row.access_token,
        refresh_token=row.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=scopes,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        row.access_token = creds.token
        row.token_expiry = creds.expiry
        db.commit()
    return creds


def require_user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as e:
        raise ValueError("user_id must be a UUID") from e
