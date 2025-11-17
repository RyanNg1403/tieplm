"""
Video Summary Evaluation Runner

Evaluates generated video summaries found in `ingestion/video_summaries/video_summaries.json`
using the `VideoSummaryEvaluator` implemented in `eval_service.py`.

Saves results under `evaluation/video_summary/results/run_<timestamp>/`.
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# Add project root to path so relative imports work
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

from evaluation.video_summary.eval_service import get_video_summary_evaluator


def main():
    parser = argparse.ArgumentParser(description="Video Summary Evaluation Runner")
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of summaries to evaluate')
    parser.add_argument('--overlap-threshold', type=float, default=0.5, help='IoU threshold for matching (default 0.5 for realistic evaluation)')
    parser.add_argument('--matching-method', type=str, default='global', choices=['global', 'greedy'], help='Matching method to use')
    parser.add_argument('--results-dir', type=str, default='results', help='Directory under evaluation/video_summary to save runs')

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    ingestion_file = project_root / "ingestion" / "video_summaries" / "video_summaries.json"
    if not ingestion_file.exists():
        print(f"Error: expected ingestion file not found: {ingestion_file}")
        return

    with open(ingestion_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    summaries = data.get('summaries', [])
    if args.limit:
        summaries = summaries[:args.limit]
    
    print(f"📊 Evaluating {len(summaries)} summaries (threshold={args.overlap_threshold}, method={args.matching_method})\n")

    # Prepare results dir
    results_base = script_dir / args.results_dir
    run_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir = results_base / f"run_{run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    evaluator = get_video_summary_evaluator()

    results = []
    stats = {"total": 0, "success": 0, "qag_sum": 0.0, "cosine_sum": 0.0, "alignment_sum": 0.0, "coverage_sum": 0.0, "temporal_f1_sum": 0.0}
    
    for i, item in enumerate(summaries, 1):
        vid = item.get('video_id') or f"unknown_{i}"

        gen_text = item.get('summary', '')
        gen_sources = item.get('sources', [])

        try:
            # Build transcript_text from sources by concatenating their text fields
            transcript_text = None
            try:
                parts = [s.get('text', '') for s in gen_sources if s.get('text')]
                transcript_text = "\n".join(parts) if parts else None
            except Exception:
                transcript_text = None

            eval_result = evaluator.evaluate(
                generated_summary_text=gen_text,
                generated_sources=gen_sources,
                ground_truth_summaries=item.get('ground_truth_summaries', []),
                ground_truth_segments=item.get('ground_truth_segments', []),
                temporal_overlap_threshold=args.overlap_threshold,
                matching_method=args.matching_method,
                transcript_text=transcript_text,
            )

            # Track stats for QAG, cosine, alignment, and coverage
            qag_score = None
            avg_alignment = None
            avg_coverage = None
            temporal_f1 = None

            if eval_result.get('text_evaluation'):
                text_eval = eval_result['text_evaluation']
                qag_score = text_eval.get('score')
                
                # Extract alignment and coverage from deepeval breakdown
                questions = text_eval.get('questions', [])
                if questions:
                    alignments = [q['alignment'] for q in questions if 'alignment' in q]
                    coverages = [q['coverage'] for q in questions if 'coverage' in q]
                    if alignments:
                        avg_alignment = np.mean(alignments)
                        stats["alignment_sum"] += avg_alignment
                    if coverages:
                        avg_coverage = np.mean(coverages)
                        stats["coverage_sum"] += avg_coverage

            if eval_result.get('temporal_evaluation'):
                temporal_f1 = eval_result['temporal_evaluation'].get('f1')


            cosine = eval_result.get('cosine_similarity')

            entry = {
                "video_id": vid,
                "generation": {
                    "summary": gen_text[:100] + "..." if len(gen_text) > 100 else gen_text,
                    "summary_chars": len(gen_text),
                    "sources_count": len(gen_sources)
                },
                "evaluation": eval_result,
                "scores": {
                    "qag": qag_score,
                    "cosine_similarity": cosine,
                    "alignment": avg_alignment,
                    "coverage": avg_coverage,
                    "temporal_f1": temporal_f1
                }
            }

            stats["total"] += 1
            if qag_score is not None:
                stats["qag_sum"] += qag_score
            if cosine is not None:
                stats["cosine_sum"] += cosine
            if temporal_f1 is not None:
                stats["temporal_f1_sum"] += temporal_f1

            print(f"[{i:2d}/{len(summaries)}] {vid:40s} | QAG:{(qag_score or 0):5.3f} COS:{(cosine or 0):5.3f} ALN:{(avg_alignment or 0):5.3f} COV:{(avg_coverage or 0):5.3f} F1:{(temporal_f1 or 0):5.3f}")

        except Exception as e:
            print(f"[{i:2d}/{len(summaries)}] {vid:40s} | ❌ {str(e)[:50]}")
            entry = {
                "video_id": vid,
                "error": str(e)
            }

        results.append(entry)

        # Save incremental results
        out_file = run_dir / "evaluations.json"
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({
                "run_id": f"run_{run_timestamp}",
                "config": {
                    "threshold": args.overlap_threshold,
                    "matching_method": args.matching_method,
                    "limit": args.limit
                },
                "stats": stats,
                "results": results
            }, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*80}")
    total = stats["total"] if stats["total"] > 0 else 1
    avg_qag = stats["qag_sum"] / total
    avg_cos = stats["cosine_sum"] / total
    avg_aln = stats["alignment_sum"] / total
    avg_cov = stats["coverage_sum"] / total
    avg_f1 = stats["temporal_f1_sum"] / total
    
    print(f"✅ Evaluated {stats['total']} summaries")
    print(f"   Average QAG: {avg_qag:.4f}")
    print(f"   Average Cosine: {avg_cos:.4f}")
    print(f"   Average Alignment: {avg_aln:.4f}")
    print(f"   Average Coverage: {avg_cov:.4f}")
    print(f"   Average Temporal F1: {avg_f1:.4f}")
    print(f"Results saved to: {run_dir}")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
