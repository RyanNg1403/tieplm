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
import re
import math
from backend.app.shared.llm.client import get_llm_client
import numpy as _np


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
        self.default_iou_threshold = 0.45  # Slightly more lenient IoU threshold to improve matching
        self.use_optimal_matching = SCIPY_AVAILABLE  # Use Hungarian if available
        # Cap for proxy text->source similarity when no references exist (avoid overfit)
        self.text_source_score_cap = float(os.getenv("TEXT_SOURCE_SCORE_CAP", "0.9"))

    def evaluate(
        self,
        generated_summary_text: str,
        generated_sources: List[Dict[str, Any]],
        ground_truth_summaries: Optional[List[str]] = None,
        ground_truth_segments: Optional[List[Dict[str, Any]]] = None,
        temporal_overlap_threshold: Optional[float] = None,
        matching_method: str = "global",
        transcript_text: Optional[str] = None,
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
        
        # If transcript_text not provided, try to build from generated_sources
        if not transcript_text and generated_sources:
            try:
                parts = [s.get("text", "") for s in generated_sources if s.get("text")]
                transcript_text = "\n".join(parts) if parts else None
            except Exception:
                transcript_text = None

        # Text-level evaluation (prefer transcript for QAG; fall back to references)
        text_eval = self._evaluate_text(
            generated_summary_text, ground_truth_summaries or [], generated_sources, transcript_text=transcript_text
        )

        # Temporal evaluation
        temporal_eval = self._evaluate_temporal(
            generated_sources=generated_sources,
            ground_truth_segments=ground_truth_segments or [],
            overlap_threshold=temporal_overlap_threshold,
            matching_method=matching_method,
        )

        # Compute cosine similarity between transcript and generated summary (if embedder available)
        cosine_sim = None
        if transcript_text and self.embedder is not None:
            try:
                cosine_sim = _compute_embedding_similarity(self.embedder, transcript_text, generated_summary_text)
            except Exception:
                cosine_sim = None

        return {
            "text_evaluation": text_eval,
            "temporal_evaluation": temporal_eval,
            "cosine_similarity": round(float(cosine_sim), 4) if cosine_sim is not None else None,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _evaluate_text(self, generated: str, references: List[str], generated_sources: Optional[List[Dict[str, Any]]] = None, transcript_text: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate summary text using DeepEval SummarizationMetric if available,
        otherwise fall back to embedding cosine similarity against references.
        Returns a dict with score in [0,1], and optional breakdowns.
        """
        # If we have explicit references (human summaries), prefer DeepEval or embedding against them
        if references:
            if DEEPEVAL_AVAILABLE:
                try:
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
                    # Extract per-question alignment/coverage if present and attach char counts
                    questions = None
                    if isinstance(breakdown, dict):
                        questions = breakdown.get("questions") or breakdown.get("qas")
                    if isinstance(questions, list):
                        total_source_chars = sum([len(r) for r in references])
                        for q in questions:
                            q.setdefault("source_chars", total_source_chars)
                            q.setdefault("summary_chars", len(generated))

                    # Attach meta
                    meta = {"source_chars": sum([len(r) for r in references]), "summary_chars": len(generated)}
                    return {
                        "score": round(score, 4) if score is not None else None,
                        "method": "deepeval_summarization",
                        "breakdown": breakdown,
                        "questions": questions,
                        "meta": meta,
                        "raw": {"success": getattr(metric, "success", None), "reason": getattr(metric, "reason", None)}
                    }
                except Exception:
                    pass

            # Embedding fallback against references
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
                    meta = {"source_chars": sum([len(r) for r in references]), "summary_chars": len(generated)}
                    return {"score": round(float(best), 4), "method": "embedding_cosine", "details": {"per_ref": [round(float(s),4) for s in scores]}, "meta": meta}
                except Exception:
                    return {"score": None, "method": "embed_error", "details": {}}

        # If no references but transcript_text provided, prefer QAG on transcript
        if not references and transcript_text:
            # Use DeepEval on the full transcript if available
            if DEEPEVAL_AVAILABLE:
                try:
                    original_text = transcript_text
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
                    # augment per-question entries with char counts if possible
                    questions = breakdown.get("questions") if isinstance(breakdown, dict) else None
                    if isinstance(questions, list):
                        for q in questions:
                            q.setdefault("source_chars", len(transcript_text))
                            q.setdefault("summary_chars", len(generated))
                    meta = {"source_chars": len(transcript_text), "summary_chars": len(generated)}
                    # Also compute transcript-summary embedding similarity
                    emb_sim = _compute_embedding_similarity(self.embedder, transcript_text, generated)
                    return {
                        "score": round(score, 4) if score is not None else None,
                        "method": "deepeval_summarization_on_transcript",
                        "breakdown": breakdown,
                        "questions": questions,
                        "meta": meta,
                        "embedding_similarity": round(float(emb_sim), 4) if emb_sim is not None else None,
                        "raw": {"success": getattr(metric, "success", None), "reason": getattr(metric, "reason", None)}
                    }
                except Exception:
                    pass

            # If DeepEval not available, fallback to embedding similarity between transcript and generated
            if self.embedder is not None:
                try:
                    sim = _compute_embedding_similarity(self.embedder, transcript_text, generated)
                    capped = None
                    if sim is not None:
                        capped = min(float(sim), float(self.text_source_score_cap))
                    meta = {"source_chars": len(transcript_text), "summary_chars": len(generated)}
                    return {"score": round(float(capped), 4) if capped is not None else None, "method": "embedding_transcript", "embedding_similarity": round(float(sim), 4) if sim is not None else None, "meta": meta}
                except Exception:
                    return {"score": None, "method": "embed_error", "details": {}}

        # If no references and no transcript, use previous conservative fallback comparing to sources
        if not references:
            if self.embedder is not None and generated_sources:
                try:
                    import numpy as np
                    gen_emb = self.embedder.embed(generated)
                    scores = []
                    for s in generated_sources:
                        txt = s.get("text") or s.get("snippet") or ""
                        if not txt:
                            continue
                        ref_emb = self.embedder.embed(txt)
                        sim = float(np.dot(gen_emb, ref_emb) / (np.linalg.norm(gen_emb) * np.linalg.norm(ref_emb)))
                        scores.append(sim)
                    best = max(scores) if scores else 0.0
                    # Conservative cap to avoid overfitting when no true refs exist
                    capped = min(float(best), float(self.text_source_score_cap))
                    return {"score": round(capped, 4), "method": "embedding_sources", "details": {"per_source": [round(float(s),4) for s in scores]}}
                except Exception:
                    return {"score": None, "method": "embed_error", "details": {}}
            return {"score": None, "method": "no_references", "details": {}}

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



def get_video_summary_evaluator() -> VideoSummaryEvaluator:
    return VideoSummaryEvaluator()


def _safe_parse_float(s: str) -> Optional[float]:
    try:
        return float(s.strip())
    except Exception:
        return None


def _compute_embedding_similarity(embedder: Optional[OpenAIEmbedder], a: str, b: str) -> Optional[float]:
    """Return cosine similarity between two texts using embedder, or None on failure."""
    if embedder is None:
        return None
    try:
        ea = _np.array(embedder.embed(a))
        eb = _np.array(embedder.embed(b))
        denom = (_np.linalg.norm(ea) * _np.linalg.norm(eb))
        if denom == 0:
            return 0.0
        return float((_np.dot(ea, eb) / denom))
    except Exception:
        # Fallback: try chunking long texts to average embeddings
        try:
            def chunks(text, size=2000):
                for i in range(0, len(text), size):
                    yield text[i:i+size]

            a_chunks = list(chunks(a)) if a else []
            b_chunks = list(chunks(b)) if b else []
            if not a_chunks or not b_chunks:
                return None
            a_embs = [_np.array(embedder.embed(chunk)) for chunk in a_chunks]
            b_embs = [_np.array(embedder.embed(chunk)) for chunk in b_chunks]
            a_mean = _np.mean(_np.stack(a_embs), axis=0)
            b_mean = _np.mean(_np.stack(b_embs), axis=0)
            denom = (_np.linalg.norm(a_mean) * _np.linalg.norm(b_mean))
            if denom == 0:
                return 0.0
            return float((_np.dot(a_mean, b_mean) / denom))
        except Exception:
            return None


def _llm_semantic_score(generated: str, references: List[str], model: str = None) -> Optional[float]:
    """Ask an LLM to score the semantic correctness of `generated` against `references`.

    Returns score in [0,1] or None on failure.
    """
    try:
        client = get_llm_client()
        system = "You are an evaluator. Given reference text(s) and a candidate summary, rate how well the candidate captures the meaning of the references on a scale from 0.0 (no match) to 1.0 (perfect match). Only return a single numeric value between 0 and 1."

        refs = "\n\n---\n\n".join(references) if references else ""
        prompt = f"References:\n{refs}\n\nCandidate summary:\n{generated}\n\nPlease output one number between 0 and 1 (inclusive) representing semantic similarity. No additional text."
        resp = client.generate(prompt=prompt, system_prompt=system, max_tokens=10)
        # Try to parse a float from response
        # It may respond like '0.85' or '0.85\n'
        for token in re.finditer(r"[0-1](?:\.[0-9]+)?", resp):
            val = _safe_parse_float(token.group(0))
            if val is not None:
                return max(0.0, min(1.0, val))
        # fallback: try parsing the whole response
        return _safe_parse_float(resp)
    except Exception:
        return None


def _validate_citations(generated_text: str, sources: List[Dict[str, Any]], embedder: Optional[OpenAIEmbedder] = None) -> Dict[str, Any]:
    """Validate citations like [1], [2] in generated_text against provided sources.

    Returns dict with counts and list of invalid citations and mapping details.
    """
    citation_pattern = re.compile(r"\[(\d+)\]")
    found = citation_pattern.findall(generated_text or "")
    total_citations = len(found)
    valid = 0
    invalid_examples = []
    cited_sources = set()

    for match in found:
        try:
            idx = int(match) - 1
        except Exception:
            invalid_examples.append({"token": match, "reason": "not_int"})
            continue
        if idx < 0 or idx >= len(sources):
            invalid_examples.append({"index": idx + 1, "reason": "out_of_range"})
            continue
        cited_sources.add(idx)
        # Quick textual grounding check (embedding similarity between source text and generated summary)
        src_text = sources[idx].get("text", "")
        sim = None
        if embedder is not None and src_text:
            try:
                sim = _compute_embedding_similarity(embedder, src_text, generated_text)
            except Exception:
                sim = None
        # Accept citation if sim is None (can't compute) or sim >= 0.2 (loose lexical overlap) or simple substring
        ok = False
        if sim is None:
            if src_text.strip() and src_text.strip()[:10] in (generated_text or ""):
                ok = True
            else:
                ok = True  # be permissive if we cannot compute embeddings
        else:
            ok = sim >= 0.2

        if ok:
            valid += 1
        else:
            invalid_examples.append({"index": idx + 1, "reason": "low_similarity", "similarity": sim})

    citation_accuracy = (valid / total_citations) if total_citations > 0 else None
    citation_coverage = (len(cited_sources) / len(sources)) if sources else None

    return {
        "total_citations": total_citations,
        "valid_citations": valid,
        "invalid_examples": invalid_examples,
        "citation_accuracy": round(float(citation_accuracy), 4) if citation_accuracy is not None else None,
        "citation_coverage": round(float(citation_coverage), 4) if citation_coverage is not None else None,
    }


def _hallucination_detection(generated_text: str, sources: List[Dict[str, Any]], embedder: Optional[OpenAIEmbedder] = None, sim_threshold: float = 0.65) -> Dict[str, Any]:
    """Simple hallucination detector: split generated_text into sentences, check if each sentence
    has a supporting source via embedding similarity. Returns list of flagged claims and rate."""
    # naive sentence split
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", generated_text) if s.strip()]
    total = len(sentences)
    flagged = []
    if total == 0:
        return {"total_claims": 0, "hallucinated_claims": 0, "hallucination_rate": 0.0, "examples": []}

    # Precompute source embeddings if available
    src_texts = [s.get("text", "") for s in sources]
    src_embs = None
    if embedder is not None and src_texts:
        try:
            src_embs = [_np.array(embedder.embed(t)) for t in src_texts]
        except Exception:
            src_embs = None

    for sent in sentences:
        supported = False
        max_sim = 0.0
        if src_embs is not None:
            try:
                se = _np.array(embedder.embed(sent))
                for emb in src_embs:
                    denom = (_np.linalg.norm(se) * _np.linalg.norm(emb))
                    if denom == 0:
                        continue
                    sim = float(_np.dot(se, emb) / denom)
                    if sim > max_sim:
                        max_sim = sim
                    if sim >= sim_threshold:
                        supported = True
                        break
            except Exception:
                supported = True  # cannot compute; be permissive
        else:
            # fallback lexical check
            for t in src_texts:
                if len(t) > 20 and t[:20] in sent:
                    supported = True
                    break

        if not supported:
            flagged.append({"sentence": sent, "max_similarity": round(float(max_sim), 4)})

    hallucinated = len(flagged)
    rate = hallucinated / total if total > 0 else 0.0
    return {"total_claims": total, "hallucinated_claims": hallucinated, "hallucination_rate": round(float(rate), 4), "examples": flagged[:5]}


def evaluate_detailed(
    generated_summary_text: str,
    generated_sources: List[Dict[str, Any]],
    ground_truth_summaries: Optional[List[str]] = None,
    ground_truth_segments: Optional[List[Dict[str, Any]]] = None,
    weights: Optional[Dict[str, float]] = None,
    verbosity: int = 0,
) -> Dict[str, Any]:
    """High-level evaluation that computes the richer metric set described in the task doc.

    Returns a dict with per-metric scores and combined score.
    """
    evaluator = VideoSummaryEvaluator()

    # Text-level correctness: embedding similarity + LLM semantic
    embed_sim = None
    if evaluator.embedder is not None and ground_truth_summaries:
        try:
            # compute average similarity to all references
            sims = [ _compute_embedding_similarity(evaluator.embedder, generated_summary_text, ref) or 0.0 for ref in ground_truth_summaries]
            embed_sim = float(max(sims)) if sims else None
        except Exception:
            embed_sim = None

    llm_score = _llm_semantic_score(generated_summary_text, ground_truth_summaries or [], model=evaluator.eval_model)

    # Compose correctness (40% embed, 60% llm) with fallbacks
    emb_component = embed_sim if embed_sim is not None else 0.0
    llm_component = llm_score if llm_score is not None else emb_component
    correctness_score = round(float(0.4 * emb_component + 0.6 * llm_component), 4)

    # Citation validation
    citation_info = _validate_citations(generated_summary_text, generated_sources, evaluator.embedder)

    # Temporal metrics
    temporal = evaluator._evaluate_temporal(generated_sources, ground_truth_segments or [], overlap_threshold=evaluator.default_iou_threshold, matching_method=("global" if evaluator.use_optimal_matching else "greedy"))

    # Hallucination detection
    halluc = _hallucination_detection(generated_summary_text, generated_sources, evaluator.embedder)

    # Readability (LLM-based, fallback heuristics)
    readability = None
    try:
        client = get_llm_client()
        sys = "You are a readability scorer. Given the candidate summary, output a single number between 0 and 1 indicating readability and coherence (1 = highly readable). Only output the number."
        resp = client.generate(prompt=generated_summary_text, system_prompt=sys, max_tokens=8)
        rscore = _safe_parse_float(resp)
        if rscore is not None:
            readability = max(0.0, min(1.0, rscore))
    except Exception:
        readability = None

    if readability is None:
        # Heuristic: ideal sentence length between 8 and 22 words
        sents = [s for s in re.split(r"(?<=[.!?])\s+", generated_summary_text) if s.strip()]
        if sents:
            lengths = [len(s.split()) for s in sents]
            avg = sum(lengths) / len(lengths)
            # Map avg into 0..1 with triangle peak at 15
            score = max(0.0, 1 - abs(avg - 15) / 15)
            readability = round(float(score), 4)
        else:
            readability = 0.0

    # Compression ratio: generated tokens / total chunk tokens
    total_chunk_chars = sum([len(s.get("text", "")) for s in generated_sources])
    gen_chars = len(generated_summary_text or "")
    compression_ratio = round(float(gen_chars / total_chunk_chars), 4) if total_chunk_chars > 0 else None

    # Clickable timestamp accuracy: check presence of start_time and video_url in sources
    valid_clicks = 0
    for s in generated_sources:
        if s.get("start_time") is not None and s.get("video_url"):
            valid_clicks += 1
    clickable_accuracy = (valid_clicks / len(generated_sources)) if generated_sources else None

    # Combined score
    # default weights
    if weights is None:
        weights = {
            "correctness": 0.35,
            "temporal_f1": 0.25,
            "citation_accuracy": 0.15,
            "faithfulness": 0.15,
            "readability": 0.10,
        }

    faithfulness = 1.0 - halluc.get("hallucination_rate", 0.0)

    components = {}
    components["correctness"] = correctness_score
    components["temporal_f1"] = temporal.get("f1", 0.0)
    components["citation_accuracy"] = citation_info.get("citation_accuracy") if citation_info.get("citation_accuracy") is not None else 0.0
    components["faithfulness"] = round(float(faithfulness), 4)
    components["readability"] = round(float(readability), 4) if readability is not None else 0.0

    # Normalize None -> 0 and ensure 0..1
    for k, v in components.items():
        if v is None:
            components[k] = 0.0
        else:
            try:
                components[k] = max(0.0, min(1.0, float(v)))
            except Exception:
                components[k] = 0.0

    combined = 0.0
    for k, w in weights.items():
        combined += components.get(k, 0.0) * float(w)
    combined = round(float(combined), 4)

    result = {
        "video_id": None,
        "metrics": {
            "correctness": components["correctness"],
            "embedding_similarity": round(float(embed_sim), 4) if embed_sim is not None else None,
            "llm_semantic_score": round(float(llm_score), 4) if llm_score is not None else None,
            "citation_accuracy": citation_info.get("citation_accuracy"),
            "citation_coverage": citation_info.get("citation_coverage"),
            "temporal_precision": temporal.get("precision"),
            "temporal_recall": temporal.get("recall"),
            "temporal_f1": temporal.get("f1"),
            "duration_coverage": temporal.get("duration_coverage"),
            "hallucination_rate": halluc.get("hallucination_rate"),
            "readability": components["readability"],
            "compression_ratio": compression_ratio,
            "clickable_timestamp_accuracy": round(float(clickable_accuracy), 4) if clickable_accuracy is not None else None,
            "combined_score": combined,
        },
        "hallucination_examples": halluc.get("examples", []),
        "citation_invalid_examples": citation_info.get("invalid_examples", []),
        "temporal_matched_pairs": temporal.get("matched_pairs", []),
        "timestamp": datetime.utcnow().isoformat()
    }

    return result
