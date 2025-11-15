"""Quiz generation service - orchestration logic."""
import os
import json
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional

from ...shared.rag.reranker import LocalReranker, get_local_reranker
from ...shared.rag.retriever import RAGRetriever, get_rag_retriever

from ...shared.llm.client import LLMClient, get_llm_client
from ...shared.database.postgres import PostgresClient, get_postgres_client
from ...shared.database.models import ChatSession, ChatMessage

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
    1. Fetch video transcript from database
    2. Build prompt with transcript content
    3. Generate questions using LLM (MCQ or open-ended)
    4. Parse and validate LLM response
    5. Save questions to database
    6. Return formatted quiz
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
        question_type: str = "mcq",
        num_questions: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate quiz questions from a list of videos.

        Args:
            video_ids: List of video IDs to generate quiz from
            question_type: Type of questions - "mcq", "open_ended", or "mixed"
            num_questions: Number of questions to generate (default from env)
            session_id: Optional existing session ID, otherwise creates new

        Returns:
            Dict containing:
            - quiz_id: Unique quiz identifier (session_id)
            - video_ids: List of source video IDs
            - videos: List of video metadata
            - questions: List of generated questions (each with video_url and video_id)
            - question_type: Type of quiz
        """
        num_questions = num_questions or self.default_num_questions

        # Handle video_ids - default to empty list if None
        if video_ids is None:
            video_ids = []
        
        source_identifier = f"{len(video_ids)} video(s)" if len(video_ids) > 1 else (video_ids[0] if video_ids else "all videos")

        # Step 0: Create or get session BEFORE generation
        created_session_id = await self._create_session(
            session_id=session_id,
            query=f"{query if query else source_identifier} - {num_questions} {question_type} questions"
        )

        # Step 1: Retrieve relevant chunks
        if query:
            print(f"📚 Retrieving chunks for query: {query[:50]}...")
            retrieved_chunks = await self.retriever.retrieve(
                query=query,
                top_k=self.retrieval_top_k,
                use_bm25=True
            )
            print(f"✅ Retrieved {len(retrieved_chunks)} chunks")
            
            if not retrieved_chunks:
                # No results found
                yield {
                    "type": "error",
                    "content": "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
                }
                return
        else:
            # If no query, retrieve chunks from selected videos
            # For now, we'll use a generic query to retrieve from all videos
            # In the future, we could add video_id filtering to the retriever
            print(f"📚 Retrieving chunks from {len(video_ids)} video(s)...")
            retrieved_chunks = await self.retriever.retrieve(
                query=source_identifier,
                top_k=self.retrieval_top_k,
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
                "session_id": created_session_id
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
            # This ensures consistency with Q&A and text_summary services
            all_questions = self._enrich_questions_with_video_info(
                questions=all_questions,
                chunks=reranked_chunks
            )

            # Yield final progress
            yield {
                "type": "progress",
                "progress": 100,
                "session_id": created_session_id
            }

            # Yield final raw response (the original JSON from LLM)
            yield {
                "type": "done",
                "content": json.dumps(all_questions, ensure_ascii=False),  # Raw JSON response
                "session_id": created_session_id
            }

            print(f"✅ Generated {len(all_questions)} questions")
            print(f"Questions: {json.dumps(all_questions, ensure_ascii=False)}")

            # Step 6: Save questions to database
            await self._save_questions(
                questions=all_questions,
                session_id=created_session_id
            )
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
    ) -> Dict[str, Any]:
        """
        Validate user answers for a quiz.

        Args:
            quiz_id: Quiz session ID
            answers: List of user answers:
                For MCQ: {"question_index": 0, "answer": "A"}
                For open-ended: {"question_index": 0, "answer": "User's text answer"}

        Returns:
            Dict containing:
            - total_questions: Total number of questions
            - mcq_score: Score for MCQ questions (if any)
            - open_ended_feedback: Feedback for open-ended questions (if any)
            - overall_score: Overall percentage score
        """
        # Step 1: Retrieve quiz questions from session
        print(f"📝 Validating answers for quiz {quiz_id}...")
        questions = await self._get_quiz_questions(quiz_id)

        if not questions:
            raise ValueError(f"No questions found for quiz {quiz_id}")

        # Step 2: Separate MCQ and open-ended questions
        mcq_results = []
        open_ended_results = []

        for answer_data in answers:
            q_idx = answer_data["question_index"]
            user_answer = answer_data["answer"]

            if q_idx >= len(questions):
                continue

            question = questions[q_idx]

            if question["type"] == "mcq":
                # Validate MCQ answer
                is_correct = user_answer == question["correct_answer"]
                mcq_results.append({
                    "question_index": q_idx,
                    "question": question["question"],
                    "user_answer": user_answer,
                    "correct_answer": question["correct_answer"],
                    "is_correct": is_correct,
                    "explanation": question.get("explanation", ""),
                    "timestamp": question.get("timestamp"),
                    "video_id": question.get("video_id"),
                    "video_title": question.get("video_title"),
                    "video_url": question.get("video_url")
                })

            elif question["type"] == "open_ended":
                # Use LLM to evaluate open-ended answer
                feedback = await self._evaluate_open_ended_answer(
                    question=question["question"],
                    reference_answer=question.get("reference_answer", ""),
                    key_points=question.get("key_points", []),
                    student_answer=user_answer
                )
                open_ended_results.append({
                    "question_index": q_idx,
                    "question": question["question"],
                    "user_answer": user_answer,
                    "feedback": feedback,
                    "timestamp": question.get("timestamp"),
                    "video_id": question.get("video_id"),
                    "video_title": question.get("video_title"),
                    "video_url": question.get("video_url")
                })

        # Step 3: Calculate scores
        mcq_score = 0
        if mcq_results:
            correct_count = sum(1 for r in mcq_results if r["is_correct"])
            mcq_score = (correct_count / len(mcq_results)) * 100

        open_ended_avg_score = 0
        if open_ended_results:
            total_score = sum(r["feedback"]["score"] for r in open_ended_results)
            open_ended_avg_score = total_score / len(open_ended_results)

        # Overall score (weighted average)
        total_questions = len(mcq_results) + len(open_ended_results)
        if total_questions > 0:
            overall_score = (
                (len(mcq_results) * mcq_score + len(open_ended_results) * open_ended_avg_score)
                / total_questions
            )
        else:
            overall_score = 0

        print(f"✅ Validation complete: {overall_score:.1f}% overall")

        return {
            "total_questions": total_questions,
            "mcq_results": mcq_results,
            "mcq_score": mcq_score,
            "open_ended_results": open_ended_results,
            "open_ended_avg_score": open_ended_avg_score,
            "overall_score": overall_score
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
    
    def _format_sources_for_response(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for frontend response."""
        sources = []
        for idx, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            sources.append({
                "index": idx,
                "video_id": metadata.get("video_id", ""),
                "chapter": metadata.get("chapter", ""),
                "video_title": metadata.get("video_title", ""),
                "video_url": metadata.get("video_url", ""),
                "start_time": metadata.get("start_time", 0),
                "end_time": metadata.get("end_time", 0),
                "text": metadata.get("text", ""),
                "score": chunk.get("rerank_score", chunk.get("rrf_score", chunk.get("score", 0)))
            })
        return sources

    def _enrich_questions_with_video_info(
        self,
        questions: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich questions with video information from chunks using source_index.
        
        This method uses the source_index from each question to directly map to the
        corresponding chunk and extract video_id, video_title, and video_url. This
        ensures consistency with how Q&A and text_summary services handle video sources.
        
        Args:
            questions: List of generated questions (should have source_index field)
            chunks: List of RAG chunks with video metadata (indexed 0-based)
            
        Returns:
            List of questions enriched with video information
        """
        if not chunks:
            return questions
        
        for question in questions:
            # Skip if video info already exists (LLM might have included it)
            if question.get("video_id") and question.get("video_title") and question.get("video_url"):
                continue
            
            source_index = question.get("source_index")
            if source_index is None:
                continue
            
            # Convert 1-based index to 0-based array index
            # source_index should be between 1 and len(chunks)
            if 1 <= source_index <= len(chunks):
                chunk = chunks[source_index - 1]
                metadata = chunk.get("metadata", {})
                
                # Extract video information from chunk
                question["video_id"] = metadata.get("video_id", "")
                question["video_title"] = metadata.get("video_title", "")
                question["video_url"] = metadata.get("video_url", "")
                
                # Use chunk's start_time as timestamp (chunks already have this in metadata)
                question["timestamp"] = metadata.get("start_time", 0)
            else:
                # Invalid source_index - log warning but don't fail
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

    async def _create_session(
        self,
        session_id: Optional[str],
        query: str
    ) -> str:
        """
        Create new session or validate existing one BEFORE streaming.
        
        Returns:
            session_id (str): ID of created or validated session
        """
        with self.postgres.session_scope() as session:
            # Create new session
            new_session = ChatSession(
                id=str(uuid.uuid4()),
                task_type="quiz",
                title=query[:100],  # Use first 100 chars of query as title
                user_id="default_user"
            )
            session.add(new_session)
            session.commit()
            return new_session.id

    async def _save_questions(
        self,
        questions: List[Dict[str, Any]],
        session_id: str
    ):
        """Save generated questions to database."""
        with self.postgres.session_scope() as session:
            # Save questions as a single assistant message with JSON content
            questions_json = json.dumps(questions, ensure_ascii=False)

            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=questions_json,
                sources=[]  # No sources for quiz generation
            )
            session.add(assistant_message)

    async def _get_quiz_questions(self, quiz_id: str) -> List[Dict[str, Any]]:
        """Retrieve quiz questions from session."""
        with self.postgres.session_scope() as session:
            messages = session.query(ChatMessage).filter_by(
                session_id=quiz_id,
                role="assistant"
            ).order_by(ChatMessage.created_at).all()

            if not messages:
                return []

            # Get the latest assistant message (contains questions)
            latest_message = messages[-1]

            try:
                questions = json.loads(latest_message.content)
                return questions
            except json.JSONDecodeError:
                return []


# Singleton instance
_quiz_service = None

def get_quiz_service() -> QuizService:
    """Get singleton quiz service."""
    global _quiz_service
    if _quiz_service is None:
        _quiz_service = QuizService()
    return _quiz_service

