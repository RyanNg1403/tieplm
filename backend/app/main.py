"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, qa, text_summary, video_summary, quiz

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
app.include_router(qa.router, prefix="/api")
app.include_router(text_summary.router, prefix="/api")
app.include_router(video_summary.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Tieplm AI Assistant API", "version": "1.0.0"}

