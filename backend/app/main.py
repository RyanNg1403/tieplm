"""FastAPI application entry point."""
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, sessions, qa, text_summary, video_summary, quiz

# Load .env from project root (one level up from backend/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Tieplm AI Assistant", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")  # Universal session management
app.include_router(qa.router, prefix="/api")
app.include_router(text_summary.router, prefix="/api")
app.include_router(video_summary.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Tieplm AI Assistant API", "version": "1.0.0"}

