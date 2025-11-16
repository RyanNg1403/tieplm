"""Quiz generation endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.quiz.service import get_quiz_service
from ..shared.database.postgres import get_postgres_client
from ..shared.database.models import Quiz as QuizModel

router = APIRouter(prefix="/quiz", tags=["quiz"])


# Request/Response Models
class GenerateQuizRequest(BaseModel):
    """Request model for quiz generation."""
    video_ids: Optional[List[str]] = None  # List of video IDs (optional)
    query: Optional[str] = None  # Optional specific topic or query
    chapters: Optional[List[str]] = None  # Chapter filters
    question_type: str = "mcq"  # "mcq", "open_ended", or "mixed"
    num_questions: Optional[int] = None


class ValidateAnswerItem(BaseModel):
    """Single answer for validation."""
    question_index: int
    answer: str  # For MCQ: "A", "B", "C", "D"; For open-ended: full text


class ValidateAnswersRequest(BaseModel):
    """Request model for answer validation."""
    quiz_id: str
    answers: List[ValidateAnswerItem]


class QuizHistoryResponse(BaseModel):
    """Response model for quiz history."""
    id: str
    topic: Optional[str]
    chapters: Optional[List[str]]
    question_type: str
    num_questions: int
    created_at: str


@router.get("/history", response_model=List[QuizHistoryResponse])
async def get_quiz_history(user_id: str = "default_user"):
    """
    Get quiz history for a user.

    Args:
        user_id: User ID (default: "default_user")

    Returns:
        List of quizzes sorted by most recent
    """
    postgres = get_postgres_client()

    try:
        with postgres.session_scope() as session:
            quizzes = (
                session.query(QuizModel)
                .filter_by(user_id=user_id)
                .order_by(QuizModel.created_at.desc())
                .all()
            )

            return [
                QuizHistoryResponse(
                    id=q.id,
                    topic=q.topic,
                    chapters=q.chapters,
                    question_type=q.question_type,
                    num_questions=q.num_questions,
                    created_at=q.created_at.isoformat()
                )
                for q in quizzes
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quiz history: {str(e)}")


@router.post("/generate")
async def generate_quiz(request: GenerateQuizRequest):
    """
    Generate quiz from video(s)/chapters with SSE streaming.

    Args:
        request: Quiz generation parameters
            - video_ids: List of video IDs (optional)
            - query: Optional topic/query
            - chapters: Chapter filters
            - question_type: "mcq", "open_ended", or "mixed"
            - num_questions: Number of questions to generate

    Returns:
        SSE stream with events:
        - data: {"type": "progress", "progress": 0-100, "quiz_id": "..."}
        - data: {"type": "done", "content": {...}, "quiz_id": "..."}
        - data: {"type": "error", "content": "..."}
    """
    service = get_quiz_service()

    async def event_generator():
        """Generate SSE events."""
        try:
            async for event in service.generate_quiz(
                video_ids=request.video_ids,
                query=request.query,
                chapters=request.chapters,
                question_type=request.question_type,
                num_questions=request.num_questions
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


@router.delete("/{quiz_id}")
async def delete_quiz(quiz_id: str):
    """
    Delete a quiz and all its questions and attempts.

    Args:
        quiz_id: Quiz ID to delete

    Returns:
        Success message
    """
    postgres = get_postgres_client()

    try:
        with postgres.session_scope() as session:
            # Find the quiz
            quiz = session.query(QuizModel).filter_by(id=quiz_id).first()

            if not quiz:
                raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found")

            # Delete the quiz (questions and attempts will be cascade deleted)
            session.delete(quiz)
            session.commit()

            return {"message": f"Quiz {quiz_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete quiz: {str(e)}")


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str):
    """
    Retrieve a generated quiz by quiz ID.

    Args:
        quiz_id: Quiz ID

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


@router.get("/{quiz_id}/attempts")
async def get_quiz_attempts(quiz_id: str):
    """
    Get previous attempts (submitted answers and validation results) for a quiz.

    Args:
        quiz_id: Quiz ID

    Returns:
        List of attempts with answers and validation results
    """
    from ..shared.database.models import QuizAttempt
    postgres = get_postgres_client()

    try:
        with postgres.session_scope() as session:
            attempts = (
                session.query(QuizAttempt)
                .filter_by(quiz_id=quiz_id)
                .all()
            )

            return [
                {
                    "question_id": attempt.question_id,
                    "user_answer": attempt.user_answer,
                    "is_correct": attempt.is_correct,
                    "llm_score": attempt.llm_score,
                    "llm_feedback": attempt.llm_feedback,
                    "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                }
                for attempt in attempts
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quiz attempts: {str(e)}")


@router.post("/validate")
async def validate_answers(request: ValidateAnswersRequest):
    """
    Validate user answers for a quiz with incremental streaming.

    Args:
        request: Quiz ID and user answers

    Returns:
        SSE stream with validation results:
        - data: {"type": "validation", "result": {...}}  # MCQ results (instant)
        - data: {"type": "validation", "result": {...}}  # Open-ended results (as they complete)
        - data: {"type": "done", "total_questions": N, "quiz_id": "..."}
    """
    try:
        service = get_quiz_service()

        # Convert Pydantic models to dicts
        answers_dict = [
            {"question_index": ans.question_index, "answer": ans.answer}
            for ans in request.answers
        ]

        async def event_generator():
            """Generate SSE events for validation results."""
            try:
                async for event in service.validate_answers(
                    quiz_id=request.quiz_id,
                    answers=answers_dict
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
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
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate answers: {str(e)}")
