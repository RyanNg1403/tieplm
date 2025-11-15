"""Quiz generation endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.quiz.service import get_quiz_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


# Request/Response Models
class GenerateQuizRequest(BaseModel):
    """Request model for quiz generation."""
    video_ids: List[str]  # List of video IDs (can be single or multiple)
    query: Optional[str] = None  # Optional specific topic or query
    question_type: str = "mcq"  # "mcq", "open_ended", or "mixed"
    num_questions: Optional[int] = None
    session_id: Optional[str] = None


class ValidateAnswerItem(BaseModel):
    """Single answer for validation."""
    question_index: int
    answer: str  # For MCQ: "A", "B", "C", "D"; For open-ended: full text


class ValidateAnswersRequest(BaseModel):
    """Request model for answer validation."""
    quiz_id: str
    answers: List[ValidateAnswerItem]


@router.post("/generate")
async def generate_quiz(request: GenerateQuizRequest):
    """
    Generate quiz from video(s) with SSE streaming.

    Args:
        request: Quiz generation parameters
            - video_ids: List of video IDs (can be single or multiple)
            - question_type: "mcq", "open_ended", or "mixed"
            - num_questions: Number of questions to generate
            - session_id: Optional session ID to continue existing quiz

    Returns:
        SSE stream with events:
        - data: {"type": "questions", "content": [...]}
        - data: {"type": "sources", "sources": [...]}
        - data: {"type": "done", "content": {...}}
        - data: {"type": "error", "content": "..."}
    """
    service = get_quiz_service()

    async def event_generator():
        """Generate SSE events."""
        try:
            async for event in service.generate_quiz(
                video_ids=request.video_ids,
                query=request.query,
                question_type=request.question_type,
                num_questions=request.num_questions,
                session_id=request.session_id
            ):
                # Format as SSE: "data: {json}\n\n"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            # Send error event
            error_event = {
                "type": "error",
                "content": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive"
        }
    )


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str):
    """
    Retrieve a generated quiz by session ID.

    Args:
        quiz_id: Quiz session ID

    Returns:
        Quiz questions
    """
    try:
        service = get_quiz_service()
        questions = await service._get_quiz_questions(quiz_id)

        if not questions:
            raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found")

        return {
            "quiz_id": quiz_id,
            "questions": questions
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve quiz: {str(e)}")


@router.post("/validate")
async def validate_answers(request: ValidateAnswersRequest):
    """
    Validate user answers for a quiz.

    Args:
        request: Quiz ID and user answers

    Returns:
        Validation results with scores and feedback
    """
    try:
        service = get_quiz_service()

        # Convert Pydantic models to dicts
        answers_dict = [
            {"question_index": ans.question_index, "answer": ans.answer}
            for ans in request.answers
        ]

        result = await service.validate_answers(
            quiz_id=request.quiz_id,
            answers=answers_dict
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate answers: {str(e)}")

