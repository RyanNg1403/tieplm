"""Quiz generation service - orchestration logic."""
import os
import json
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

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

        source_identifier = f"{len(video_ids)} video(s)" if len(video_ids) > 1 else video_ids[0]

        # Step 0: Create or get session BEFORE generation
        created_session_id = await self._create_session(
            session_id=session_id,
            query=f"{query if query else source_identifier} - {num_questions} {question_type} questions"
        )

        # if query:
        #     # Step 1: Retrieve relevant chunks
        #     print(f"📚 Retrieving chunks for question: {query[:50]}...")
        #     retrieved_chunks = await self.retriever.retrieve(
        #         query=query,
        #         top_k=self.retrieval_top_k,
        #         # video_filter=video_ids,
        #         use_bm25=True
        #     )
        #     print(f"✅ Retrieved {len(retrieved_chunks)} chunks")
            
        #     if not retrieved_chunks:
        #         # No results found
        #         yield {
        #             "type": "error",
        #             "content": "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
        #         }
        #         return
            
        #     # Step 2: Rerank (if enabled)
        #     if self.enable_reranking and len(retrieved_chunks) > self.final_top_k:
        #         print(f"🔄 Reranking {len(retrieved_chunks)} chunks...")
        #         reranked_chunks = self.reranker.rerank(
        #             query=query,
        #             results=retrieved_chunks,
        #             top_k=self.final_top_k
        #         )
        #         print(f"✅ Reranked to top-{len(reranked_chunks)} chunks")
        #     else:
        #         reranked_chunks = retrieved_chunks[:self.final_top_k]
        # else:
        #     # If there is no query, filter the selected videos/chapters
        #     reranked_chunks = []
        #     pass

        # # Step 2: Generate questions per video for better attribution
        # print(f"🤖 Generating {num_questions} {question_type} questions...")

        # # Step 3: Format sources for prompt and response
        # sources_for_prompt = self._format_sources_for_prompt(reranked_chunks)
        # sources_for_response = self._format_sources_for_response(reranked_chunks)
        
        # # Step 4: Stream LLM response with progress updates
        # print("🤖 Generating questions with LLM...")

        # # Generate questions with inline progress tracking
        # accumulated_response = ""
        # # Estimate total length: each question ~600-800 chars, plus JSON structure overhead
        # base_estimate = num_questions * 700
        # estimated_total_length = base_estimate

        # # Choose prompt based on question type
        # match question_type:
        #     case "mcq":
        #         prompt = MCQ_GENERATION_PROMPT_TEMPLATE.format(
        #             sources=sources_for_prompt,
        #             num_questions=num_questions
        #         )
        #     case "open_ended":
        #         prompt = OPEN_ENDED_GENERATION_PROMPT_TEMPLATE.format(
        #             sources=sources_for_prompt,
        #             num_questions=num_questions
        #         )
        #     # case "mixed":
        #     #     prompt = MIXED_GENERATION_PROMPT_TEMPLATE.format(
        #     #         sources=sources_for_prompt,
        #     #         num_mcq=num_questions // 2,
        #     #         num_open=num_questions - num_questions // 2
        #     #     )
        #     case _:
        #         raise ValueError(f"Invalid question type: {question_type}")

        # # Stream tokens from LLM and yield progress
        # async for token in self.llm.stream(
        #     prompt=prompt,
        #     system_prompt=QUIZ_SYSTEM_PROMPT,
        #     max_tokens=3000
        # ):
        #     accumulated_response += token
        #     current_length = len(accumulated_response)

        #     # Dynamically adjust estimate if we exceed it
        #     if current_length > estimated_total_length:
        #         # Increase estimate by 20% to accommodate longer responses
        #         estimated_total_length = int(current_length * 1.2)

        #     # Calculate progress based on actual JSON response length
        #     # Cap at 95% until we're actually done parsing
        #     progress = min(95, int((current_length / estimated_total_length) * 100))

        #     yield {
        #         "type": "progress",
        #         "progress": progress,
        #         "session_id": created_session_id
        #     }

        accumulated_response = '{"questions": [{"question": "Mục đích chính của mạng Recurrent Neural Network (RNN) là gì?", "options": {"A": "Xử lý và học từ dữ liệu có cấu trúc lưới như ảnh", "B": "Xử lý dữ liệu dạng chuỗi và nắm bắt phụ thuộc theo thứ tự", "C": "Giảm chiều dữ liệu với mục đích nén", "D": "Thực hiện phân cụm các điểm dữ liệu không giám sát"}, "correct_answer": "B", "timestamp": 25, "explanation": "RNN được thiết kế để xử lý dữ liệu chuỗi, có khả năng giữ trạng thái ẩn theo thời gian để nắm bắt các phụ thuộc theo thứ tự giữa các phần tử trong chuỗi.", "question_type": "mcq"}, {"question": "Trong kiến trúc sequence-to-sequence (encoder-decoder) cho dịch máy, vai trò chính của encoder là gì?", "options": {"A": "Sinh ra câu dịch đầu ra từng token một", "B": "Đọc và mã hóa (encode) thông tin đầu vào thành hidden state biểu diễn", "C": "Tạo từ điển và tiền xử lý dữ liệu đầu vào", "D": "Áp dụng hàm softmax để chọn từ tiếp theo"}, "correct_answer": "B", "timestamp": 295, "explanation": "Encoder đọc chuỗi đầu vào và mã hóa thông tin vào các hidden state (biểu diễn) để decoder sử dụng khi sinh câu đầu ra.", "question_type": "mcq"}, {"question": "Tại sao các mạng feedforward (neural network thông thường) không phù hợp trực tiếp cho mọi bài toán dữ liệu dạng chuỗi?", "options": {"A": "Dữ liệu chuỗi có thứ tự và phụ thuộc thời gian nên cần cơ chế giữ trạng thái qua các bước thời gian", "B": "Vì mạng feedforward luôn yêu cầu dữ liệu có dạng ảnh", "C": "Vì mạng feedforward không thể tính softmax", "D": "Vì dữ liệu chuỗi luôn có kích thước cố định"}, "correct_answer": "A", "timestamp": 60, "explanation": "Dữ liệu chuỗi có quan hệ theo thứ tự (temporal dependencies); RNN cung cấp trạng thái ẩn theo thời gian để xử lý các phụ thuộc này, điều mà mạng feedforward tiêu chuẩn không làm được.", "question_type": "mcq"}, {"question": "Trong Keras, Embedding layer được dùng để làm gì trong bài toán xử lý ngôn ngữ?", "options": {"A": "Map mỗi token rời rạc sang một vector đặc trưng dày (dense vector)", "B": "Thực hiện lớp phân loại cuối cùng bằng softmax", "C": "Thực hiện phép tích chập trên chuỗi đầu vào", "D": "Chuẩn hóa đầu vào bằng batch normalization"}, "correct_answer": "A", "timestamp": 20, "explanation": "Embedding layer ánh xạ các chỉ số token rời rạc thành vector dày (vector nhúng) để mạng có thể học đại diện liên tục cho từ/ngữ.", "question_type": "mcq"}, {"question": "Khi giảng nói Neural Machine Translation là một phương pháp end-to-end, điều đó có nghĩa là gì?", "options": {"A": "Hệ thống sử dụng nhiều mô-đun thủ công xen kẽ với mô hình học máy", "B": "Hệ thống dựa hoàn toàn trên quy tắc ngôn ngữ viết tay", "C": "Toàn bộ ánh xạ từ câu nguồn sang câu đích được học bởi một (hoặc một hệ mô hình thần kinh) mà không cần các bước trung gian thủ công", "D": "Chỉ dùng các mô hình thống kê cổ điển chứ không dùng neural networks"}, "correct_answer": "C", "timestamp": 247, "explanation": "End-to-end ở đây nghĩa là mô hình neural (ví dụ RNN seq2seq) học trực tiếp ánh xạ từ câu nguồn sang câu đích mà không cần các bước xử lý trung gian thủ công hay mô-đun riêng biệt.", "question_type": "mcq"}]}'
        
        yield {
            "type": "progress",
            "progress": 50,
            "session_id": created_session_id
        }

        print("LLM response received for quiz generation.")
        print(f"Response: {accumulated_response}")

        # Parse JSON response
        try:
            parsed = json.loads(accumulated_response)
            all_questions = parsed.get("questions", [])

            # Add type field
            for q in all_questions:
                q["question_type"] = question_type

            print(f"Generated {len(all_questions)} questions")

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

            # Step 5: Save questions to database
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
                    "explanation": question.get("explanation", "")
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
                    "feedback": feedback
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

