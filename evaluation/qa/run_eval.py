"""
Q&A Evaluation Runner

Loads test questions from ground truth, runs Q&A evaluation,
and saves results with detailed metrics.
"""
import os
import sys
import json
import asyncio
import argparse
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add backend and evaluation to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend'))
eval_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_path)
sys.path.insert(0, eval_path)

# Import from qa subdirectory
from qa.eval_service import QAEvaluationService


def load_test_questions(filepath: str) -> List[Dict[str, Any]]:
    """
    Load test questions from JSON file.

    Expected format (matching test_questions.json):
    [
        {
            "Chương": 2,
            "Nội dung câu hỏi": "Question text...",
            "Phương án (nếu có)": "a) ... b) ... c) ... d) ..." or null,
            "Đáp án": "Answer text...",
            "Link Video": "https://youtu.be/...",
            "Timestamps": "00:00:30–00:00:50",
            "Video Title": "Video title..." (optional, only for Chương 2 and 3)
        },
        ...
    ]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def atomic_write_json(filepath: str, data: Any):
    """
    Write JSON data to filepath atomically to avoid partial writes.
    """
    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as tmp_file:
        json.dump(data, tmp_file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, filepath)


def save_results_incrementally(
    evaluations_file: str,
    summary_file: str,
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Persist the latest evaluations and summary metrics incrementally so that
    partial progress is not lost if the run is interrupted.
    """
    summary = calculate_summary_statistics(results)
    atomic_write_json(evaluations_file, results)
    atomic_write_json(summary_file, summary)
    return summary


async def run_evaluation(
    test_questions: List[Dict[str, Any]],
    output_dir: str,
    n_questions: Optional[int] = None,
    random_sample: bool = False,
    chapter_filter: Optional[List[int]] = None
):
    """
    Run Q&A evaluation on test questions.

    Args:
        test_questions: List of test questions
        output_dir: Directory to save results
        n_questions: Number of questions to evaluate (optional)
        random_sample: Whether to randomly sample questions
        chapter_filter: List of chapters to filter (e.g., [2, 3])
    """
    eval_service = QAEvaluationService()

    # Filter by chapters
    questions = test_questions
    if chapter_filter:
        questions = [q for q in questions if q.get("Chương") in chapter_filter]

    # Sample questions
    if n_questions and n_questions < len(questions):
        if random_sample:
            questions = random.sample(questions, n_questions)
        else:
            questions = questions[:n_questions]
    
    print(f"\n{'='*60}")
    print(f"Q&A Evaluation Runner")
    print(f"{'='*60}")
    print(f"📝 Total questions: {len(questions)}")
    if chapter_filter:
        print(f"📚 Filtered by chapters: {chapter_filter}")
    if random_sample:
        print(f"🎲 Random sampling: Yes")
    print(f"💾 Output directory: {output_dir}")
    print(f"{'='*60}\n")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    evaluations_file = os.path.join(output_dir, "evaluations.json")
    summary_file = os.path.join(output_dir, "summary.json")

    # Run evaluation
    results: List[Dict[str, Any]] = []
    latest_summary = save_results_incrementally(evaluations_file, summary_file, results)
    for i, question_data in enumerate(questions, 1):
        # Map from test_questions.json format
        question = question_data.get("Nội dung câu hỏi", "")
        ground_truth_answer = question_data.get("Đáp án", "")
        ground_truth_videos = [question_data.get("Link Video", "")]
        ground_truth_timestamps = [question_data.get("Timestamps", "")]
        chapter = question_data.get("Chương", "")
        
        print(f"\n[{i}/{len(questions)}] Evaluating question from Chapter {chapter}...")
        print(f"❓ {question[:80]}...")
        
        try:
            # Detect question type based on "Phương án (nếu có)"
            options = question_data.get("Phương án (nếu có)")
            question_type = "mcq" if options else "short_answer"

            result = await eval_service.evaluate_question(
                question=question,
                ground_truth_answer=ground_truth_answer,
                ground_truth_videos=ground_truth_videos,
                ground_truth_timestamps=ground_truth_timestamps,
                chapters=[f"Chương {chapter}"] if chapter else None,
                question_type=question_type,
                ground_truth_options=options
            )
            
            # Add metadata
            result["chapter"] = chapter
            result["question_index"] = i
            
            results.append(result)
            latest_summary = save_results_incrementally(evaluations_file, summary_file, results)
            
            # Print metrics
            metrics = result["metrics"]
            q_type = result.get("question_type", "short_answer")

            if q_type == "mcq" and "exact_match" in metrics:
                print(f"  ✅ Exact Match: {metrics['exact_match']['score']:.3f} (Predicted: {metrics['exact_match']['predicted_choice']}, GT: {metrics['exact_match']['ground_truth_choice']})")

            if "answer_correctness" in metrics:
                print(f"  📝 Answer Correctness: {metrics['answer_correctness']['combined_score']:.3f} (Cosine: {metrics['answer_correctness']['cosine_similarity']:.3f}, LLM: {metrics['answer_correctness']['llm_score']:.3f})")

            print(f"  📎 Citation Accuracy: {metrics['citation_accuracy']['score']:.3f} (GT in retrieved: {metrics['citation_accuracy']['ground_truth_in_retrieved']})")
            print(f"  🎯 MRR: {metrics['mrr']['mrr_score']:.3f} (Rank: {metrics['mrr']['rank']})")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results.append({
                "question": question,
                "error": str(e),
                "chapter": chapter,
                "question_index": i
            })
            latest_summary = save_results_incrementally(evaluations_file, summary_file, results)
    
    # Ensure final summary reflects the full run (already saved incrementally)
    summary = latest_summary or calculate_summary_statistics(results)
    
    print(f"\n{'='*60}")
    print(f"✅ Evaluation Complete!")
    print(f"{'='*60}")
    print(f"📊 Summary Statistics:")
    
    # Check if we have valid metrics
    if summary['average_metrics']:
        if summary['average_metrics'].get('exact_match') is not None:
            print(f"  • Exact Match (MCQ): {summary['average_metrics']['exact_match']:.3f}")
        if 'answer_correctness' in summary['average_metrics'] and summary['average_metrics']['answer_correctness'] is not None:
            print(f"  • Answer Correctness: {summary['average_metrics']['answer_correctness']:.3f}")
        if 'answer_correctness_llm' in summary['average_metrics'] and summary['average_metrics']['answer_correctness_llm'] is not None:
            print(f"    ◦ Answer Correctness (LLM): {summary['average_metrics']['answer_correctness_llm']:.3f}")
        if 'answer_correctness_cosine' in summary['average_metrics'] and summary['average_metrics']['answer_correctness_cosine'] is not None:
            print(f"    ◦ Answer Correctness (Cosine): {summary['average_metrics']['answer_correctness_cosine']:.3f}")
        if 'citation_accuracy' in summary['average_metrics']:
            print(f"  • Citation Accuracy: {summary['average_metrics']['citation_accuracy']:.3f}")
        if 'mrr' in summary['average_metrics']:
            print(f"  • MRR (Mean Reciprocal Rank): {summary['average_metrics']['mrr']:.3f}")
    else:
        print(f"  ⚠️  No valid evaluations - all questions failed")
    
    print(f"\n📁 Results saved to:")
    print(f"  • {evaluations_file}")
    print(f"  • {summary_file}")
    print(f"{'='*60}\n")


