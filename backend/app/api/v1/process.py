"""Message processing endpoints."""

import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter
from app.services.auth_service import get_current_user, require_user_context
from app.services.graph_service import GraphService
from app.services.process_quota import enforce_process_quota
from app.services.user_llm_credentials_service import get_decrypted_keys
from app.services.workflow_thread_service import persist_workflow_thread

router = APIRouter()
logger = logging.getLogger(__name__)


class ProcessMessageRequest(BaseModel):
    """Request model for message processing."""

    message: str
    user_id: Optional[str] = Field(default=None, description="users.id (UUID string); must match Bearer identity")
    gmail_message_id: Optional[str] = Field(
        default=None,
        description="Gmail API message id when processing an inbox email (for durable thread history).",
    )
    use_specialist: bool = Field(
        default=True,
        description="If false, run general draft/extract only (skip domain specialist nodes).",
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description="Override LLM_PROVIDER for this run (openai, anthropic, google_genai).",
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="Override model name for this run when set.",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="Optional when ALLOW_LLM_API_KEYS_IN_REQUEST_BODY=true; otherwise use saved credentials or env.",
    )
    anthropic_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)


class ProcessMessageResponse(BaseModel):
    """Response model for message processing."""

    thread_id: str
    status: str
    state: Optional[dict] = None
    error: Optional[str] = None


def _body_has_llm_api_keys(body: ProcessMessageRequest) -> bool:
    for v in (body.openai_api_key, body.anthropic_api_key, body.gemini_api_key):
        if isinstance(v, str) and v.strip():
            return True
    return False


def _resolve_llm_api_keys_for_process(
    db: Session,
    user_id: str,
    body: ProcessMessageRequest,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Request body keys (if allowed) override DB-stored keys; env fallback happens in ``get_chat_model``."""
    db_keys = get_decrypted_keys(db, user_id)
    if not settings.ALLOW_LLM_API_KEYS_IN_REQUEST_BODY:
        if _body_has_llm_api_keys(body):
            logger.warning(
                "Ignored LLM API keys in POST /process body (ALLOW_LLM_API_KEYS_IN_REQUEST_BODY=false)",
            )
        return (
            db_keys["openai_api_key"],
            db_keys["anthropic_api_key"],
            db_keys["gemini_api_key"],
        )

    def pick(body_val: Optional[str], stored: Optional[str]) -> Optional[str]:
        if isinstance(body_val, str) and body_val.strip():
            return body_val.strip()
        return stored

    return (
        pick(body.openai_api_key, db_keys["openai_api_key"]),
        pick(body.anthropic_api_key, db_keys["anthropic_api_key"]),
        pick(body.gemini_api_key, db_keys["gemini_api_key"]),
    )


@router.post("/process", response_model=ProcessMessageResponse)
@limiter.limit("30/minute")
async def process_message(
    request_body: ProcessMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process a message through the workflow.
    """
    try:
        user_id = require_user_context(current_user, request_body.user_id)
        enforce_process_quota(user_id, settings.PROCESS_QUOTA_PER_HOUR)
        okey, akey, gkey = _resolve_llm_api_keys_for_process(db, user_id, request_body)
        result = GraphService.process_message(
            user_id=user_id,
            raw_message=request_body.message,
            message_id=request_body.gmail_message_id,
            use_specialist=request_body.use_specialist,
            llm_provider=request_body.llm_provider,
            llm_model=request_body.llm_model,
            openai_api_key=okey,
            anthropic_api_key=akey,
            gemini_api_key=gkey,
        )

        try:
            persist_workflow_thread(
                db,
                user_id=user_id,
                thread_id=result["thread_id"],
                status=result["status"],
                state=result.get("state"),
                trace_id=result.get("trace_id"),
                gmail_message_id=request_body.gmail_message_id,
                error_message=result.get("error"),
            )
            logger.info(
                "workflow_thread_persisted",
                extra={"user_id": user_id, "thread_id": result["thread_id"]},
            )
        except Exception:
            logger.exception(
                "Failed to persist workflow thread row",
                extra={"thread_id": result.get("thread_id"), "user_id": user_id},
            )

        state = result.get("state")
        usage = state.get("llm_token_usage") if isinstance(state, dict) else None
        logger.info(
            "workflow_process_finished",
            extra={
                "user_id": user_id,
                "thread_id": result.get("thread_id"),
                "status": result.get("status"),
                "llm_token_usage": usage,
            },
        )

        return ProcessMessageResponse(
            thread_id=result["thread_id"],
            status=result["status"],
            state=result.get("state"),
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Unhandled error in /process",
            extra={
                "user_id": request_body.user_id,
                "use_specialist": request_body.use_specialist,
                "llm_provider": request_body.llm_provider,
                "llm_model": request_body.llm_model,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Workflow processing failed. Try again later.",
        )
