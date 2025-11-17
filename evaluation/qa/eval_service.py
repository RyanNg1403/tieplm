"""
Q&A Evaluation Service

Evaluates Q&A responses using simplified metrics:
1. Exact Match - For MCQ questions (A/B/C/D matching)
2. Answer Correctness - Semantic similarity with ground truth (cosine + LLM score)
3. Citation Accuracy - Ground truth source in retrieved chunks
"""
import os
import sys
import numpy as np
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.shared.embeddings.embedder import OpenAIEmbedder
from app.shared.llm.client import LLMClient
from app.shared.rag.retriever import get_rag_retriever
from app.shared.rag.reranker import get_local_reranker

# Evaluation-specific prompts (ngắn gọn, không dài dòng như prompt cho users)
EVAL_QA_SYSTEM_PROMPT = """Bạn là trợ lý AI cho khóa học CS431 - Deep Learning.

NHIỆM VỤ: Trả lời câu hỏi dựa vào các nguồn transcript video được cung cấp.

QUY TẮC:
1. Trả lời NGẮN GỌN, đi thẳng vào vấn đề
2. Chỉ trả lời những gì có trong nguồn
3. Với câu hỏi trắc nghiệm: chỉ cần trả lời "A", "B", "C" hoặc "D" kèm giải thích ngắn
4. Với câu hỏi tự luận: trả lời súc tích trong 2-3 câu
5. Không cần format markdown phức tạp
"""

EVAL_QA_USER_PROMPT_TEMPLATE = """# NGUỒN TÀI LIỆU:
{sources}

# CÂU HỎI:
{query}

# TRẢ LỜI:
(Trả lời ngắn gọn, đi thẳng vào vấn đề)
"""


