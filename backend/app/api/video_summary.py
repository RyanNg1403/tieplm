"""Video summarization endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/video-summary", tags=["video_summary"])


@router.post("/summarize")
async def summarize_video():
    """Summarize a specific video."""
    pass


@router.get("/videos")
async def list_videos():
    """List all available videos."""
    pass

