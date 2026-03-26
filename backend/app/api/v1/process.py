"""Message processing endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.user import User
from app.services.graph_service import GraphService
from app.services.auth_service import get_current_user_optional, resolve_user_id_or_current

router = APIRouter()


class ProcessMessageRequest(BaseModel):
    """Request model for message processing."""

    message: str
    user_id: str | None = Field(default=None, description="users.id (UUID string)")


class ProcessMessageResponse(BaseModel):
    """Response model for message processing."""
    thread_id: str
    status: str
    state: dict = None
    error: str = None


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
            raw_message=request.message
        )
        
        return ProcessMessageResponse(
            thread_id=result["thread_id"],
            status=result["status"],
            state=result.get("state"),
            error=result.get("error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