class QAEvaluationService:
    """Service for evaluating Q&A task performance."""
    
    def __init__(self):
        self.embedder = OpenAIEmbedder()
        self.llm = LLMClient()
        self.retriever = get_rag_retriever()
        self.reranker = get_local_reranker()
        
    async def evaluate_question(
        self,
        question: str,
        ground_truth_answer: str,
        ground_truth_videos: List[str],
        ground_truth_timestamps: List[str],
        chapters: Optional[List[str]] = None,
        question_type: str = "short_answer",  # "mcq" hoặc "short_answer"
        ground_truth_options: Optional[str] = None  # Cho MCQ
    ) -> Dict[str, Any]:
        """
        Evaluate a single Q&A question.
        
        Args:
            question: User question
            ground_truth_answer: Expected answer from ground truth
            ground_truth_videos: List of expected video URLs
            ground_truth_timestamps: List of expected timestamp ranges
            chapters: Optional chapter filter
            question_type: "mcq" or "short_answer"
            ground_truth_options: Options string for MCQ (e.g., "a) ... b) ... c) ... d) ...")
            
        Returns:
            Dict with evaluation metrics and details
        """
        # Step 1: Retrieve và rerank chunks
        print(f"  📚 Retrieving chunks...")
        retrieved_chunks = await self.retriever.retrieve(
            query=question,
            top_k=150,
            chapter_filter=chapters,
            use_bm25=True
        )
        
        # Rerank to get top 10
        print(f"  🔄 Reranking to top 10...")
        reranked_chunks = self.reranker.rerank(question, retrieved_chunks, top_k=10)
        
        # Format sources cho prompt
        sources_text = ""
        for i, chunk in enumerate(reranked_chunks, 1):
            metadata = chunk.get('metadata', {})
            sources_text += f"[{i}] {metadata.get('video_title', 'Unknown')}\n"
            start_time = metadata.get('start_time', 0)
            end_time = metadata.get('end_time', 0)
            sources_text += f"Timestamp: {self._format_timestamp(start_time)} - {self._format_timestamp(end_time)}\n"
            sources_text += f"{metadata.get('text', '')}\n\n"
        
        # Build eval prompt
        query_with_options = question
        if question_type == "mcq" and ground_truth_options:
            query_with_options += f"\n\nCác phương án:\n{ground_truth_options}"
        
        eval_prompt = EVAL_QA_USER_PROMPT_TEMPLATE.format(
            sources=sources_text,
            query=query_with_options
        )
        
        # Step 2: Generate answer với eval prompt
        print(f"  🤖 Generating answer with LLM...")
        generated_answer = await self.llm.generate_async(
            prompt=eval_prompt,
            system_prompt=EVAL_QA_SYSTEM_PROMPT,
            max_tokens=500
        )
        
        # Convert chunks to sources format
        generated_sources = []
        for chunk in reranked_chunks:
            metadata = chunk.get('metadata', {})
            start_time = metadata.get('start_time', 0)
            end_time = metadata.get('end_time', 0)
            generated_sources.append({
                "video_title": metadata.get("video_title", ""),
                "video_url": metadata.get("video_url", ""),
                "timestamp": f"{self._format_timestamp(start_time)} - {self._format_timestamp(end_time)}",
                "text": metadata.get("text", "")
            })
        
        # Step 3: Calculate metrics
        print(f"  📊 Calculating metrics...")
        metrics = {}
        
        # Metric 1: Exact Match (chỉ cho MCQ)
        if question_type == "mcq":
            metrics["exact_match"] = self._calculate_exact_match(
                generated_answer, ground_truth_answer
            )
        
        # Metric 2: Answer Correctness (cho cả MCQ và tự luận)
        metrics["answer_correctness"] = await self._calculate_answer_correctness(
            question, generated_answer, ground_truth_answer
        )
        
        # Metric 3: Citation Accuracy (đơn giản - kiểm tra ground truth source có trong retrieved không)
        metrics["citation_accuracy"] = self._calculate_citation_accuracy_simple(
            generated_sources, ground_truth_videos, ground_truth_timestamps
        )
        
        # Step 4: Return evaluation result
        return {
            "question": question,
            "question_type": question_type,
            "generated_answer": generated_answer,
            "ground_truth_answer": ground_truth_answer,
            "generated_sources": generated_sources,
            "ground_truth_videos": ground_truth_videos,
            "ground_truth_timestamps": ground_truth_timestamps,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_exact_match(
        self,
        generated_answer: str,
        ground_truth_answer: str
    ) -> Dict[str, Any]:
        """
        Metric cho MCQ: Exact Match
        
        Trích xuất lựa chọn (a, b, c, d) từ câu trả lời và so sánh.
        
        Returns:
            Dict with:
            - predicted_choice: str (a/b/c/d)
            - ground_truth_choice: str (a/b/c/d)
            - is_correct: bool
            - score: float (1.0 hoặc 0.0)
        """
        # Extract choice từ generated answer (tìm a, b, c, d đầu tiên)
        predicted_choice = None
        generated_lower = generated_answer.lower()
        
        # Tìm pattern "a)", "b)", "c)", "d)" hoặc đơn giản "a", "b", "c", "d"
        for choice in ['a', 'b', 'c', 'd']:
            if f"{choice})" in generated_lower[:50] or f"{choice}." in generated_lower[:50]:
                predicted_choice = choice
                break
            # Fallback: tìm chữ đơn
            if generated_lower.strip().startswith(choice):
                predicted_choice = choice
                break
        
        # Extract choice từ ground truth
        ground_truth_choice = None
        ground_truth_lower = ground_truth_answer.lower()
        for choice in ['a', 'b', 'c', 'd']:
            if ground_truth_lower.strip().startswith(f"{choice})") or ground_truth_lower.strip().startswith(f"{choice}."):
                ground_truth_choice = choice
                break
        
        is_correct = (predicted_choice == ground_truth_choice) if predicted_choice and ground_truth_choice else False
        
        return {
            "predicted_choice": predicted_choice,
            "ground_truth_choice": ground_truth_choice,
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0
        }
    
    async def _calculate_answer_correctness(
        self,
        question: str,
        generated: str, 
        ground_truth: str
    ) -> Dict[str, Any]:
        """
        Metric: Answer Correctness
        
        Uses both embedding similarity and LLM-based evaluation.
        
        Returns:
            Dict with:
            - cosine_similarity: float (0-1)
            - llm_score: float (0-1)
            - combined_score: float (0-1)
            - explanation: str
        """
        # Embedding-based similarity
        gen_embedding = self.embedder.embed(generated)
        gt_embedding = self.embedder.embed(ground_truth)
        
        # Cosine similarity
        embedding_sim = float(np.dot(gen_embedding, gt_embedding) / 
                            (np.linalg.norm(gen_embedding) * np.linalg.norm(gt_embedding)))
        
        # LLM-based evaluation (thêm question để LLM hiểu context)
        llm_prompt = f"""Đánh giá độ chính xác của câu trả lời được generate so với đáp án ground truth.

# Câu hỏi gốc:
{question}

# Đáp án Ground Truth:
{ground_truth}

# Câu trả lời được Generate:
{generated}

# Yêu cầu đánh giá:
1. So sánh nội dung semantic (ý nghĩa) của hai câu trả lời
2. Kiểm tra xem câu trả lời generated có đủ thông tin quan trọng từ ground truth không
3. Đánh giá độ chính xác về mặt kỹ thuật (thuật ngữ, định nghĩa)
4. Xét trong context của câu hỏi gốc

# Output format (JSON):
{{
    "score": <float 0-1>,
    "explanation": "<giải thích ngắn gọn>"
}}

Chỉ trả về JSON, không giải thích thêm.
"""
        
        llm_response = await self.llm.generate_async(
            prompt=llm_prompt,
            system_prompt="You are an evaluation assistant. Return only valid JSON.",
            max_tokens=500
        )
        
        # Parse LLM response
        try:
            llm_eval = json.loads(llm_response.strip())
            llm_score = float(llm_eval.get("score", 0.0))
            explanation = llm_eval.get("explanation", "")
        except:
            llm_score = 0.0
            explanation = "Failed to parse LLM evaluation"
        
        # Combined score (weighted average)
        combined_score = 0.4 * embedding_sim + 0.6 * llm_score
        
        return {
            "cosine_similarity": round(embedding_sim, 4),
            "llm_score": round(llm_score, 4),
            "combined_score": round(combined_score, 4),
            "explanation": explanation
        }
    
    def _calculate_citation_accuracy_simple(
        self,
        generated_sources: List[Dict[str, Any]],
        ground_truth_videos: List[str],
        ground_truth_timestamps: List[str]
    ) -> Dict[str, Any]:
        """
        Metric: Citation Accuracy (Đơn giản hóa)
        
        Kiểm tra xem ground truth source có nằm trong 10 chunks retrieved không.
        Mỗi câu hỏi chỉ có 1 source, RAG retrieve 10 chunks.
        
        Returns:
            Dict with:
            - ground_truth_in_retrieved: bool
            - retrieved_count: int
            - score: float (1.0 nếu có, 0.0 nếu không)
        """
        if not ground_truth_videos or not generated_sources:
            return {
                "ground_truth_in_retrieved": False,
                "retrieved_count": len(generated_sources),
                "score": 0.0,
                "details": "No ground truth or no retrieved sources"
            }
        
        # Lấy ground truth video URL (chỉ có 1)
        gt_video_url = ground_truth_videos[0]
        gt_timestamp = ground_truth_timestamps[0] if ground_truth_timestamps else None
        
        # Extract video ID từ ground truth
        gt_video_id = self._extract_video_id(gt_video_url)
        
        # Kiểm tra xem có chunk nào match không
        found = False
        for source in generated_sources:
            source_video_id = self._extract_video_id(source.get("video_url", ""))
            
            if source_video_id == gt_video_id:
                # Nếu có timestamp, kiểm tra overlap
                if gt_timestamp:
                    source_timestamp = source.get("timestamp", "")
                    if self._check_timestamp_overlap(gt_timestamp, source_timestamp):
                        found = True
                        break
                else:
                    # Không có timestamp thì chỉ cần video ID khớp
                    found = True
                    break
        
        return {
            "ground_truth_in_retrieved": found,
            "retrieved_count": len(generated_sources),
            "score": 1.0 if found else 0.0,
            "ground_truth_video": gt_video_url,
            "ground_truth_timestamp": gt_timestamp
        }
    
    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL."""
        if "youtu.be/" in url:
            return url.split("youtu.be/")[-1].split("?")[0]
        elif "youtube.com/watch?v=" in url:
            return url.split("v=")[-1].split("&")[0]
        return url
    
    def _check_timestamp_overlap(self, gt_timestamp: str, source_timestamp: str) -> bool:
        """Kiểm tra xem 2 timestamp có overlap không."""
        try:
            # Parse ground truth timestamp (format: "00:26:00 - 00:27:00")
            if " - " in gt_timestamp:
                gt_start_str, gt_end_str = gt_timestamp.split(" - ")
                gt_start = self._parse_timestamp(gt_start_str.strip())
                gt_end = self._parse_timestamp(gt_end_str.strip())
            else:
                # Single timestamp
                gt_start = gt_end = self._parse_timestamp(gt_timestamp.strip())
            
            # Parse source timestamp (format: "00:26:15")
            if " - " in source_timestamp:
                src_start_str, src_end_str = source_timestamp.split(" - ")
                src_start = self._parse_timestamp(src_start_str.strip())
                src_end = self._parse_timestamp(src_end_str.strip())
            else:
                src_start = src_end = self._parse_timestamp(source_timestamp.strip())
            
            # Check overlap
            return not (src_end < gt_start or src_start > gt_end)
        except:
            return False
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _parse_timestamp(self, timestamp: str) -> int:
        """Convert timestamp string (HH:MM:SS) to seconds."""
        parts = timestamp.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0
