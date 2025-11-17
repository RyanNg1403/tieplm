"""
Quiz QAG evaluation service.

Pipeline:
1. Sample a random knowledge chunk from the course transcripts.
2. Use the quiz service prompts/models to generate a short-answer question.
3. Feed the question + same context to the QA service (context-only mode) to get an answer.
4. Compare the generated answer embedding with the reference answer using cosine similarity.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import numpy as np

from dotenv import load_dotenv
from sqlalchemy.sql import func

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables if needed
env_path = PROJECT_ROOT / ".env"
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(dotenv_path=env_path)

from backend.app.core.quiz.service import QuizService, get_quiz_service
from backend.app.core.quiz.prompts import (
    QUIZ_SYSTEM_PROMPT,
    MCQ_GENERATION_PROMPT_TEMPLATE,
    OPEN_ENDED_GENERATION_PROMPT_TEMPLATE,
)
from backend.app.core.qa.service import QAService, get_qa_service
from evaluation.quiz.prompts import (
    QUIZ_EVAL_QA_SYSTEM_PROMPT,
    QUIZ_EVAL_SHORT_ANSWER_PROMPT,
    QUIZ_EVAL_MCQ_PROMPT,
)
from backend.app.shared.embeddings.embedder import OpenAIEmbedder
from backend.app.shared.database.models import Chunk, Video
from backend.app.shared.database.postgres import (
    PostgresClient,
    get_postgres_client,
)


class QuizQAGEvaluator:
    """Evaluation helper that glues QuizService and QAService together."""

    def __init__(
        self,
        quiz_service: Optional[QuizService] = None,
        qa_service: Optional[QAService] = None,
        postgres: Optional[PostgresClient] = None,
    ):
        self.quiz_service = quiz_service or get_quiz_service()
        self.qa_service = qa_service or get_qa_service()
        self.postgres = postgres or get_postgres_client()
        self.embedder = OpenAIEmbedder()

        self.max_generation_tokens = int(os.getenv("EVAL_QUIZ_MAX_TOKENS", "1200"))
        self.max_chunk_chars = int(os.getenv("EVAL_QUIZ_MAX_CHARS", "1800"))

    async def evaluate_case(
        self,
        case_id: str,
        question_type: str = "open_ended",
    ) -> Dict[str, Any]:
        """Run a full evaluation loop for a single case."""
        result: Dict[str, Any] = {
            "case_id": case_id,
            "timestamp": datetime.utcnow().isoformat(),
            "question_type": question_type,
        }

        print("Question type:", question_type)

        try:
            chunk_payload = self._sample_random_chunk()
            result["chunk"] = chunk_payload["metadata"]

            if question_type == "mcq":
                question_payload = await self._generate_mcq_question(chunk_payload)
            else:
                question_payload = await self._generate_open_question(chunk_payload)

            result["question_payload"] = question_payload

            if question_payload.get("error"):
                result["error"] = question_payload["error"]
                return result

            if question_type == "mcq":
                mcq_response = await self._answer_mcq_with_context(
                    question_payload["question"],
                    question_payload.get("options", {}),
                    chunk_payload,
                )
                score = self._score_mcq_answer(
                    predicted=mcq_response,
                    correct=question_payload.get("correct_answer"),
                )
                result.update(
                    {
                        "question": question_payload.get("question"),
                        "options": question_payload.get("options"),
                        "predicted_answer": mcq_response,
                        "correct_answer": question_payload.get("correct_answer"),
                        "score": score,
                        "source_index": question_payload.get("source_index", 1),
                    }
                )
            else:
                qa_answer = await self._answer_with_context(
                    question_payload["question"],
                    chunk_payload,
                )

                reference_answer = question_payload.get("reference_answer", "").strip()
                similarity = self._compute_embedding_similarity(
                    reference_answer,
                    qa_answer,
                )

                result.update(
                    {
                        "question": question_payload.get("question"),
                        "reference_answer": reference_answer,
                        "qa_answer": qa_answer,
                        "key_points": question_payload.get("key_points", []),
                        "embedding_similarity": similarity,
                        "source_index": question_payload.get("source_index", 1),
                    }
                )

            return result

        except Exception as exc:
            result["error"] = str(exc)
            return result

    def _sample_random_chunk(self) -> Dict[str, Any]:
        """Randomly pick a chunk from the database (with video metadata)."""
        with self.postgres.session_scope() as session:
            record = (
                session.query(Chunk, Video)
                .join(Video, Chunk.video_id == Video.id)
                .order_by(func.random())
                .first()
            )

            if not record:
                raise ValueError("No chunks available in database.")

            chunk, video = record

            text = chunk.contextualized_text or ""
            if self.max_chunk_chars and len(text) > self.max_chunk_chars:
                text = text[: self.max_chunk_chars].rstrip() + "..."

            metadata = {
                "chunk_id": chunk.id,
                "video_id": video.id,
                "video_title": video.title,
                "video_url": video.url,
                "chapter": video.chapter,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "text": text,
            }

        return {
            "metadata": metadata,
        }

    async def _generate_open_question(
        self, chunk_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an open-ended quiz question from the supplied chunk."""
        sources = self.quiz_service._format_sources_for_prompt([chunk_payload])
        prompt = OPEN_ENDED_GENERATION_PROMPT_TEMPLATE.format(
            sources=sources,
            num_questions=1,
        )

        response = await self.quiz_service.llm.generate_async(
            prompt=prompt,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            max_tokens=self.max_generation_tokens,
        )

        parsed = self._safe_json_loads(response)
        questions: List[Dict[str, Any]] = parsed.get("questions", [])

        if not questions:
            return {
                "error": "Quiz service did not return any questions.",
                "raw_response": response,
            }

        question = questions[0]
        question["question_type"] = "open_ended"
        question.setdefault("source_index", 1)

        return question

    async def _generate_mcq_question(
        self,
        chunk_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create an MCQ question from the supplied chunk."""
        sources = self.quiz_service._format_sources_for_prompt([chunk_payload])
        prompt = MCQ_GENERATION_PROMPT_TEMPLATE.format(
            sources=sources,
            num_questions=1,
        )

        response = await self.quiz_service.llm.generate_async(
            prompt=prompt,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            max_tokens=self.max_generation_tokens,
        )

        parsed = self._safe_json_loads(response)
        questions: List[Dict[str, Any]] = parsed.get("questions", [])

        if not questions:
            return {
                "error": "Quiz service did not return any MCQ questions.",
                "raw_response": response,
            }

        question = questions[0]
        question["question_type"] = "mcq"
        question.setdefault("source_index", 1)

        return question

    async def _answer_with_context(
        self,
        question: str,
        chunk_payload: Dict[str, Any],
    ) -> str:
        """Call QA service LLM using ONLY the provided context chunk."""
        sources = self.qa_service._format_sources_for_prompt([chunk_payload])
        prompt = QUIZ_EVAL_SHORT_ANSWER_PROMPT.format(
            question=question,
            sources=sources,
        )

        answer = await self.qa_service.llm.generate_async(
            prompt=prompt,
            system_prompt=QUIZ_EVAL_QA_SYSTEM_PROMPT,
            max_tokens=600,
        )

        return answer.strip()

    async def _answer_mcq_with_context(
        self,
        question: str,
        options: Dict[str, str],
        chunk_payload: Dict[str, Any],
    ) -> str:
        """Ask QA service to pick one MCQ option."""
        sources = self.qa_service._format_sources_for_prompt([chunk_payload])
        options_text = "\n".join(
            f"{key}. {value}" for key, value in sorted(options.items())
        )
        prompt = QUIZ_EVAL_MCQ_PROMPT.format(
            question=question,
            options=options_text,
            sources=sources,
        )
        
        answer = await self.qa_service.llm.generate_async(
            prompt=prompt,
            system_prompt=QUIZ_EVAL_QA_SYSTEM_PROMPT,
            max_tokens=50,
        )

        return self._normalize_option(answer)

    def _normalize_option(self, answer: str) -> str:
        """Extract option letter (A/B/C/D/IDK) from model answer."""

        print("Answer: ", answer)

        if not answer:
            return "idk"

        cleaned = answer.strip().upper()

        for letter in ["A", "B", "C", "D"]:
            if cleaned.startswith(letter):
                return letter.lower()

        if "IDK" in cleaned:
            return "idk"

        # fallback to single char if present
        for ch in cleaned:
            if ch in ["A", "B", "C", "D"]:
                return ch.lower()

        return "idk"

    def _score_mcq_answer(self, predicted: str, correct: Optional[str]) -> int:
        """Compare predicted vs correct option."""
        if not correct:
            return 0
        normalized_correct = correct.strip().lower()
        normalized_pred = (predicted or "").strip().lower()
        return 1 if normalized_correct == normalized_pred else 0

    def _safe_json_loads(self, raw: str) -> Dict[str, Any]:
        """Best-effort JSON parsing with fallback trimming."""
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            first_brace = raw.find("{")
            last_brace = raw.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                trimmed = raw[first_brace : last_brace + 1]
                try:
                    return json.loads(trimmed)
                except json.JSONDecodeError:
                    pass
        return {}

    def _compute_embedding_similarity(self, reference: str, candidate: str) -> float:
        """Embed answers and compute cosine similarity."""
        reference = reference.strip()
        candidate = candidate.strip()

        if not reference or not candidate:
            return 0.0

        ref_vec = np.array(self.embedder.embed(reference))
        cand_vec = np.array(self.embedder.embed(candidate))

        ref_norm = np.linalg.norm(ref_vec)
        cand_norm = np.linalg.norm(cand_vec)

        if ref_norm == 0 or cand_norm == 0:
            return 0.0

        similarity = float(np.dot(ref_vec, cand_vec) / (ref_norm * cand_norm))
        return round(similarity, 4)


def get_quiz_qag_evaluator() -> QuizQAGEvaluator:
    """Factory for external callers (mirrors other evaluation services)."""
    return QuizQAGEvaluator()

