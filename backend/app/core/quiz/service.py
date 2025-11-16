"""Quiz generation service - orchestration logic."""
import os
import json
import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from ...shared.rag.reranker import LocalReranker, get_local_reranker
from ...shared.rag.retriever import RAGRetriever, get_rag_retriever

from ...shared.llm.client import LLMClient, get_llm_client
from ...shared.database.postgres import PostgresClient, get_postgres_client
from ...shared.database.models import Quiz, QuizQuestion, QuizAttempt

from .prompts import (
    QUIZ_SYSTEM_PROMPT,
    MCQ_GENERATION_PROMPT_TEMPLATE,
    OPEN_ENDED_GENERATION_PROMPT_TEMPLATE,
    MIXED_GENERATION_PROMPT_TEMPLATE,
    VALIDATE_ANSWER_PROMPT_TEMPLATE
)


class QuizService:
    """
    Service for quiz generation from video transcripts.

    Pipeline:
    1. Retrieve relevant chunks using RAG
    2. Generate questions using LLM (MCQ or open-ended)
    3. Parse and validate LLM response
    4. Save questions to quizzes and quiz_questions tables
    5. Return formatted quiz
    """

    def __init__(
        self,
        retriever: RAGRetriever = None,
        reranker: LocalReranker = None,
        llm_client: LLMClient = None,
        postgres: PostgresClient = None
    ):
        self.retriever = retriever or get_rag_retriever()
        self.reranker = reranker or get_local_reranker()
        self.llm = llm_client or get_llm_client()
        self.postgres = postgres or get_postgres_client()

        # Load configuration
        self.default_num_questions = int(os.getenv("QUIZ_DEFAULT_NUM_QUESTIONS", "5"))
        self.max_transcript_length = int(os.getenv("QUIZ_MAX_TRANSCRIPT_LENGTH", "8000"))

        self.enable_reranking = os.getenv("ENABLE_RERANKING", "true").lower() == "true"
        self.retrieval_top_k = int(os.getenv("RETRIEVAL_INITIAL_K", "150"))
        self.final_top_k = int(os.getenv("FINAL_CONTEXT_CHUNKS", "10"))

    async def generate_quiz(
        self,
        video_ids: Optional[List[str]] = None,
        query: Optional[str] = None,
        chapters: Optional[List[str]] = None,
        question_type: str = "mcq",
        num_questions: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate quiz questions from videos/chapters.

        Args:
            video_ids: List of video IDs to generate quiz from
            query: Optional topic/query
            chapters: List of chapters to filter by
            question_type: Type of questions - "mcq", "open_ended", or "mixed"
            num_questions: Number of questions to generate (default from env)

        Yields:
            SSE events with progress, questions, and quiz_id
        """
        num_questions = num_questions or self.default_num_questions

        # Handle video_ids - default to empty list if None
        if video_ids is None:
            video_ids = []

        source_identifier = f"{len(video_ids)} video(s)" if len(video_ids) > 1 else (video_ids[0] if video_ids else "all videos")

        # Step 0: Create quiz record BEFORE generation
        quiz_id = await self._create_quiz(
            topic=query,
            chapters=chapters,
            question_type=question_type,
            num_questions=num_questions
        )

        # Step 1: Retrieve relevant chunks
        if query:
            print(f"📚 Retrieving chunks for query: {query[:50]}...")
            retrieved_chunks = await self.retriever.retrieve(
                query=query,
                top_k=self.retrieval_top_k,
                chapter_filter=chapters,
                use_bm25=True
            )
            print(f"✅ Retrieved {len(retrieved_chunks)} chunks")

            if not retrieved_chunks:
                yield {
                    "type": "error",
                    "content": "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
                }
                return
        else:
            # If no query, use a generic query with chapter filtering
            # For quiz generation, we want broad coverage of the chapters
            generic_query = "deep learning neural networks machine learning"
            print(f"📚 Retrieving chunks from chapters: {chapters}...")
            retrieved_chunks = await self.retriever.retrieve(
                query=generic_query,
                top_k=self.retrieval_top_k,
                chapter_filter=chapters,
                use_bm25=True
            )
            print(f"✅ Retrieved {len(retrieved_chunks)} chunks")

            if not retrieved_chunks:
                yield {
                    "type": "error",
                    "content": "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
                }
                return

        # Step 2: Rerank (if enabled)
        if self.enable_reranking and len(retrieved_chunks) > self.final_top_k:
            print(f"🔄 Reranking {len(retrieved_chunks)} chunks...")
            reranked_chunks = self.reranker.rerank(
                query=query if query else source_identifier,
                results=retrieved_chunks,
                top_k=self.final_top_k
            )
            print(f"✅ Reranked to top-{len(reranked_chunks)} chunks")
        else:
            reranked_chunks = retrieved_chunks[:self.final_top_k]

        # Step 3: Format sources for prompt
        sources_for_prompt = self._format_sources_for_prompt(reranked_chunks)

        # Step 4: Generate questions with LLM
        print(f"🤖 Generating {num_questions} {question_type} questions...")

        # Choose prompt based on question type
        match question_type:
            case "mcq":
                prompt = MCQ_GENERATION_PROMPT_TEMPLATE.format(
                    sources=sources_for_prompt,
                    num_questions=num_questions
                )
            case "open_ended":
                prompt = OPEN_ENDED_GENERATION_PROMPT_TEMPLATE.format(
                    sources=sources_for_prompt,
                    num_questions=num_questions
                )
            case "mixed":
                prompt = MIXED_GENERATION_PROMPT_TEMPLATE.format(
                    sources=sources_for_prompt,
                    num_mcq=num_questions // 2,
                    num_open=num_questions - num_questions // 2
                )
            case _:
                raise ValueError(f"Invalid question type: {question_type}")

        # Stream tokens from LLM and yield progress
        print("🤖 Generating questions with LLM...")
        accumulated_response = ""
        # Estimate total length: each question ~600-800 chars, plus JSON structure overhead
        base_estimate = num_questions * 700
        estimated_total_length = base_estimate

        async for token in self.llm.stream(
            prompt=prompt,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            max_tokens=3000
        ):
            accumulated_response += token
            current_length = len(accumulated_response)

            # Dynamically adjust estimate if we exceed it
            if current_length > estimated_total_length:
                # Increase estimate by 20% to accommodate longer responses
                estimated_total_length = int(current_length * 1.2)

            # Calculate progress based on actual JSON response length
            # Cap at 95% until we're actually done parsing
            progress = min(95, int((current_length / estimated_total_length) * 100))

            yield {
                "type": "progress",
                "progress": progress,
                "quiz_id": quiz_id
            }

        print("LLM response received for quiz generation.")
        print(f"Response: {accumulated_response[:500]}...")  # Truncate for logging

        # Parse JSON response
        try:
            parsed = json.loads(accumulated_response)

            # Handle mixed question type format
            if question_type == "mixed":
                mcq_questions = parsed.get("mcq_questions", [])
                open_ended_questions = parsed.get("open_ended_questions", [])
                all_questions = mcq_questions + open_ended_questions
                # Add type field to each question
                for q in mcq_questions:
                    q["question_type"] = "mcq"
                    q["type"] = "mcq"
                for q in open_ended_questions:
                    q["question_type"] = "open_ended"
                    q["type"] = "open_ended"
            else:
                all_questions = parsed.get("questions", [])
                # Add type field
                for q in all_questions:
                    q["question_type"] = question_type
                    q["type"] = question_type

            print(f"Generated {len(all_questions)} questions")

            # Step 5: Enrich questions with video info from chunks
            all_questions = self._enrich_questions_with_video_info(
                questions=all_questions,
                chunks=reranked_chunks
            )

            # Yield final progress
            yield {
                "type": "progress",
                "progress": 100,
                "quiz_id": quiz_id
            }

            # Step 6: Save questions to database
            await self._save_questions(
                quiz_id=quiz_id,
                questions=all_questions
            )

            # Yield final response with questions
            yield {
                "type": "done",
                "content": json.dumps(all_questions, ensure_ascii=False),
                "quiz_id": quiz_id
            }

            print(f"✅ Generated {len(all_questions)} questions for quiz {quiz_id}")

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response: {e}")
            print(f"Response: {accumulated_response[:200]}...")
            yield {
                "type": "error",
                "content": "Failed to generate valid quiz questions"
            }

    async def validate_answers(
        self,
        quiz_id: str,
        answers: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Validate user answers with parallel processing and incremental streaming.

        Args:
            quiz_id: Quiz ID
            answers: List of user answers:
                {"question_index": 0, "answer": "A"}

        Yields:
            Validation results incrementally as they complete
        """
        print(f"📝 Validating answers for quiz {quiz_id}...")

        # Step 1: Retrieve quiz questions
        questions = await self._get_quiz_questions(quiz_id)

        if not questions:
            yield {
                "type": "error",
                "content": f"No questions found for quiz {quiz_id}"
            }
            return

        # Step 2: Separate MCQ and open-ended questions
        mcq_validations = []
        open_ended_validations = []

        for answer_data in answers:
            q_idx = answer_data["question_index"]
            user_answer = answer_data["answer"]

            if q_idx >= len(questions):
                continue

            question = questions[q_idx]

            if question["question_type"] == "mcq":
                mcq_validations.append((q_idx, question, user_answer))
            elif question["question_type"] == "open_ended":
                open_ended_validations.append((q_idx, question, user_answer))

        # Step 3: Process MCQ validations instantly
        print(f"✅ Validating {len(mcq_validations)} MCQ questions...")
        for q_idx, question, user_answer in mcq_validations:
            is_correct = user_answer == question["correct_answer"]
            result = {
                "question_index": q_idx,
                "question_type": "mcq",
                "question": question["question"],
                "user_answer": user_answer,
                "correct_answer": question["correct_answer"],
                "is_correct": is_correct,
                "explanation": question.get("explanation", ""),
                "timestamp": question.get("timestamp"),
                "video_id": question.get("video_id"),
                "video_title": question.get("video_title"),
                "video_url": question.get("video_url"),
            }

            # Save to database
            await self._save_attempt(
                quiz_id=quiz_id,
                question_id=question["id"],
                user_answer=user_answer,
                is_correct=is_correct
            )

            # Stream result immediately
            yield {
                "type": "validation",
                "result": result
            }

        # Step 4: Process open-ended validations in parallel
        if open_ended_validations:
            print(f"🤖 Validating {len(open_ended_validations)} open-ended questions in parallel...")

            # Create tasks for parallel execution
            tasks = []
            for q_idx, question, user_answer in open_ended_validations:
                task = self._validate_open_ended(
                    quiz_id=quiz_id,
                    question_id=question["id"],
                    q_idx=q_idx,
                    question=question,
                    user_answer=user_answer
                )
                tasks.append(task)

            # Process as they complete (stream incrementally)
            for completed_task in asyncio.as_completed(tasks):
                result = await completed_task
                yield {
                    "type": "validation",
                    "result": result
                }

        # Step 5: Calculate and send final summary
        total_questions = len(mcq_validations) + len(open_ended_validations)
        yield {
            "type": "done",
            "total_questions": total_questions,
            "quiz_id": quiz_id
        }

        print(f"✅ Validation complete for quiz {quiz_id}")

    async def _validate_open_ended(
        self,
        quiz_id: str,
        question_id: int,
        q_idx: int,
        question: Dict[str, Any],
        user_answer: str
    ) -> Dict[str, Any]:
        """Validate a single open-ended question with LLM."""
        feedback = await self._evaluate_open_ended_answer(
            question=question["question"],
            reference_answer=question.get("reference_answer", ""),
            key_points=question.get("key_points", []),
            student_answer=user_answer
        )

        # Save to database
        await self._save_attempt(
            quiz_id=quiz_id,
            question_id=question_id,
            user_answer=user_answer,
            llm_score=feedback["score"],
            llm_feedback=feedback
        )

        return {
            "question_index": q_idx,
            "question_type": "open_ended",
            "question": question["question"],
            "user_answer": user_answer,
            "llm_score": feedback["score"],
            "llm_feedback": feedback,
            "timestamp": question.get("timestamp"),
            "video_id": question.get("video_id"),
            "video_title": question.get("video_title"),
            "video_url": question.get("video_url"),
        }

    def _format_sources_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Format sources with numbering for LLM prompt."""
        formatted = []
        for idx, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            video_title = metadata.get("video_title", "Unknown")
            start_time = metadata.get("start_time", 0)
            end_time = metadata.get("end_time", 0)
            text = metadata.get("text", "")

            # Format timestamp
            start_min, start_sec = divmod(start_time, 60)
            end_min, end_sec = divmod(end_time, 60)
            timestamp = f"{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}"

            formatted.append(
                f"[{idx}] Video: {video_title} ({timestamp})\n{text}"
            )

        return "\n\n".join(formatted)

    def _enrich_questions_with_video_info(
        self,
        questions: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich questions with video information from chunks using source_index."""
        if not chunks:
            return questions

        for question in questions:
            # Skip if video info already exists
            if question.get("video_id") and question.get("video_title") and question.get("video_url"):
                continue

            source_index = question.get("source_index")
            if source_index is None:
                continue

            # Convert 1-based index to 0-based array index
            if 1 <= source_index <= len(chunks):
                chunk = chunks[source_index - 1]
                metadata = chunk.get("metadata", {})

                # Extract video information from chunk
                question["video_id"] = metadata.get("video_id", "")
                question["video_title"] = metadata.get("video_title", "")
                question["video_url"] = metadata.get("video_url", "")

                # Use chunk's start_time as timestamp
                question["timestamp"] = metadata.get("start_time", 0)
            else:
                print(f"⚠️ Warning: Invalid source_index {source_index} for question. Valid range: 1-{len(chunks)}")

        return questions

    async def _evaluate_open_ended_answer(
        self,
        question: str,
        reference_answer: str,
        key_points: List[str],
        student_answer: str
    ) -> Dict[str, Any]:
        """Use LLM to evaluate open-ended answer."""
        prompt = VALIDATE_ANSWER_PROMPT_TEMPLATE.format(
            question=question,
            reference_answer=reference_answer,
            key_points="\n".join([f"- {point}" for point in key_points]),
            student_answer=student_answer
        )

        response = await self.llm.generate_async(
            prompt=prompt,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            max_tokens=1000
        )

        # Parse JSON response
        try:
            feedback = json.loads(response)
            return feedback
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse evaluation response: {e}")
            # Return default feedback
            return {
                "score": 50,
                "feedback": "Unable to automatically evaluate. Please review with instructor.",
                "covered_points": [],
                "missing_points": key_points
            }

    async def _create_quiz(
        self,
        topic: Optional[str],
        chapters: Optional[List[str]],
        question_type: str,
        num_questions: int
    ) -> str:
        """Create new quiz record."""
        with self.postgres.session_scope() as session:
            new_quiz = Quiz(
                id=str(uuid.uuid4()),
                user_id="default_user",
                topic=topic,
                chapters=chapters,
                question_type=question_type,
                num_questions=num_questions
            )
            session.add(new_quiz)
            session.commit()
            return new_quiz.id

    async def _save_questions(
        self,
        quiz_id: str,
        questions: List[Dict[str, Any]]
    ):
        """Save generated questions to quiz_questions table."""
        with self.postgres.session_scope() as session:
            for idx, q in enumerate(questions):
                question_record = QuizQuestion(
                    quiz_id=quiz_id,
                    question_index=idx,
                    question=q["question"],
                    question_type=q["type"],
                    # MCQ fields
                    options=q.get("options"),
                    correct_answer=q.get("correct_answer"),
                    # Open-ended fields
                    reference_answer=q.get("reference_answer"),
                    key_points=q.get("key_points"),
                    # Common fields
                    explanation=q.get("explanation"),
                    source_index=q.get("source_index"),
                    video_id=q.get("video_id"),
                    video_title=q.get("video_title"),
                    video_url=q.get("video_url"),
                    timestamp=q.get("timestamp")
                )
                session.add(question_record)
            session.commit()

    async def _get_quiz_questions(self, quiz_id: str) -> List[Dict[str, Any]]:
        """Retrieve quiz questions."""
        with self.postgres.session_scope() as session:
            questions = session.query(QuizQuestion).filter_by(
                quiz_id=quiz_id
            ).order_by(QuizQuestion.question_index).all()

            result = []
            for q in questions:
                result.append({
                    "id": q.id,
                    "quiz_id": q.quiz_id,
                    "question_index": q.question_index,
                    "question": q.question,
                    "question_type": q.question_type,  # Use question_type (not "type")
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "reference_answer": q.reference_answer,
                    "key_points": q.key_points,
                    "explanation": q.explanation,
                    "source_index": q.source_index,
                    "video_id": q.video_id,
                    "video_title": q.video_title,
                    "video_url": q.video_url,
                    "timestamp": q.timestamp,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
            return result

    async def _save_attempt(
        self,
        quiz_id: str,
        question_id: int,
        user_answer: str,
        is_correct: Optional[bool] = None,
        llm_score: Optional[int] = None,
        llm_feedback: Optional[Dict[str, Any]] = None
    ):
        """Save user attempt to database."""
        with self.postgres.session_scope() as session:
            attempt = QuizAttempt(
                quiz_id=quiz_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                llm_score=llm_score,
                llm_feedback=llm_feedback
            )
            session.add(attempt)
            session.commit()


# Singleton instance
_quiz_service = None

def get_quiz_service() -> QuizService:
    """Get singleton quiz service."""
    global _quiz_service
    if _quiz_service is None:
        _quiz_service = QuizService()
    return _quiz_service
