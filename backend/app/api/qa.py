"""Q&A endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask")
async def ask_question():
    """Ask a question about the course content."""
    pass


@router.get("/history")
async def get_chat_history():
    """Get chat history."""
    pass

