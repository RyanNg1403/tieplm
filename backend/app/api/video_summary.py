"""Video summarization endpoints."""
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.video_summary.service import get_video_summary_service
from ..shared.database.postgres import get_postgres_client
from ..shared.database.models import Video, VideoSummary


router = APIRouter(prefix="/video-summary", tags=["video_summary"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SummarizeVideoRequest(BaseModel):
    """Request model for video summarization."""
    video_id: str
    regenerate: bool = False  # If True, regenerate summary even if it exists


class VideoInfo(BaseModel):
    """Response model for video information."""
    id: str
    chapter: str
    title: str
    url: str
    duration: int


class VideoSummaryResponse(BaseModel):
    """Response model for video summary."""
    video_id: str
    summary: str
    sources: List[Dict[str, Any]]
    has_summary: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/summarize", response_class=StreamingResponse)
async def summarize_video(request: SummarizeVideoRequest):
    """
    Summarize a specific video using pre-computed summaries or RAG pipeline.
    Returns SSE stream with tokens and sources.

    Args:
        request: Contains video_id and regenerate flag

    Returns:
        SSE stream with events:
        - {"type": "token", "content": str}
        - {"type": "sources", "sources": list}
        - {"type": "done", "content": str, "sources": list}
    """
    service = get_video_summary_service()

    async def generate():
        try:
            async for event in service.summarize_video(
                video_id=request.video_id,
                regenerate=request.regenerate
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            print(f"❌ Error in video summarization: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.get("/videos", response_model=List[VideoInfo])
async def list_videos():
    """
    List all available videos in the database.
    
    Returns:
        List of VideoInfo objects
    """
    try:
        postgres = get_postgres_client()

        with postgres.session_scope() as session:
            # Order videos by chapter then title for a stable, human-friendly listing
            videos = session.query(Video).order_by(Video.chapter, Video.title).all()

            if not videos:
                return []

            return [
                VideoInfo(
                    id=video.id,
                    chapter=video.chapter,
                    title=video.title,
                    url=video.url,
                    duration=video.duration or 0
                )
                for video in videos
            ]
    except Exception as e:
        print(f"❌ Error listing videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{video_id}", response_model=VideoInfo)
async def get_video_info(video_id: str):
    """
    Get information about a specific video.

    Args:
        video_id: ID of the video

    Returns:
        VideoInfo object
    """
    try:
        postgres = get_postgres_client()

        with postgres.session_scope() as session:
            # Try exact match first
            video = session.query(Video).filter(Video.id == video_id).first()

            # If not found, attempt to match by YouTube id suffix (ids appear like "Chương 7_<ytid>")
            if not video and '_' in video_id:
                # try suffix match if caller passed full id with underscore or passed only youtube id
                # Example stored id: "Chương 7_KjPEqyGCtUs". Caller may send "Chương 7_KjPEqyGCtUs" or "KjPEqyGCtUs".
                suffix = video_id.split('_')[-1]
                video = session.query(Video).filter(Video.id.endswith(f"_{suffix}")).first()

            # As a last resort, try a case-sensitive partial match (LIKE) to be forgiving about encoding issues
            if not video:
                like_match = f"%{video_id}%"
                video = session.query(Video).filter(Video.id.like(like_match)).first()

            if not video:
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

            return VideoInfo(
                id=video.id,
                chapter=video.chapter,
                title=video.title,
                url=video.url,
                duration=video.duration or 0
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting video info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{video_id}", response_model=VideoSummaryResponse)
async def get_video_summary(video_id: str):
    """
    Get existing pre-computed summary for a video (non-streaming).

    Args:
        video_id: ID of the video

    Returns:
        VideoSummaryResponse with summary and sources, or empty if not exists
    """
    try:
        postgres = get_postgres_client()

        with postgres.session_scope() as session:
            # Check if video exists
            video = session.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

            # Get existing summary
            summary_obj = session.query(VideoSummary).filter(
                VideoSummary.video_id == video_id
            ).first()

            if summary_obj:
                # Return existing summary
                return VideoSummaryResponse(
                    video_id=video_id,
                    summary=summary_obj.summary,
                    sources=summary_obj.sources or [],
                    has_summary=True,
                    created_at=summary_obj.created_at.isoformat() if summary_obj.created_at else None,
                    updated_at=summary_obj.updated_at.isoformat() if summary_obj.updated_at else None
                )
            else:
                # No summary exists yet
                return VideoSummaryResponse(
                    video_id=video_id,
                    summary="",
                    sources=[],
                    has_summary=False
                )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting video summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

