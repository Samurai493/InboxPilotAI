"""Gmail integration: per-user OAuth (users.id UUID) and API calls."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.gmail_oauth import (
    complete_oauth,
    create_authorization_url,
    delete_gmail_connection,
    get_gmail_credentials,
    require_user_uuid,
)
from app.services.gmail_service import GmailService
from app.models.user import User
from app.models.gmail_credential import GmailCredential

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


class GmailCallbackResponse(BaseModel):
    status: str
    user_id: str
    google_account_email: str | None


class GmailStatusResponse(BaseModel):
    connected: bool
    google_account_email: str | None = None


class GmailDraftRequest(BaseModel):
    to: str
    subject: str
    body: str


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
async def gmail_oauth_authorize(user_id: str, db: Session = Depends(get_db)):
    """Start OAuth: returns Google authorization URL. user_id must be users.id (UUID)."""
    uid = _user_uuid_param(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        url = create_authorization_url(uid)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return GmailAuthorizeResponse(authorization_url=url)


@router.get("/gmail/oauth/callback", response_model=GmailCallbackResponse)
async def gmail_oauth_callback(request: Request, db: Session = Depends(get_db)):
    """OAuth redirect target: exchanges code and stores tokens for the user UUID in state."""
    url = str(request.url)
    try:
        row = complete_oauth(db, url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return GmailCallbackResponse(
        status="connected",
        user_id=str(row.user_id),
        google_account_email=row.google_account_email,
    )


@router.get("/gmail/status/{user_id}", response_model=GmailStatusResponse)
async def gmail_status(user_id: str, db: Session = Depends(get_db)):
    """Whether Gmail OAuth is stored for this user."""
    uid = _user_uuid_param(user_id)

    row = db.query(GmailCredential).filter(GmailCredential.user_id == uid).first()
    if not row:
        return GmailStatusResponse(connected=False)
    return GmailStatusResponse(connected=True, google_account_email=row.google_account_email)


@router.delete("/gmail/connection/{user_id}")
async def gmail_disconnect(user_id: str, db: Session = Depends(get_db)):
    """Remove stored Gmail tokens for this user."""
    uid = _user_uuid_param(user_id)
    if not delete_gmail_connection(db, uid):
        raise HTTPException(status_code=404, detail="Gmail not connected")
    return {"status": "disconnected", "user_id": str(uid)}


@router.get("/gmail/messages", response_model=list[GmailMessageResponse])
async def list_gmail_messages(
    user_id: str,
    max_results: int = 10,
    db: Session = Depends(get_db),
):
    """List inbox messages for the connected Gmail account."""
    creds = _credentials_or_404(db, user_id)
    try:
        svc = GmailService(credentials=creds)
        rows = svc.list_message_summaries(max_results=max_results)
        return [GmailMessageResponse(**r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/gmail/messages/{message_id}", response_model=GmailMessageResponse)
async def get_gmail_message(message_id: str, user_id: str, db: Session = Depends(get_db)):
    """Get one message by Gmail id."""
    creds = _credentials_or_404(db, user_id)
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
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/gmail/drafts")
async def create_gmail_draft(
    user_id: str,
    payload: GmailDraftRequest,
    db: Session = Depends(get_db),
):
    """Create a Gmail draft for the connected account."""
    creds = _credentials_or_404(db, user_id)
    try:
        svc = GmailService(credentials=creds)
        return svc.create_draft(payload.to, payload.subject, payload.body)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
