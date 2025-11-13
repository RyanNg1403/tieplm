"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
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


class QuizQuestion(Base):
    """Generated quiz questions."""
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"))
    question = Column(Text, nullable=False)
    question_type = Column(String)  # mcq or yes_no
    options = Column(Text)  # JSON string
    correct_answer = Column(String)
    timestamp = Column(Integer)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)

