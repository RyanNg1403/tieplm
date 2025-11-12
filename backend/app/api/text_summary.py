"""Text summarization endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/text-summary", tags=["text_summary"])


@router.post("/summarize")
async def summarize_topic():
    """Summarize content related to a specific topic."""
    pass


@router.post("/filter")
async def filter_relevant_videos():
    """Get relevant videos for a topic."""
    pass

