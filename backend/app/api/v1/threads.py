"""Thread endpoints."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class ThreadStateResponse(BaseModel):
    """Response model for thread state."""
    thread_id: str
    state: dict | None = None
    status: str
    error: str | None = None


@router.get("/threads/{thread_id}", response_model=ThreadStateResponse)
async def get_thread(thread_id: str):
    """
    Get thread state.
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        Thread state and status
    """
    from app.services.graph_service import GraphService
    
    try:
        result = GraphService.get_thread_state(thread_id)
        
        return ThreadStateResponse(
            thread_id=result["thread_id"],
            state=result.get("state"),
            status=result["status"],
            error=result.get("error")
        )
    except Exception as e:
        logger.exception(
            "Unhandled error in GET /api/v1/threads/{thread_id}",
            extra={"thread_id": thread_id},
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str):
    """
    Get thread execution history (checkpoint history).
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        Thread history with checkpoints
    """
    from app.graphs.main_graph import graph
    
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    try:
        # Get state history from checkpointer
        history = []
        state = graph.get_state(config)
        
        if state:
            # Get all checkpoints for this thread
            # This is a simplified version - in production, you'd want to track all checkpoints
            history.append({
                "checkpoint_id": getattr(state, "id", None),
                "values": state.values if hasattr(state, "values") else None,
                "metadata": state.metadata if hasattr(state, "metadata") else None,
                "parent_checkpoint_id": getattr(state, "parent_checkpoint_id", None)
            })
        
        return {
            "thread_id": thread_id,
            "history": history,
            "status": "found" if history else "not_found"
        }
    except Exception as e:
        logger.exception(
            "Unhandled error in GET /api/v1/threads/{thread_id}/history",
            extra={"thread_id": thread_id},
        )
        raise HTTPException(status_code=500, detail=str(e))
