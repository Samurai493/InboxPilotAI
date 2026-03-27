"""Message processing endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.user import User
from app.services.graph_service import GraphService
from app.services.auth_service import get_current_user_optional, resolve_user_id_or_current

router = APIRouter()
logger = logging.getLogger(__name__)


class ProcessMessageRequest(BaseModel):
    """Request model for message processing."""

    message: str
    user_id: str | None = Field(default=None, description="users.id (UUID string)")
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
async def process_message(
    request: ProcessMessageRequest,
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Process a message through the workflow.
    
    Args:
        request: Message processing request
        
    Returns:
        Thread ID and processing status
    """
    try:
        user_id = resolve_user_id_or_current(request.user_id, current_user)
        result = GraphService.process_message(
            user_id=user_id,
            raw_message=request.message,
            use_specialist=request.use_specialist,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            openai_api_key=request.openai_api_key,
            anthropic_api_key=request.anthropic_api_key,
            gemini_api_key=request.gemini_api_key,
        )
        
        return ProcessMessageResponse(
            thread_id=result["thread_id"],
            status=result["status"],
            state=result.get("state"),
            error=result.get("error")
        )
    except Exception as e:
        logger.exception(
            "Unhandled error in /process",
            extra={
                "user_id": request.user_id,
                "use_specialist": request.use_specialist,
                "llm_provider": request.llm_provider,
                "llm_model": request.llm_model,
            },
        )
        raise HTTPException(status_code=500, detail=str(e))
