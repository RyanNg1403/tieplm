"""
Video Summary Evaluation Service using DeepEval with QAG metrics.

This service evaluates video summaries based on:
1. Coverage Score: How much detail from the transcript is included
2. Alignment Score: Factual alignment between transcript and summary
3. Cosine Similarity: Semantic similarity using OpenAI embeddings
4. Character Counts: Source and summary lengths for compression analysis
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env if not already loaded
env_path = project_root / ".env"
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(dotenv_path=env_path)

from deepeval.test_case import LLMTestCase
from deepeval.metrics import SummarizationMetric

from backend.app.shared.embeddings.embedder import OpenAIEmbedder
import numpy as np


class VideoSummaryEvaluator:
    """
    Evaluates video summarization using DeepEval's QAG-based metrics and cosine similarity.

    QAG (Question-Answer Generation) Framework:
    - Generates closed-ended questions from the video transcript
    - Measures coverage (detail inclusion) and alignment (factual accuracy)
    - Uses 15 questions (more than text summary due to longer transcripts)
    """

    def __init__(
        self,
        evaluation_model: Optional[str] = None,
        n_questions: int = 15
    ):
        """
        Initialize evaluator.

        Args:
            evaluation_model: Model to use for evaluation (default: from env)
            n_questions: Number of QAG questions to generate (default: 15)
        """
        # Load evaluation configuration
        self.eval_model = evaluation_model or os.getenv("EVAL_MODEL", "gpt-5-nano")
        self.eval_threshold = float(os.getenv("EVAL_SUMMARIZATION_THRESHOLD", "0.5"))
        self.eval_n_questions = n_questions

        # Initialize OpenAI embedder for cosine similarity
        try:
            self.embedder = OpenAIEmbedder()
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize OpenAI embedder: {e}")
            self.embedder = None

    def evaluate_summary(
        self,
        video_id: str,
        summary: str,
        transcript: str,
        assessment_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a video summary using QAG and cosine similarity.

        Args:
            video_id: Unique identifier for the video
            summary: Generated summary to evaluate
            transcript: Full video transcript (original text)
            assessment_questions: Optional pre-defined questions for coverage

        Returns:
            Evaluation results with scores and metrics
        """
        print(f"📊 Evaluating video summary for: {video_id}")

        # Character counts
        source_chars = len(transcript)
        summary_chars = len(summary)
        compression_ratio = summary_chars / source_chars if source_chars > 0 else 0

        print(f"   Source: {source_chars:,} chars | Summary: {summary_chars:,} chars | Ratio: {compression_ratio:.2%}")

        # Create test case for QAG evaluation
        test_case = LLMTestCase(
            input=transcript,
            actual_output=summary
        )

        # Create summarization metric with QAG (15 questions for video transcripts)
        print(f"   Running QAG evaluation with {self.eval_n_questions} questions...")
        metric = SummarizationMetric(
            threshold=self.eval_threshold,
            model=self.eval_model,
            n=self.eval_n_questions,
            assessment_questions=assessment_questions,
            verbose_mode=True
        )

        # Evaluate
        metric.measure(test_case)

        # Get score breakdown (coverage and alignment scores)
        score_breakdown = getattr(metric, 'score_breakdown', {})

        # Compute cosine similarity between transcript and summary
        cosine_sim = None
        if self.embedder is not None:
            print(f"   Computing cosine similarity...")
            cosine_sim = self._compute_cosine_similarity(transcript, summary)

        return {
            "video_id": video_id,
            "qag_score": metric.score,
            "qag_success": metric.success,
            "qag_reason": metric.reason,
            "coverage_score": score_breakdown.get('Coverage', None),
            "alignment_score": score_breakdown.get('Alignment', None),
            "cosine_similarity": round(float(cosine_sim), 4) if cosine_sim is not None else None,
            "source_chars": source_chars,
            "summary_chars": summary_chars,
            "compression_ratio": round(compression_ratio, 4),
            "threshold": self.eval_threshold,
            "n_questions": self.eval_n_questions,
            "evaluation_model": self.eval_model,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _compute_cosine_similarity(self, transcript: str, summary: str) -> Optional[float]:
        """
        Compute cosine similarity between transcript and summary using OpenAI embeddings.

        Args:
            transcript: Full video transcript
            summary: Generated summary

        Returns:
            Cosine similarity score in [0, 1] or None on failure
        """
        if self.embedder is None:
            return None

        try:
            # For long transcripts, chunk and average embeddings
            transcript_emb = self._embed_text(transcript)
            summary_emb = self._embed_text(summary)

            if transcript_emb is None or summary_emb is None:
                return None

            # Compute cosine similarity
            dot_product = np.dot(transcript_emb, summary_emb)
            norm_product = np.linalg.norm(transcript_emb) * np.linalg.norm(summary_emb)

            if norm_product == 0:
                return 0.0

            return float(dot_product / norm_product)

        except Exception as e:
            print(f"⚠️  Error computing cosine similarity: {e}")
            return None

    def _embed_text(self, text: str, chunk_size: int = 8000) -> Optional[np.ndarray]:
        """
        Embed text, chunking if necessary for long texts.

        Args:
            text: Text to embed
            chunk_size: Maximum characters per chunk

        Returns:
            Averaged embedding vector or None on failure
        """
        if not text or self.embedder is None:
            return None

        try:
            # If text is short enough, embed directly
            if len(text) <= chunk_size:
                return np.array(self.embedder.embed(text))

            # Otherwise, chunk and average embeddings
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            embeddings = [np.array(self.embedder.embed(chunk)) for chunk in chunks]

            # Return average embedding
            return np.mean(embeddings, axis=0)

        except Exception as e:
            print(f"⚠️  Error embedding text: {e}")
            return None


def load_transcript(video_id: str, transcripts_dir: Path) -> Optional[str]:
    """
    Load transcript for a video from JSON file.

    Args:
        video_id: Video identifier
        transcripts_dir: Directory containing transcript JSON files

    Returns:
        Full transcript text or None if not found
    """
    # Try to find transcript file matching video_id
    transcript_files = list(transcripts_dir.glob("*.json"))

    for transcript_file in transcript_files:
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if this is the right video by comparing filename or video_id
            if video_id in transcript_file.name or transcript_file.stem == video_id:
                return data.get('text', '')

        except Exception as e:
            print(f"⚠️  Error loading {transcript_file}: {e}")
            continue

    return None


def get_video_summary_evaluator(n_questions: int = 15) -> VideoSummaryEvaluator:
    """Get evaluator instance with specified number of questions."""
    return VideoSummaryEvaluator(n_questions=n_questions)
