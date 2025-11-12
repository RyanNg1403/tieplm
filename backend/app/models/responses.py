"""API response models."""
from pydantic import BaseModel
from typing import List, Optional


class Source(BaseModel):
    """Source information."""
    video_url: str
    video_id: str
    chapter: str
    timestamp: str
    timestamp_seconds: int


class QuestionResponse(BaseModel):
    """Response model for Q&A."""
    answer: str
    sources: List[Source]
    session_id: str


class SummaryResponse(BaseModel):
    """Response model for summarization."""
    summary: str
    sources: List[Source]


class QuizQuestion(BaseModel):
    """Single quiz question."""
    question_id: int
    question: str
    options: Optional[List[str]] = None  # For MCQ
    timestamp: str
    video_url: str


class QuizResponse(BaseModel):
    """Response model for quiz generation."""
    quiz_id: int
    questions: List[QuizQuestion]


class QuizValidationResponse(BaseModel):
    """Response model for quiz validation."""
    score: int
    total: int
    results: dict  # {question_id: {correct: bool, user_answer: str, correct_answer: str}}

