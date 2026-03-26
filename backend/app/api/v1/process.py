"""Message processing endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.graph_service import GraphService

router = APIRouter()


class ProcessMessageRequest(BaseModel):
    """Request model for message processing."""

    message: str
    user_id: str = Field(..., description="users.id (UUID string)")


class ProcessMessageResponse(BaseModel):
    """Response model for message processing."""
    thread_id: str
    status: str
    state: dict = None
    error: str = None


@router.post("/process", response_model=ProcessMessageResponse)
async def process_message(request: ProcessMessageRequest):
    """
    Process a message through the workflow.
    
    Args:
        request: Message processing request
        
    Returns:
        Thread ID and processing status
    """
    try:
        result = GraphService.process_message(
            user_id=request.user_id,
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
