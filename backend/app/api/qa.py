"""Q&A API endpoints with SSE streaming."""
import json
from typing import List, Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.qa.service import get_qa_service


router = APIRouter(prefix="/qa", tags=["Q&A"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AskRequest(BaseModel):
    """Request model for Q&A."""
    query: str
    chapters: Optional[List[str]] = None  # e.g., ["Chương 2", "Chương 3"]
    session_id: Optional[str] = None  # For followup questions


class FollowupRequest(BaseModel):
    """Request model for followup questions."""
    query: str
    chapters: Optional[List[str]] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/ask")
async def ask_question(request: AskRequest):
    """
    Answer a question with SSE streaming.
    
    - **query**: User question
    - **chapters**: Optional list of chapters to filter (e.g., ["Chương 2"])
    - **session_id**: Optional session ID for followup, otherwise creates new session
    
    Returns:
        SSE stream with events:
        - data: {"type": "token", "content": "..."}
        - data: {"type": "sources", "sources": [...]}
        - data: {"type": "done", "content": "full response", "sources": [...]}
    """
    service = get_qa_service()
    
    async def event_generator():
        """Generate SSE events."""
        try:
            async for event in service.answer(
                query=request.query,
                chapters=request.chapters,
                session_id=request.session_id
            ):
                # Format as SSE: "data: {json}\n\n"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            # Send error event
            error_event = {
                "type": "error",
                "content": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive"
        }
    )


@router.post("/sessions/{session_id}/followup")
async def followup(session_id: str, request: FollowupRequest):
    """
    Ask followup question in existing session.
    
    - **session_id**: Existing session ID
    - **query**: Followup question
    - **chapters**: Optional chapter filter
    
    Returns:
        SSE stream with same format as /ask
    """
    service = get_qa_service()
    
    async def event_generator():
        """Generate SSE events."""
        try:
            async for event in service.followup(
                session_id=session_id,
                query=request.query,
                chapters=request.chapters
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "content": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# Note: Session management endpoints moved to /api/sessions.py
# This keeps qa.py focused on task-specific endpoints only

