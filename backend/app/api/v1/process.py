"""Message processing endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter
from app.services.graph_service import GraphService
from app.services.auth_service import get_current_user, require_user_context
from app.services.workflow_thread_service import persist_workflow_thread

router = APIRouter()
logger = logging.getLogger(__name__)


class ProcessMessageRequest(BaseModel):
    """Request model for message processing."""

    message: str
    user_id: str | None = Field(default=None, description="users.id (UUID string); must match Bearer identity")
    gmail_message_id: str | None = Field(
        default=None,
        description="Gmail API message id when processing an inbox email (for durable thread history).",
    )
    use_specialist: bool = Field(
        default=True,
        description="If false, run general draft/extract only (skip domain specialist nodes).",
    )
    llm_provider: str | None = Field(
        default=None,
        description="Override LLM_PROVIDER for this run (openai, anthropic, google_genai).",
    )
    llm_model: str | None = Field(
        default=None,
        description="Override model name for this run when set.",
    )
    openai_api_key: str | None = Field(default=None, description="Optional; else OPENAI_API_KEY from env.")
    anthropic_api_key: str | None = Field(default=None, description="Optional; else ANTHROPIC_API_KEY from env.")
    gemini_api_key: str | None = Field(default=None, description="Optional; else GEMINI_API_KEY from env.")


class ProcessMessageResponse(BaseModel):
    """Response model for message processing."""

    thread_id: str
    status: str
    state: dict | None = None
    error: str | None = None


@router.post("/process", response_model=ProcessMessageResponse)
@limiter.limit("60/minute")
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
        result = GraphService.process_message(
            user_id=user_id,
            raw_message=request_body.message,
            message_id=request_body.gmail_message_id,
            use_specialist=request_body.use_specialist,
            llm_provider=request_body.llm_provider,
            llm_model=request_body.llm_model,
            openai_api_key=request_body.openai_api_key,
            anthropic_api_key=request_body.anthropic_api_key,
            gemini_api_key=request_body.gemini_api_key,
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
        except Exception:
            logger.exception(
                "Failed to persist workflow thread row",
                extra={"thread_id": result.get("thread_id"), "user_id": user_id},
            )

        return ProcessMessageResponse(
            thread_id=result["thread_id"],
            status=result["status"],
            state=result.get("state"),
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unhandled error in /process",
            extra={
                "user_id": request_body.user_id,
                "use_specialist": request_body.use_specialist,
                "llm_provider": request_body.llm_provider,
                "llm_model": request_body.llm_model,
            },
        )
        raise HTTPException(status_code=500, detail=str(e))
