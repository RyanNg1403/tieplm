"""
Universal session management API endpoints.

These endpoints handle chat sessions for ALL tasks (text summary, Q&A, etc.)
"""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.shared.database.postgres import get_postgres_client
from app.shared.database.models import ChatSession, ChatMessage

router = APIRouter(tags=["sessions"])

# ============================================================================
# Response Models
# ============================================================================

class SourceReference(BaseModel):
    index: int
    video_id: str
    video_title: str
    video_url: str
    chapter: str
    start_time: int
    end_time: int
    text: str

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: List[SourceReference] | None = None
    created_at: str

class SessionResponse(BaseModel):
    id: str
    title: str
    task_type: str
    created_at: str
    updated_at: str

# ============================================================================
# Endpoints
# ============================================================================

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    user_id: str = "default_user",
    task_type: str | None = None
):
    """
    Get all chat sessions for a user, optionally filtered by task type.
    
    - **user_id**: User ID (default: "default_user")
    - **task_type**: Optional filter by task (text_summary, qa, video_summary, quiz)
    
    Returns:
        List of sessions sorted by most recent
    """
    postgres = get_postgres_client()
    
    try:
        with postgres.session_scope() as session:
            query = session.query(ChatSession).filter_by(user_id=user_id)
            
            if task_type:
                query = query.filter_by(task_type=task_type)
            
            sessions = query.order_by(ChatSession.updated_at.desc()).all()
            
            return [
                SessionResponse(
                    id=s.id,
                    title=s.title or "Untitled",
                    task_type=s.task_type,
                    created_at=s.created_at.isoformat(),
                    updated_at=s.updated_at.isoformat()
                )
                for s in sessions
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(session_id: str):
    """
    Get all messages in a session.
    
    - **session_id**: Session ID
    
    Returns:
        List of messages in chronological order
    """
    postgres = get_postgres_client()
    
    try:
        with postgres.session_scope() as session:
            messages = (
                session.query(ChatMessage)
                .filter_by(session_id=session_id)
                .order_by(ChatMessage.created_at)
                .all()
            )
            
            if not messages:
                # Check if session exists
                chat_session = session.query(ChatSession).filter_by(id=session_id).first()
                if not chat_session:
                    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
                # Session exists but has no messages yet
                return []
            
            return [
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    sources=m.sources,
                    created_at=m.created_at.isoformat()
                )
                for m in messages
            ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and all its messages.
    
    - **session_id**: Session ID to delete
    
    Returns:
        Success message
    """
    postgres = get_postgres_client()
    
    try:
        with postgres.session_scope() as session:
            # Find the session
            chat_session = session.query(ChatSession).filter_by(id=session_id).first()
            
            if not chat_session:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
            # Delete the session (messages will be cascade deleted due to ondelete='CASCADE')
            session.delete(chat_session)
            session.commit()
            
            return {"message": f"Session {session_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

