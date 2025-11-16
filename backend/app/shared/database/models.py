"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Video(Base):
    """Video metadata."""
    __tablename__ = "videos"
    
    id = Column(String, primary_key=True)
    chapter = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    duration = Column(Integer)  # in seconds
    transcript_path = Column(String)  # path to transcript JSON file
    created_at = Column(DateTime, default=datetime.utcnow)


class Chunk(Base):
    """Embedded chunks with timestamps."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    start_time = Column(Integer, nullable=False)  # in seconds
    end_time = Column(Integer, nullable=False)  # in seconds
    text = Column(Text, nullable=False)  # original chunk text
    contextualized_text = Column(Text)  # contextualized chunk text (for BM25 and embeddings)
    qdrant_id = Column(String, nullable=False)  # ID in Qdrant collection
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
    """Chat session for tracking conversations."""
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, default="default_user")  # For future multi-user support
    task_type = Column(String, nullable=False)  # "text_summary", "qa", "video_summary", "quiz"
    title = Column(String)  # Auto-generated from first query
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual messages in a chat session."""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)  # User query or LLM response
    sources = Column(JSON)  # List of source references with timestamps (for assistant messages)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")


class Quiz(Base):
    """Quiz generation metadata."""
    __tablename__ = "quizzes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, default="default_user")
    topic = Column(String)  # Optional topic/query
    chapters = Column(JSON)  # Array of chapter filters
    question_type = Column(String, nullable=False)  # mcq, open_ended, mixed
    num_questions = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to questions
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    """Individual quiz questions."""
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_index = Column(Integer, nullable=False)  # Order in quiz (0, 1, 2...)
    question = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)  # mcq or open_ended

    # MCQ fields
    options = Column(JSON)  # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer = Column(String)  # "A", "B", "C", or "D"

    # Open-ended fields
    reference_answer = Column(Text)  # Reference answer for open-ended
    key_points = Column(JSON)  # Array of key points for open-ended

    # Common fields
    explanation = Column(Text)
    source_index = Column(Integer)
    video_id = Column(String)
    video_title = Column(String)
    video_url = Column(String)
    timestamp = Column(Integer)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to quiz
    quiz = relationship("Quiz", back_populates="questions")
    # Relationship to attempts
    attempts = relationship("QuizAttempt", back_populates="question", cascade="all, delete-orphan")


class QuizAttempt(Base):
    """User answers and validation results."""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    user_answer = Column(Text, nullable=False)

    # MCQ validation
    is_correct = Column(Boolean)  # For MCQ

    # Open-ended validation
    llm_score = Column(Integer)  # 0-100 for open-ended
    llm_feedback = Column(JSON)  # Full LLM feedback (score, feedback, covered_points, missing_points)

    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to question
    question = relationship("QuizQuestion", back_populates="attempts")


class VideoSummary(Base):
    """Pre-computed video summaries."""
    __tablename__ = "video_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    sources = Column(JSON)  # List of source references with timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

