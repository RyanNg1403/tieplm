"""Domain entities."""
from pydantic import BaseModel
from typing import Optional


class VideoMetadata(BaseModel):
    """Video metadata entity."""
    id: str
    url: str
    title: Optional[str]
    chapter: str
    duration: Optional[int]


class TranscriptChunk(BaseModel):
    """Transcript chunk entity."""
    video_id: str
    text: str
    start_time: int
    end_time: int
    embedding: Optional[list[float]] = None

