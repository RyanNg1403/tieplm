"""API request models."""
from pydantic import BaseModel
from typing import Optional


class QuestionRequest(BaseModel):
    """Request model for Q&A."""
    question: str
    session_id: Optional[str] = None


class SummarizeTopicRequest(BaseModel):
    """Request model for text summarization."""
    topic: str
    chapter_filter: Optional[str] = None


class SummarizeVideoRequest(BaseModel):
    """Request model for video summarization."""
    video_id: str


class GenerateQuizRequest(BaseModel):
    """Request model for quiz generation."""
    video_id: str
    question_type: str  # "mcq" or "yes_no"
    num_questions: int = 5


class ValidateQuizRequest(BaseModel):
    """Request model for quiz validation."""
    quiz_id: int
    answers: dict  # {question_id: answer}

