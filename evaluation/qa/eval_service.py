"""
Q&A Evaluation Service

Evaluates Q&A responses using 4 key metrics:
1. Answer Correctness - Semantic similarity with ground truth
2. Citation Accuracy - Presence and correctness of citations
3. Source Relevance - Retrieved sources match ground truth videos/timestamps
4. Hallucination Rate - Generated content not grounded in sources
"""
import os
import re
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.shared.embeddings.embedder import OpenAIEmbedder
from app.shared.llm.client import LLMClient
from app.core.qa.service import QAService


class QAEvaluationService:
    """Service for evaluating Q&A task performance."""
    
    def __init__(self):
        self.qa_service = QAService()
        self.embedder = OpenAIEmbedder()
        self.llm = LLMClient()
        
    async def evaluate_question(
        self,
        question: str,
        ground_truth_answer: str,
        ground_truth_videos: List[str],
        ground_truth_timestamps: List[str],
        chapters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single Q&A question.
        
        Args:
            question: User question
            ground_truth_answer: Expected answer from ground truth
            ground_truth_videos: List of expected video URLs
            ground_truth_timestamps: List of expected timestamp ranges
            chapters: Optional chapter filter
            
        Returns:
            Dict with evaluation metrics and details
        """
        # Step 1: Generate answer using Q&A service
        generated_answer = ""
        generated_sources = []
        
        async for event in self.qa_service.answer(
            query=question,
            chapters=chapters,
            session_id=None  # Create new session for each eval
        ):
            if event["type"] == "token":
                generated_answer += event["content"]
            elif event["type"] == "sources":
                generated_sources = event["sources"]
        
        # Step 2: Calculate metrics
        metrics = {
            "answer_correctness": await self._calculate_answer_correctness(
                generated_answer, ground_truth_answer
            ),
            "citation_accuracy": self._calculate_citation_accuracy(
                generated_answer, generated_sources
            ),
            "source_relevance": self._calculate_source_relevance(
                generated_sources, ground_truth_videos, ground_truth_timestamps
            ),
            "hallucination_rate": await self._calculate_hallucination_rate(
                generated_answer, generated_sources
            )
        }
        
        # Step 3: Return evaluation result
        return {
            "question": question,
            "generated_answer": generated_answer,
            "ground_truth_answer": ground_truth_answer,
            "generated_sources": generated_sources,
            "ground_truth_videos": ground_truth_videos,
            "ground_truth_timestamps": ground_truth_timestamps,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _calculate_answer_correctness(
        self, 
        generated: str, 
        ground_truth: str
    ) -> Dict[str, Any]:
        """
        Metric 1: Answer Correctness
        
        Uses both embedding similarity and LLM-based evaluation.
        
        Returns:
            Dict with:
            - embedding_similarity: float (0-1)
            - llm_score: float (0-1)
            - combined_score: float (0-1)
            - explanation: str
        """
        # Embedding-based similarity
        gen_embedding = self.embedder.embed(generated)
        gt_embedding = self.embedder.embed(ground_truth)
        
        # Cosine similarity
        import numpy as np
        embedding_sim = float(np.dot(gen_embedding, gt_embedding) / 
                            (np.linalg.norm(gen_embedding) * np.linalg.norm(gt_embedding)))
        
        # LLM-based evaluation
        llm_prompt = f"""Đánh giá độ chính xác của câu trả lời được generate so với đáp án ground truth.

# Đáp án Ground Truth:
{ground_truth}

# Câu trả lời được Generate:
{generated}

# Yêu cầu đánh giá:
1. So sánh nội dung semantic (ý nghĩa) của hai câu trả lời
2. Kiểm tra xem câu trả lời generated có đủ thông tin quan trọng từ ground truth không
3. Đánh giá độ chính xác về mặt kỹ thuật (thuật ngữ, định nghĩa)

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
        import json
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
            "embedding_similarity": round(embedding_sim, 4),
            "llm_score": round(llm_score, 4),
            "combined_score": round(combined_score, 4),
            "explanation": explanation
        }
    
    def _calculate_citation_accuracy(
        self,
        generated_answer: str,
        generated_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Metric 2: Citation Accuracy
        
        Checks:
        1. Are citations present? ([1], [2], [3])
        2. Do citations match actual sources?
        3. Are citations used correctly?
        
        Returns:
            Dict with:
            - has_citations: bool
            - citation_count: int
            - valid_citation_count: int
            - citation_coverage: float (0-1)
            - accuracy_score: float (0-1)
        """
        # Extract citations from answer
        citation_pattern = r'\[(\d+)\]'
        citations = re.findall(citation_pattern, generated_answer)
        citation_numbers = [int(c) for c in citations]
        unique_citations = set(citation_numbers)
        
        has_citations = len(unique_citations) > 0
        citation_count = len(unique_citations)
        
        # Check if citations match sources
        source_count = len(generated_sources)
        valid_citations = [c for c in unique_citations if 1 <= c <= source_count]
        valid_citation_count = len(valid_citations)
        
        # Citation coverage: How many sources were cited?
        citation_coverage = valid_citation_count / source_count if source_count > 0 else 0.0
        
        # Accuracy score: Are all citations valid?
        accuracy_score = valid_citation_count / citation_count if citation_count > 0 else 0.0
        
        return {
            "has_citations": has_citations,
            "citation_count": citation_count,
            "valid_citation_count": valid_citation_count,
            "citation_coverage": round(citation_coverage, 4),
            "accuracy_score": round(accuracy_score, 4)
        }
    
    def _calculate_source_relevance(
        self,
        generated_sources: List[Dict[str, Any]],
        ground_truth_videos: List[str],
        ground_truth_timestamps: List[str]
    ) -> Dict[str, Any]:
        """
        Metric 3: Source Relevance
        
        Checks if retrieved sources match ground truth videos/timestamps.
        
        Returns:
            Dict with:
            - video_match_count: int
            - timestamp_overlap_count: int
            - precision: float (0-1)
            - recall: float (0-1)
            - f1_score: float (0-1)
        """
        video_match_count = 0
        timestamp_overlap_count = 0
        
        # Extract video IDs from URLs
        def extract_video_id(url: str) -> str:
            """Extract YouTube video ID from URL."""
            match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
            return match.group(1) if match else ""
        
        gt_video_ids = [extract_video_id(url) for url in ground_truth_videos]
        
        # Check each generated source
        for source in generated_sources:
            source_video_url = source.get("video_url", "")
            source_video_id = extract_video_id(source_video_url)
            
            # Video match
            if source_video_id in gt_video_ids:
                video_match_count += 1
                
                # Check timestamp overlap
                source_start = source.get("start_time", 0)
                source_end = source.get("end_time", 0)
                
                for ts_range in ground_truth_timestamps:
                    # Parse timestamp range (e.g., "00:26:00 - 00:27:00")
                    ts_match = re.match(r'(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)', ts_range.strip())
                    if ts_match:
                        gt_start = self._parse_timestamp(ts_match.group(1))
                        gt_end = self._parse_timestamp(ts_match.group(2))
                        
                        # Check overlap
                        if not (source_end < gt_start or source_start > gt_end):
                            timestamp_overlap_count += 1
                            break
        
        # Calculate precision, recall, F1
        total_generated = len(generated_sources)
        total_ground_truth = len(ground_truth_videos)
        
        precision = video_match_count / total_generated if total_generated > 0 else 0.0
        recall = video_match_count / total_ground_truth if total_ground_truth > 0 else 0.0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "video_match_count": video_match_count,
            "timestamp_overlap_count": timestamp_overlap_count,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4)
        }
    
    def _parse_timestamp(self, timestamp: str) -> int:
        """Convert timestamp string (HH:MM:SS) to seconds."""
        parts = timestamp.split(':')
        hours = int(parts[0]) if len(parts) > 2 else 0
        minutes = int(parts[-2]) if len(parts) > 1 else 0
        seconds = int(parts[-1])
        return hours * 3600 + minutes * 60 + seconds
    
    async def _calculate_hallucination_rate(
        self,
        generated_answer: str,
        generated_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Metric 4: Hallucination Rate
        
        Uses LLM to check if generated answer contains information
        not present in retrieved sources.
        
        Returns:
            Dict with:
            - hallucination_score: float (0-1, lower is better)
            - has_hallucination: bool
            - hallucination_examples: List[str]
        """
        # Combine all source texts
        source_texts = "\n\n".join([
            f"[{i+1}] {source.get('text', '')}"
            for i, source in enumerate(generated_sources)
        ])
        
        # LLM-based hallucination detection
        hallucination_prompt = f"""Kiểm tra xem câu trả lời có chứa thông tin KHÔNG có trong các nguồn được cung cấp không.

# Các nguồn tài liệu:
{source_texts}

# Câu trả lời được generate:
{generated_answer}

# Nhiệm vụ:
1. Tìm các thông tin trong câu trả lời KHÔNG xuất hiện trong nguồn
2. Đánh giá mức độ "hallucination" (bịa đặt thông tin)
3. Liệt kê các ví dụ cụ thể (nếu có)

# Output format (JSON):
{{
    "hallucination_score": <float 0-1, 0=no hallucination, 1=severe hallucination>,
    "has_hallucination": <bool>,
    "hallucination_examples": [<list of specific examples>]
}}

Chỉ trả về JSON, không giải thích thêm.
"""
        
        llm_response = await self.llm.generate_async(
            prompt=hallucination_prompt,
            system_prompt="You are an evaluation assistant. Return only valid JSON.",
            max_tokens=800
        )
        
        # Parse LLM response
        import json
        try:
            hallucination_eval = json.loads(llm_response.strip())
            hallucination_score = float(hallucination_eval.get("hallucination_score", 0.0))
            has_hallucination = hallucination_eval.get("has_hallucination", False)
            hallucination_examples = hallucination_eval.get("hallucination_examples", [])
        except:
            hallucination_score = 0.0
            has_hallucination = False
            hallucination_examples = []
        
        return {
            "hallucination_score": round(hallucination_score, 4),
            "has_hallucination": has_hallucination,
            "hallucination_examples": hallucination_examples
        }
