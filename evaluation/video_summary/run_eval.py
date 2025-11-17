"""
Video Summary Evaluation Runner

Evaluates generated video summaries found in `ingestion/video_summaries/video_summaries.json`
using the `VideoSummaryEvaluator` implemented in `eval_service.py`.

Saves results under `evaluation/video_summary/results/run_<timestamp>/`.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path so relative imports work
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

from eval_service import get_video_summary_evaluator


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
    stats = {"total": 0, "success": 0, "f1_sum": 0.0, "recall_sum": 0.0, "precision_sum": 0.0}
    
    for i, item in enumerate(summaries, 1):
        vid = item.get('video_id') or f"unknown_{i}"

        gen_text = item.get('summary', '')
        gen_sources = item.get('sources', [])

        try:
            eval_result = evaluator.evaluate(
                generated_summary_text=gen_text,
                generated_sources=gen_sources,
                ground_truth_summaries=item.get('ground_truth_summaries', []),
                ground_truth_segments=item.get('ground_truth_segments', []),
                temporal_overlap_threshold=args.overlap_threshold,
                matching_method=args.matching_method
            )

            entry = {
                "video_id": vid,
                "generation": {
                    "summary": gen_text[:100] + "..." if len(gen_text) > 100 else gen_text,
                    "summary_chars": len(gen_text),
                    "sources_count": len(gen_sources)
                },
                "evaluation": eval_result
            }
            
            # Track stats
            temporal = eval_result.get('temporal_evaluation', {})
            f1 = temporal.get('f1')
            recall = temporal.get('recall')
            precision = temporal.get('precision')
            
            stats["total"] += 1
            if f1 is not None and f1 > 0:
                stats["success"] += 1
                stats["f1_sum"] += f1
                stats["recall_sum"] += recall
                stats["precision_sum"] += precision
            
            print(f"[{i:2d}/{len(summaries)}] {vid:40s} | P:{precision:5.3f} R:{recall:5.3f} F1:{f1:5.3f}")

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
    if stats["success"] > 0:
        avg_f1 = stats["f1_sum"] / stats["success"]
        avg_recall = stats["recall_sum"] / stats["success"]
        avg_precision = stats["precision_sum"] / stats["success"]
        print(f"✅ {stats['success']} summaries with F1 > 0")
        print(f"   Average F1: {avg_f1:.4f}")
        print(f"   Average Precision: {avg_precision:.4f}")
        print(f"   Average Recall: {avg_recall:.4f}")
    else:
        print("⚠️  No summaries with F1 > 0")
    print(f"Results saved to: {run_dir}")
    print(f"{'='*80}")

    with open(ingestion_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    summaries = data.get('summaries', [])
    if args.limit:
        summaries = summaries[: args.limit]

    print(f"Found {len(summaries)} generated summaries to evaluate")

    # Prepare results dir
    results_base = script_dir / args.results_dir
    run_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir = results_base / f"run_{run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    evaluator = get_video_summary_evaluator()

    results = []
    for i, item in enumerate(summaries, 1):
        vid = item.get('video_id') or f"unknown_{i}"
        print(f"\n[{i}/{len(summaries)}] Evaluating video: {vid}")

        gen_text = item.get('summary', '')
        gen_sources = item.get('sources', [])

        try:
            eval_result = evaluator.evaluate(
                generated_summary_text=gen_text,
                generated_sources=gen_sources,
                ground_truth_summaries=item.get('ground_truth_summaries', []),
                ground_truth_segments=item.get('ground_truth_segments', []),
                temporal_overlap_threshold=args.overlap_threshold,
                # internal param is named 'matching_method'
                # evaluator will accept it to choose matching strategy
                **{"matching_method": args.matching_method}
            )

            entry = {
                "video_id": vid,
                "generation": {
                    "summary": gen_text,
                    "summary_chars": len(gen_text),
                    "sources_count": len(gen_sources)
                },
                "evaluation": eval_result
            }

        except Exception as e:
            entry = {
                "video_id": vid,
                "error": str(e)
            }

        results.append(entry)

        # Save incremental results
        out_file = run_dir / "evaluations.json"
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({"run_id": f"run_{run_timestamp}", "results": results}, f, indent=2, ensure_ascii=False)

    print(f"\nEvaluation finished. Results saved to: {run_dir}")


if __name__ == '__main__':
    main()
