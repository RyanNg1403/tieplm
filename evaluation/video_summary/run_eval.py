"""
Video Summary Evaluation Runner

Evaluates video summaries stored in the database using QAG metrics and cosine similarity.
Loads transcripts from ingestion/transcripts/*.json files.

Saves results under `evaluation/video_summary/results/run_<timestamp>/`.
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
# Add project root to path so relative imports work
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / ".env")

from evaluation.video_summary.eval_service import get_video_summary_evaluator, load_transcript
from backend.app.shared.database.postgres import get_postgres_client
from backend.app.shared.database.models import VideoSummary, Video


def main():
    parser = argparse.ArgumentParser(description="Video Summary Evaluation Runner")
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of summaries to evaluate')
    parser.add_argument('--n-questions', type=int, default=15, help='Number of QAG questions (default: 15)')
    parser.add_argument('--results-dir', type=str, default='results', help='Directory under evaluation/video_summary to save runs')

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    transcripts_dir = project_root / "ingestion" / "transcripts"

    if not transcripts_dir.exists():
        print(f"❌ Error: Transcripts directory not found: {transcripts_dir}")
        return

    print(f"📊 Loading video summaries from database...\n")

    # Connect to database
    postgres_client = get_postgres_client()
    db = postgres_client.get_session()

    try:
        # Load all video summaries from database
        query = db.query(VideoSummary).join(Video)

        if args.limit:
            query = query.limit(args.limit)

        summaries = query.all()

        print(f"   Found {len(summaries)} video summaries to evaluate")
        print(f"   Using {args.n_questions} QAG questions per summary\n")

        # Prepare results dir
        results_base = script_dir / args.results_dir
        run_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = results_base / f"run_{run_timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Initialize evaluator
        evaluator = get_video_summary_evaluator(n_questions=args.n_questions)

        results = []
        stats = {
            "total": 0,
            "success": 0,
            "qag_sum": 0.0,
            "cosine_sum": 0.0,
            "alignment_sum": 0.0,
            "coverage_sum": 0.0
        }

        for i, summary_obj in enumerate(summaries, 1):
            video_id = summary_obj.video_id
            summary_text = summary_obj.summary

            try:
                # Get the video object to access transcript_path
                video = db.query(Video).filter(Video.id == video_id).first()

                if not video or not video.transcript_path:
                    print(f"[{i:2d}/{len(summaries)}] {video_id:40s} | ⚠️  No transcript path in database, skipping...")
                    continue

                # Load transcript from the path specified in database
                # transcript_path is relative like "transcripts/[CS431 - Chương 7]..."
                # We need to prepend "ingestion/" to make it "ingestion/transcripts/..."
                transcript_file = project_root / "ingestion" / video.transcript_path

                if not transcript_file.exists():
                    print(f"[{i:2d}/{len(summaries)}] {video_id:40s} | ⚠️  Transcript file not found: {transcript_file}")
                    continue

                with open(transcript_file, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    transcript = transcript_data.get('text', '')

                if not transcript:
                    print(f"[{i:2d}/{len(summaries)}] {video_id:40s} | ⚠️  Empty transcript, skipping...")
                    continue

                # Evaluate summary
                eval_result = evaluator.evaluate_summary(
                    video_id=video_id,
                    summary=summary_text,
                    transcript=transcript
                )

                # Extract scores
                qag_score = eval_result.get('qag_score')
                alignment_score = eval_result.get('alignment_score')
                coverage_score = eval_result.get('coverage_score')
                cosine_sim = eval_result.get('cosine_similarity')

                # Track statistics
                stats["total"] += 1
                if qag_score is not None:
                    stats["qag_sum"] += qag_score
                    stats["success"] += 1
                if alignment_score is not None:
                    stats["alignment_sum"] += alignment_score
                if coverage_score is not None:
                    stats["coverage_sum"] += coverage_score
                if cosine_sim is not None:
                    stats["cosine_sum"] += cosine_sim

                entry = {
                    "video_id": video_id,
                    "summary_preview": summary_text[:100] + "..." if len(summary_text) > 100 else summary_text,
                    "evaluation": eval_result
                }

                results.append(entry)

                # Print progress
                print(f"[{i:2d}/{len(summaries)}] {video_id:40s} | "
                      f"QAG: {qag_score:.3f} | "
                      f"Align: {alignment_score:.3f} | "
                      f"Cover: {coverage_score:.3f} | "
                      f"Cos: {cosine_sim:.3f}")

            except Exception as e:
                print(f"[{i:2d}/{len(summaries)}] {video_id:40s} | ❌ Error: {str(e)[:50]}")
                entry = {
                    "video_id": video_id,
                    "error": str(e)
                }
                results.append(entry)

            # Save incremental results
            out_file = run_dir / "evaluations.json"
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "run_id": f"run_{run_timestamp}",
                    "config": {
                        "n_questions": args.n_questions,
                        "limit": args.limit
                    },
                    "stats": stats,
                    "results": results
                }, f, indent=2, ensure_ascii=False)

        # Calculate averages
        total = stats["total"] if stats["total"] > 0 else 1
        avg_qag = stats["qag_sum"] / total
        avg_alignment = stats["alignment_sum"] / total
        avg_coverage = stats["coverage_sum"] / total
        avg_cosine = stats["cosine_sum"] / total

        # Print summary
        print(f"\n{'='*80}")
        print(f"✅ Evaluation Complete")
        print(f"   Total Evaluated: {stats['total']}")
        print(f"   Successful: {stats['success']}")
        print(f"\n   Average Scores:")
        print(f"   - QAG Score:        {avg_qag:.4f}")
        print(f"   - Alignment Score:  {avg_alignment:.4f}")
        print(f"   - Coverage Score:   {avg_coverage:.4f}")
        print(f"   - Cosine Similarity: {avg_cosine:.4f}")
        print(f"\n   Results saved to: {run_dir}")
        print(f"{'='*80}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
