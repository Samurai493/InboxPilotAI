"""Gmail integration: per-user OAuth (users.id UUID) and API calls."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.gmail_credential import GmailCredential
from app.services.gmail_oauth import (
    complete_oauth,
    create_authorization_url,
    delete_gmail_connection,
    get_gmail_credentials,
    require_user_uuid,
    sign_gmail_oauth_binding,
    verify_gmail_oauth_binding,
)
from app.services.gmail_service import GmailService
from app.models.user import User
from app.services.auth_service import get_current_user, require_user_context

router = APIRouter()


class GmailMessageResponse(BaseModel):
    """Response model for Gmail message."""

    id: str
    subject: str
    from_email: str
    date: str
    body: str
    snippet: str


class GmailAuthorizeResponse(BaseModel):
    authorization_url: str


class GmailStatusResponse(BaseModel):
    connected: bool
    google_account_email: str | None = None


class GmailDraftRequest(BaseModel):
    to: str
    subject: str
    body: str


class GmailMessagesPageResponse(BaseModel):
    messages: list[GmailMessageResponse]
    next_page_token: str | None = None


def _user_uuid_param(user_id: str):
    try:
        return require_user_uuid(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be a UUID")


def _credentials_or_404(db: Session, user_id: str):
    uid = _user_uuid_param(user_id)
    creds = get_gmail_credentials(db, uid)
    if not creds:
        raise HTTPException(
            status_code=404,
            detail="Gmail not connected for this user; complete OAuth first",
        )
    return creds


@router.get("/gmail/oauth/authorize", response_model=GmailAuthorizeResponse)
async def gmail_oauth_authorize(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start OAuth: returns Google authorization URL. user_id must be users.id (UUID)."""
    uid = _user_uuid_param(require_user_context(current_user, user_id))
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        url = create_authorization_url(uid)
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Gmail OAuth is not configured or temporarily unavailable.",
        )
    secure = settings.ENVIRONMENT.lower() == "production"
    binding = sign_gmail_oauth_binding(uid)
    resp = JSONResponse(content={"authorization_url": url})
    resp.set_cookie(
        key=settings.GMAIL_OAUTH_BINDING_COOKIE_NAME,
        value=binding,
        max_age=900,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/gmail/oauth/callback")
async def gmail_oauth_callback(request: Request, db: Session = Depends(get_db)):
    """OAuth redirect target: exchanges code and stores tokens for the user UUID in state."""
    url = str(request.url)
    raw_cookie = request.cookies.get(settings.GMAIL_OAUTH_BINDING_COOKIE_NAME)
    binding_uid = None
    if raw_cookie:
        try:
            binding_uid = verify_gmail_oauth_binding(raw_cookie)
        except ValueError:
            binding_uid = None
    try:
        complete_oauth(db, url, cookie_binding_user_id=binding_uid)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Gmail connection failed. Start the connection again from the app.",
        )
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Gmail OAuth is temporarily unavailable. Try again later.",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Gmail connection failed due to a server error. Try again later.",
        )
    # Google hits this URL in the browser as part of the OAuth redirect flow.
    # Redirect back to the frontend so it can call /gmail/status and load messages.
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3002")
    response = RedirectResponse(url=f"{frontend_url}/?gmail_connected=1")
    secure = settings.ENVIRONMENT.lower() == "production"
    response.delete_cookie(
        settings.GMAIL_OAUTH_BINDING_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/gmail/status/{user_id}", response_model=GmailStatusResponse)
async def gmail_status(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Whether Gmail OAuth is stored for this user (authenticated, self only)."""
    uid = _user_uuid_param(require_user_context(current_user, user_id))

    row = db.query(GmailCredential).filter(GmailCredential.user_id == uid).first()
    if not row:
        return GmailStatusResponse(connected=False)
    return GmailStatusResponse(connected=True, google_account_email=row.google_account_email)


@router.get("/gmail/status/me", response_model=GmailStatusResponse)
async def gmail_status_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Whether Gmail OAuth is stored for the authenticated user."""
    uid = _user_uuid_param(str(current_user.id))
    row = db.query(GmailCredential).filter(GmailCredential.user_id == uid).first()
    if not row:
        return GmailStatusResponse(connected=False)
    return GmailStatusResponse(connected=True, google_account_email=row.google_account_email)


@router.delete("/gmail/connection/{user_id}")
async def gmail_disconnect(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove stored Gmail tokens for this user (authenticated, self only)."""
    uid = _user_uuid_param(require_user_context(current_user, user_id))
    if not delete_gmail_connection(db, uid):
        raise HTTPException(status_code=404, detail="Gmail not connected")
    return {"status": "disconnected", "user_id": str(uid)}


@router.get("/gmail/messages", response_model=list[GmailMessageResponse])
async def list_gmail_messages(
    user_id: str | None = None,
    max_results: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inbox messages for the connected Gmail account."""
    resolved = require_user_context(current_user, user_id)
    creds = _credentials_or_404(db, resolved)
    try:
        svc = GmailService(credentials=creds)
        rows = svc.list_message_summaries(max_results=max_results)
        return [GmailMessageResponse(**r) for r in rows]
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Gmail request failed. Try again later.",
        )


@router.get("/gmail/messages/page", response_model=GmailMessagesPageResponse)
async def list_gmail_messages_page(
    user_id: str | None = None,
    max_results: int = 50,
    page_token: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List one inbox page and a token for loading the next page."""
    resolved = require_user_context(current_user, user_id)
    creds = _credentials_or_404(db, resolved)
    try:
        svc = GmailService(credentials=creds)
        page = svc.list_message_summaries_page(max_results=max_results, page_token=page_token)
        return GmailMessagesPageResponse(
            messages=[GmailMessageResponse(**r) for r in page.get("messages", [])],
            next_page_token=page.get("next_page_token"),
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Gmail request failed. Try again later.",
        )


@router.get("/gmail/messages/{message_id}", response_model=GmailMessageResponse)
async def get_gmail_message(
    message_id: str,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get one message by Gmail id."""
    resolved = require_user_context(current_user, user_id)
    creds = _credentials_or_404(db, resolved)
    try:
        svc = GmailService(credentials=creds)
        raw = svc.get_message(message_id)
        return GmailMessageResponse(
            id=raw["id"],
            subject=raw["subject"],
            from_email=raw["from"],
            date=raw["date"],
            body=raw["body"],
            snippet=raw["snippet"],
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Gmail request failed. Try again later.",
        )


@router.post("/gmail/drafts")
async def create_gmail_draft(
    payload: GmailDraftRequest,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Gmail draft for the connected account."""
    resolved = require_user_context(current_user, user_id)
    creds = _credentials_or_404(db, resolved)
    try:
        svc = GmailService(credentials=creds)
        return svc.create_draft(payload.to, payload.subject, payload.body)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Gmail request failed. Try again later.",
        )