def calculate_summary_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics from evaluation results."""
    valid_results = [r for r in results if "metrics" in r]
    
    if not valid_results:
        return {
            "total_questions": len(results),
            "successful_evaluations": 0,
            "failed_evaluations": len(results),
            "average_metrics": {}
        }
    
    # Extract metric values
    exact_match_scores = []
    answer_correctness_scores = []
    answer_correctness_llm_scores = []
    answer_correctness_cosine_scores = []
    citation_accuracy_scores = []
    mrr_scores = []

    for result in valid_results:
        metrics = result["metrics"]

        # Exact Match (chỉ có cho MCQ)
        if "exact_match" in metrics:
            exact_match_scores.append(metrics["exact_match"]["score"])

        # Answer Correctness (chỉ có cho short_answer)
        if "answer_correctness" in metrics:
            ac_metrics = metrics["answer_correctness"]
            answer_correctness_scores.append(ac_metrics["combined_score"])
            answer_correctness_llm_scores.append(ac_metrics.get("llm_score", 0.0))
            answer_correctness_cosine_scores.append(ac_metrics.get("cosine_similarity", 0.0))

        # Citation Accuracy
        citation_accuracy_scores.append(metrics["citation_accuracy"]["score"])

        # MRR
        if "mrr" in metrics:
            mrr_scores.append(metrics["mrr"]["mrr_score"])
    
    # Calculate averages
    def avg(lst): return sum(lst) / len(lst) if lst else 0.0
    
    # By chapter breakdown
    chapter_stats = {}
    for result in valid_results:
        chapter = result.get("chapter", "unknown")
        if chapter not in chapter_stats:
            chapter_stats[chapter] = {
                "count": 0,
                "exact_match": [],
                "answer_correctness": [],
                "answer_correctness_llm": [],
                "answer_correctness_cosine": [],
                "citation_accuracy": [],
                "mrr": []
            }

        chapter_stats[chapter]["count"] += 1
        metrics = result["metrics"]

        if "exact_match" in metrics:
            chapter_stats[chapter]["exact_match"].append(metrics["exact_match"]["score"])

        if "answer_correctness" in metrics:
            ac_metrics = metrics["answer_correctness"]
            chapter_stats[chapter]["answer_correctness"].append(ac_metrics["combined_score"])
            chapter_stats[chapter]["answer_correctness_llm"].append(ac_metrics.get("llm_score", 0.0))
            chapter_stats[chapter]["answer_correctness_cosine"].append(ac_metrics.get("cosine_similarity", 0.0))

        chapter_stats[chapter]["citation_accuracy"].append(metrics["citation_accuracy"]["score"])

        if "mrr" in metrics:
            chapter_stats[chapter]["mrr"].append(metrics["mrr"]["mrr_score"])
    
    # Average by chapter
    chapter_averages = {}
    for chapter, stats in chapter_stats.items():
        chapter_averages[chapter] = {
            "count": stats["count"],
            "citation_accuracy": round(avg(stats["citation_accuracy"]), 4),
            "mrr": round(avg(stats["mrr"]), 4) if stats["mrr"] else None
        }
        if stats["exact_match"]:
            chapter_averages[chapter]["exact_match"] = round(avg(stats["exact_match"]), 4)
        if stats["answer_correctness"]:
            chapter_averages[chapter]["answer_correctness"] = round(avg(stats["answer_correctness"]), 4)
        if stats.get("answer_correctness_llm"):
            chapter_averages[chapter]["answer_correctness_llm"] = round(avg(stats["answer_correctness_llm"]), 4)
        if stats.get("answer_correctness_cosine"):
            chapter_averages[chapter]["answer_correctness_cosine"] = round(avg(stats["answer_correctness_cosine"]), 4)

    return {
        "total_questions": len(results),
        "successful_evaluations": len(valid_results),
        "failed_evaluations": len(results) - len(valid_results),
        "average_metrics": {
            "exact_match": round(avg(exact_match_scores), 4) if exact_match_scores else None,
            "answer_correctness": round(avg(answer_correctness_scores), 4) if answer_correctness_scores else None,
            "answer_correctness_llm": round(avg(answer_correctness_llm_scores), 4) if answer_correctness_llm_scores else None,
            "answer_correctness_cosine": round(avg(answer_correctness_cosine_scores), 4) if answer_correctness_cosine_scores else None,
            "citation_accuracy": round(avg(citation_accuracy_scores), 4),
            "mrr": round(avg(mrr_scores), 4) if mrr_scores else 0.0
        },
        "by_chapter": chapter_averages,
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="Run Q&A evaluation")
    parser.add_argument(
        '--test-file',
        type=str,
        default='test_questions.json',
        help='Path to test questions JSON file'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for results (default: results/run_TIMESTAMP)'
    )
    parser.add_argument(
        '--n-questions',
        type=int,
        default=None,
        help='Number of questions to evaluate (default: all questions)'
    )
    parser.add_argument(
        '--all-questions',
        action='store_true',
        help='Evaluate all available questions (overrides --n-questions)'
    )
    parser.add_argument(
        '--random',
        action='store_true',
        help='Randomly sample n questions instead of taking first n'
    )
    parser.add_argument(
        '--chapters',
        type=int,
        nargs='+',
        default=None,
        help='Filter by chapters (e.g., --chapters 2 3 for Chương 2 and 3)'
    )

    args = parser.parse_args()
    
    # Load test questions
    test_file = os.path.join(os.path.dirname(__file__), args.test_file)
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        print("Please create test_questions.json in evaluation/qa/ directory")
        return
    
    test_questions = load_test_questions(test_file)
    
    # Output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(__file__), 'results', f'run_{timestamp}')
    
    # Determine number of questions to run
    n_questions = None if args.all_questions else args.n_questions

    # Run evaluation
    asyncio.run(run_evaluation(
        test_questions=test_questions,
        output_dir=output_dir,
        n_questions=n_questions,
        random_sample=args.random,
        chapter_filter=args.chapters
    ))


if __name__ == "__main__":
    main()
