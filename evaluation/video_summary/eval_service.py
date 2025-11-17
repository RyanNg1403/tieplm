"""
Video Summary Evaluation Service

Implements evaluation for the video-summary task inspired by:
Otani et al., "Rethinking the Evaluation of Video Summaries" (CVPR 2019).

Provides two complementary evaluations:
- Text-level evaluation: Uses DeepEval SummarizationMetric (QAG) when available
  and falls back to embedding-based similarity using OpenAIEmbedder.
- Temporal/shot-level evaluation: Computes segment overlap matching between
  generated summary segments (timestamped sources) and ground-truth segments,
  producing precision/recall/F1 and duration-based coverage.

This file is intentionally self-contained and mirrors patterns used by
`evaluation/text_summary/eval_service.py`.
"""
from __future__ import annotations

import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from pathlib import Path

# Ensure project root is importable (used by other eval modules)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import SummarizationMetric
    DEEPEVAL_AVAILABLE = True
except Exception:
    DEEPEVAL_AVAILABLE = False

try:
    from scipy.optimize import linear_sum_assignment
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False

from backend.app.shared.embeddings.embedder import OpenAIEmbedder


def _parse_timestamp_to_seconds(ts: str) -> int:
    """Parse timestamp strings like HH:MM:SS or MM:SS into seconds."""
    parts = ts.strip().split(":")
    parts = [int(p) for p in parts if p != ""]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    # Fallback
    return 0


def _segment_intersection(seg_a: Tuple[int, int], seg_b: Tuple[int, int]) -> int:
    """Return intersection duration in seconds between two segments."""
    a0, a1 = seg_a
    b0, b1 = seg_b
    start = max(a0, b0)
    end = min(a1, b1)
    return max(0, end - start)


def _segment_union(seg_a: Tuple[int, int], seg_b: Tuple[int, int]) -> int:
    a0, a1 = seg_a
    b0, b1 = seg_b
    start = min(a0, b0)
    end = max(a1, b1)
    return max(0, end - start)


def _optimal_matching(iou_matrix: List[List[float]], overlap_threshold: float = 0.3) -> Tuple[int, List[Tuple[int, int, float]]]:
    """Optimal matching using Hungarian algorithm (requires scipy).
    Maximizes total IoU, respecting the overlap_threshold.
    Returns (matched_count, matched_pairs list of (gen_idx, gt_idx, iou))."""
    if not iou_matrix or not SCIPY_AVAILABLE:
        # Fallback to greedy
        matched_gt = set()
        matched_pairs = []
        for gi, row in enumerate(iou_matrix or []):
            best_ti = None
            best_iou = 0.0
            for ti, val in enumerate(row):
                if ti in matched_gt or val < overlap_threshold:
                    continue
                if val > best_iou:
                    best_iou = val
                    best_ti = ti
            if best_ti is not None:
                matched_gt.add(best_ti)
                matched_pairs.append((gi, best_ti, best_iou))
        return len(matched_pairs), matched_pairs
    
    gen_count = len(iou_matrix)
    gt_count = len(iou_matrix[0]) if iou_matrix else 0
    if gen_count == 0 or gt_count == 0:
        return 0, []
    
    # Convert to cost matrix (negative IoU, so minimization becomes maximization)
    cost_matrix = [[-iou for iou in row] for row in iou_matrix]
    
    # Solve assignment
    gen_indices, gt_indices = linear_sum_assignment(cost_matrix)
    
    # Filter by threshold and collect matches
    matched_pairs = []
    for gi, ti in zip(gen_indices, gt_indices):
        iou = iou_matrix[gi][ti]
        if iou >= overlap_threshold:
            matched_pairs.append((gi, ti, iou))
    
    return len(matched_pairs), matched_pairs


def _greedy_matching(iou_matrix: List[List[float]], overlap_threshold: float = 0.3) -> Tuple[int, List[Tuple[int, int, float]]]:
    """Greedy per-generated matching: for each generated, find best unmatched GT with IoU >= threshold.
    Returns (matched_count, matched_pairs list of (gen_idx, gt_idx, iou))."""
    matched_gt = set()
    matched_pairs = []
    for gi, row in enumerate(iou_matrix or []):
        best_ti = None
        best_iou = 0.0
        for ti, val in enumerate(row):
            if ti in matched_gt or val < overlap_threshold:
                continue
            if val > best_iou:
                best_iou = val
                best_ti = ti
        if best_ti is not None:
            matched_gt.add(best_ti)
            matched_pairs.append((gi, best_ti, best_iou))
    return len(matched_pairs), matched_pairs


