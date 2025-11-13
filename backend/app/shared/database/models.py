"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

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


class ChatHistory(Base):
    """Chat history."""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String)
    user_message = Column(Text)
    assistant_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


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