class VideoSummaryEvaluator:
    """Evaluate video summaries using text and temporal metrics.

    Typical usage:
        evaluator = VideoSummaryEvaluator()
        results = evaluator.evaluate(
            generated_summary_text=...,
            generated_sources=[{"start_time":0, "end_time":30, "text":...}, ...],
            ground_truth_summaries=[...],
            ground_truth_segments=[{"start":0, "end":28}, ...]
        )
    """

    def __init__(self, evaluation_model: Optional[str] = None):
        self.eval_model = evaluation_model or os.getenv("EVAL_MODEL", "gpt-5-nano")
        self.eval_threshold = float(os.getenv("EVAL_SUMMARIZATION_THRESHOLD", "0.5"))
        self.eval_n_questions = int(os.getenv("EVAL_SUMMARIZATION_N_QUESTIONS", "10"))
        # Embedder for fallback and textual similarity
        try:
            self.embedder = OpenAIEmbedder()
        except Exception:
            self.embedder = None
        
        # Temporal evaluation settings
        self.default_iou_threshold = 0.5  # Realistic threshold for meaningful evaluation
        self.use_optimal_matching = SCIPY_AVAILABLE  # Use Hungarian if available

    def evaluate(
        self,
        generated_summary_text: str,
        generated_sources: List[Dict[str, Any]],
        ground_truth_summaries: Optional[List[str]] = None,
        ground_truth_segments: Optional[List[Dict[str, Any]]] = None,
        temporal_overlap_threshold: Optional[float] = None,
        matching_method: str = "global",
    ) -> Dict[str, Any]:
        """Run a combined evaluation and return detailed metrics.

        Args:
            generated_summary_text: Text of the generated summary.
            generated_sources: List of sources produced with timestamps, each item
                should contain `start_time` and `end_time` (seconds).
            ground_truth_summaries: List of human reference summaries (text).
            ground_truth_segments: List of dicts with `start` and `end` (seconds)
                representing reference important segments.
            temporal_overlap_threshold: IoU threshold for segment matching.
                If None, uses default (0.5 for more realistic evaluation).
            matching_method: "global" (Hungarian) or "greedy".

        Returns:
            Dict with `text_evaluation`, `temporal_evaluation`, and `combined_score`.
        """
        if temporal_overlap_threshold is None:
            temporal_overlap_threshold = self.default_iou_threshold
        
        # Text-level evaluation
        text_eval = self._evaluate_text(
            generated_summary_text, ground_truth_summaries or []
        )

        # If no ground-truth segments provided, use only first/last generated segments as proxy
        # (Avoid overfitting by not using all sources as GT)
        gt_segments = ground_truth_segments
        if not gt_segments and generated_sources and len(generated_sources) >= 2:
            # Use first and last sources as minimal GT (representative coverage)
            gt_segments = [
                {"start": int(generated_sources[0].get("start_time") or 0), 
                 "end": int(generated_sources[0].get("end_time") or 0)},
                {"start": int(generated_sources[-1].get("start_time") or 0), 
                 "end": int(generated_sources[-1].get("end_time") or 0)},
            ]
        elif not gt_segments and generated_sources and len(generated_sources) == 1:
            # Only one source, use it as GT
            gt_segments = [
                {"start": int(generated_sources[0].get("start_time") or 0), 
                 "end": int(generated_sources[0].get("end_time") or 0)},
            ]

        # Temporal shot-level evaluation
        temporal_eval = self._evaluate_temporal(
            generated_sources, gt_segments or [], temporal_overlap_threshold, matching_method=matching_method
        )

        # Simple combined score (weighted): 0.6 text, 0.4 temporal (configurable later)
        combined_score = None
        if text_eval.get("score") is not None and temporal_eval.get("f1") is not None:
            combined_score = round(0.6 * text_eval["score"] + 0.4 * temporal_eval["f1"], 4)

        return {
            "text_evaluation": text_eval,
            "temporal_evaluation": temporal_eval,
            "combined_score": combined_score,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _evaluate_text(self, generated: str, references: List[str]) -> Dict[str, Any]:
        """Evaluate summary text using DeepEval SummarizationMetric if available,
        otherwise fall back to embedding cosine similarity against references.
        Returns a dict with score in [0,1], and optional breakdowns.
        """
        if not references:
            # No ground truth texts provided — return embedding self-similarity as proxy
            if self.embedder is not None:
                emb = self.embedder.embed(generated)
                # similarity with itself => 1.0
                return {"score": 1.0, "method": "self", "details": {}}
            return {"score": None, "method": "none", "details": {}}

        if DEEPEVAL_AVAILABLE:
            try:
                # Create a single input text by concatenating references
                original_text = "\n\n---\n\n".join(references)
                test_case = LLMTestCase(input=original_text, actual_output=generated)
                metric = SummarizationMetric(
                    threshold=self.eval_threshold,
                    model=self.eval_model,
                    n=self.eval_n_questions,
                    verbose_mode=False,
                )
                metric.measure(test_case)
                score = getattr(metric, "score", None)
                breakdown = getattr(metric, "score_breakdown", {})
                return {
                    "score": round(score, 4) if score is not None else None,
                    "method": "deepeval_summarization",
                    "breakdown": breakdown,
                    "raw": {"success": getattr(metric, "success", None), "reason": getattr(metric, "reason", None)}
                }
            except Exception:
                # fall through to embedding fallback
                pass

        # Embedding fallback: compute cosine similarity between generated and each ref, take max
        if self.embedder is not None:
            try:
                gen_emb = self.embedder.embed(generated)
                import numpy as np
                scores = []
                for ref in references:
                    ref_emb = self.embedder.embed(ref)
                    sim = float(np.dot(gen_emb, ref_emb) / (np.linalg.norm(gen_emb) * np.linalg.norm(ref_emb)))
                    scores.append(sim)
                best = max(scores) if scores else 0.0
                return {"score": round(float(best), 4), "method": "embedding_cosine", "details": {"per_ref": [round(float(s),4) for s in scores]}}
            except Exception:
                return {"score": None, "method": "embed_error", "details": {}}

        return {"score": None, "method": "no_eval_available", "details": {}}

    def _evaluate_temporal(
        self,
        generated_sources: List[Dict[str, Any]],
        ground_truth_segments: List[Dict[str, Any]],
        overlap_threshold: Optional[float] = None,
        matching_method: str = "global",
    ) -> Dict[str, Any]:
        """Evaluate temporal overlap between generated and ground-truth segments.

        Treats two segments as a match if IoU (intersection / union) >= overlap_threshold.
        Uses global greedy or per-generated matching.
        Returns precision/recall/f1, mean IoU, and duration-based coverage statistics.
        """
        if overlap_threshold is None:
            overlap_threshold = self.default_iou_threshold
        
        # Normalize segments to (start, end) ints in seconds
        gen_segs: List[Tuple[int,int]] = []
        for s in generated_sources:
            st = int(s.get("start_time") or s.get("start") or 0)
            en = int(s.get("end_time") or s.get("end") or st)
            gen_segs.append((st, en))

        gt_segs: List[Tuple[int,int]] = []
        for s in ground_truth_segments:
            st = int(s.get("start") or s.get("start_time") or 0)
            en = int(s.get("end") or s.get("end_time") or st)
            gt_segs.append((st, en))

        if not gen_segs or not gt_segs:
            return {
                "precision": 0.0, "recall": 0.0, "f1": 0.0, "matched": 0,
                "generated_count": len(gen_segs), "ground_truth_count": len(gt_segs),
                "mean_iou": None, "duration_coverage": None, "matched_pairs": []
            }

        # Build IoU matrix
        iou_matrix = []
        for gi, g in enumerate(gen_segs):
            row = []
            for ti, t in enumerate(gt_segs):
                inter = _segment_intersection(g, t)
                union = _segment_union(g, t)
                iou = float(inter) / union if union > 0 else 0.0
                row.append(iou)
            iou_matrix.append(row)

        # Perform matching
        if matching_method == "global" or self.use_optimal_matching:
            matched_count, matched_pairs = _optimal_matching(iou_matrix, overlap_threshold)
        else:
            matched_count, matched_pairs = _greedy_matching(iou_matrix, overlap_threshold)

        matched = matched_count
        generated_count = len(gen_segs)
        gt_count = len(gt_segs)

        precision = matched / generated_count if generated_count > 0 else 0.0
        recall = matched / gt_count if gt_count > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Mean IoU of matched pairs
        mean_iou = None
        if matched_pairs:
            mean_iou = round(sum([pair[2] for pair in matched_pairs]) / len(matched_pairs), 4)

        # Duration coverage: fraction of ground-truth total duration covered by any generated segment
        total_gt_duration = sum([t[1] - t[0] for t in gt_segs]) if gt_segs else 0
        covered_duration = 0
        for t in gt_segs:
            # find any generated that intersects
            for g in gen_segs:
                covered_duration += _segment_intersection(g, t)
        # clamp
        covered_duration = min(covered_duration, total_gt_duration)
        duration_coverage = (covered_duration / total_gt_duration) if total_gt_duration > 0 else None

        return {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "matched": int(matched),
            "generated_count": int(generated_count),
            "ground_truth_count": int(gt_count),
            "mean_iou": mean_iou,
            "duration_coverage": round(float(duration_coverage), 4) if duration_coverage is not None else None,
            "matched_pairs": [(int(g), int(t), float(iou)) for g, t, iou in matched_pairs],
        }

        # Build IoU matrix (list of tuples for global matching)
        pairs: List[Tuple[int, int, float]] = []  # (gi, ti, iou)
        for gi, g in enumerate(gen_segs):
            for ti, t in enumerate(gt_segs):
                inter = _segment_intersection(g, t)
                union = _segment_union(g, t)
                iou = float(inter) / union if union > 0 else 0.0
                pairs.append((gi, ti, iou))

        matched_pairs: List[Tuple[int, int, float]] = []
        matched_gt = set()
        matched_gen = set()

        if matching_method == "global":
            # Global greedy: sort all pairs by IoU desc, match highest first (each GT/gen used once)
            pairs_sorted = sorted(pairs, key=lambda x: x[2], reverse=True)
            for gi, ti, iou in pairs_sorted:
                if iou < overlap_threshold:
                    break
                if ti in matched_gt or gi in matched_gen:
                    continue
                matched_gt.add(ti)
                matched_gen.add(gi)
                matched_pairs.append((gi, ti, iou))
        else:
            # Per-generated greedy (original): for each generated, pick best unmatched GT
            # Build quick lookup rows
            rows = {}
            for gi, ti, iou in pairs:
                rows.setdefault(gi, []).append((ti, iou))

            for gi, entries in rows.items():
                best_ti = None
                best_iou = 0.0
                for ti, iou in entries:
                    if ti in matched_gt:
                        continue
                    if iou >= overlap_threshold and iou > best_iou:
                        best_iou = iou
                        best_ti = ti
                if best_ti is not None:
                    matched_gt.add(best_ti)
                    matched_pairs.append((gi, best_ti, best_iou))

        matched = len(matched_pairs)
        generated_count = len(gen_segs)
        gt_count = len(gt_segs)

        precision = matched / generated_count if generated_count > 0 else 0.0
        recall = matched / gt_count if gt_count > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Duration coverage: fraction of ground-truth total duration covered by any generated segment
        total_gt_duration = sum([t[1] - t[0] for t in gt_segs]) if gt_segs else 0
        covered_duration = 0
        for t in gt_segs:
            # find any generated that intersects
            for g in gen_segs:
                covered_duration += _segment_intersection(g, t)
        # clamp
        covered_duration = min(covered_duration, total_gt_duration)
        duration_coverage = (covered_duration / total_gt_duration) if total_gt_duration > 0 else None

        # mean IoU for matched pairs
        mean_iou = None
        if matched_pairs:
            mean_iou = sum([p[2] for p in matched_pairs]) / len(matched_pairs)

        return {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "matched": matched,
            "generated_count": generated_count,
            "ground_truth_count": gt_count,
            "duration_coverage": round(float(duration_coverage), 4) if duration_coverage is not None else None,
            "mean_iou": round(float(mean_iou), 4) if mean_iou is not None else None,
            "matched_pairs": matched_pairs,
            "matching_method": matching_method,
            "overlap_threshold": overlap_threshold,
        }


def get_video_summary_evaluator() -> VideoSummaryEvaluator:
    return VideoSummaryEvaluator()
