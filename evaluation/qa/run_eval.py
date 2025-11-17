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
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
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
    
    Expected format:
    [
        {
            "chapter": "7",
            "question": "RNN là viết tắt của thuật ngữ gì trong học sâu?",
            "options": null,  # For MCQ questions
            "answer": "RNN là tên viết tắt của mạng Recurrent Neural Network.",
            "video_urls": ["https://youtu.be/_KvZN8-SyvQ"],
            "timestamps": ["00:00:10 - 00:00:40"]
        },
        ...
    ]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


async def run_evaluation(
    test_questions: List[Dict[str, Any]],
    output_dir: str,
    limit: int = None,
    filter_chapter: str = None
):
    """
    Run Q&A evaluation on test questions.
    
    Args:
        test_questions: List of test questions
        output_dir: Directory to save results
        limit: Optional limit on number of questions
        filter_chapter: Optional chapter filter (e.g., "7")
    """
    eval_service = QAEvaluationService()
    
    # Filter questions
    questions = test_questions
    if filter_chapter:
        questions = [q for q in questions if q.get("chapter") == filter_chapter]
    if limit:
        questions = questions[:limit]
    
    print(f"\n{'='*60}")
    print(f"Q&A Evaluation Runner")
    print(f"{'='*60}")
    print(f"📝 Total questions: {len(questions)}")
    if filter_chapter:
        print(f"📚 Filtered by chapter: {filter_chapter}")
    print(f"💾 Output directory: {output_dir}")
    print(f"{'='*60}\n")
    
    # Run evaluation
    results = []
    for i, question_data in enumerate(questions, 1):
        question = question_data.get("question", "")
        ground_truth_answer = question_data.get("answer", "")
        ground_truth_videos = question_data.get("video_urls", [])
        ground_truth_timestamps = question_data.get("timestamps", [])
        chapter = question_data.get("chapter", "")
        
        print(f"\n[{i}/{len(questions)}] Evaluating question from Chapter {chapter}...")
        print(f"❓ {question[:80]}...")
        
        try:
            result = await eval_service.evaluate_question(
                question=question,
                ground_truth_answer=ground_truth_answer,
                ground_truth_videos=ground_truth_videos,
                ground_truth_timestamps=ground_truth_timestamps,
                chapters=[f"Chương {chapter}"] if chapter else None
            )
            
            # Add metadata
            result["chapter"] = chapter
            result["question_index"] = i
            
            results.append(result)
            
            # Print metrics
            metrics = result["metrics"]
            print(f"  ✅ Answer Correctness: {metrics['answer_correctness']['combined_score']:.3f}")
            print(f"  📎 Citation Accuracy: {metrics['citation_accuracy']['accuracy_score']:.3f}")
            print(f"  🎯 Source Relevance (F1): {metrics['source_relevance']['f1_score']:.3f}")
            print(f"  ⚠️  Hallucination Score: {metrics['hallucination_rate']['hallucination_score']:.3f}")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results.append({
                "question": question,
                "error": str(e),
                "chapter": chapter,
                "question_index": i
            })
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    
    # Save individual evaluations
    evaluations_file = os.path.join(output_dir, "evaluations.json")
    with open(evaluations_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Calculate and save summary statistics
    summary = calculate_summary_statistics(results)
    summary_file = os.path.join(output_dir, "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ Evaluation Complete!")
    print(f"{'='*60}")
    print(f"📊 Summary Statistics:")
    print(f"  • Answer Correctness: {summary['average_metrics']['answer_correctness']:.3f}")
    print(f"  • Citation Accuracy: {summary['average_metrics']['citation_accuracy']:.3f}")
    print(f"  • Source Relevance: {summary['average_metrics']['source_relevance_f1']:.3f}")
    print(f"  • Hallucination Score: {summary['average_metrics']['hallucination_score']:.3f} (lower is better)")
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
    answer_correctness_scores = []
    citation_accuracy_scores = []
    source_relevance_f1_scores = []
    hallucination_scores = []
    
    for result in valid_results:
        metrics = result["metrics"]
        answer_correctness_scores.append(metrics["answer_correctness"]["combined_score"])
        citation_accuracy_scores.append(metrics["citation_accuracy"]["accuracy_score"])
        source_relevance_f1_scores.append(metrics["source_relevance"]["f1_score"])
        hallucination_scores.append(metrics["hallucination_rate"]["hallucination_score"])
    
    # Calculate averages
    def avg(lst): return sum(lst) / len(lst) if lst else 0.0
    
    # By chapter breakdown
    chapter_stats = {}
    for result in valid_results:
        chapter = result.get("chapter", "unknown")
        if chapter not in chapter_stats:
            chapter_stats[chapter] = {
                "count": 0,
                "answer_correctness": [],
                "citation_accuracy": [],
                "source_relevance_f1": [],
                "hallucination_score": []
            }
        
        chapter_stats[chapter]["count"] += 1
        metrics = result["metrics"]
        chapter_stats[chapter]["answer_correctness"].append(metrics["answer_correctness"]["combined_score"])
        chapter_stats[chapter]["citation_accuracy"].append(metrics["citation_accuracy"]["accuracy_score"])
        chapter_stats[chapter]["source_relevance_f1"].append(metrics["source_relevance"]["f1_score"])
        chapter_stats[chapter]["hallucination_score"].append(metrics["hallucination_rate"]["hallucination_score"])
    
    # Average by chapter
    chapter_averages = {}
    for chapter, stats in chapter_stats.items():
        chapter_averages[chapter] = {
            "count": stats["count"],
            "answer_correctness": round(avg(stats["answer_correctness"]), 4),
            "citation_accuracy": round(avg(stats["citation_accuracy"]), 4),
            "source_relevance_f1": round(avg(stats["source_relevance_f1"]), 4),
            "hallucination_score": round(avg(stats["hallucination_score"]), 4)
        }
    
    return {
        "total_questions": len(results),
        "successful_evaluations": len(valid_results),
        "failed_evaluations": len(results) - len(valid_results),
        "average_metrics": {
            "answer_correctness": round(avg(answer_correctness_scores), 4),
            "citation_accuracy": round(avg(citation_accuracy_scores), 4),
            "source_relevance_f1": round(avg(source_relevance_f1_scores), 4),
            "hallucination_score": round(avg(hallucination_scores), 4)
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
        '--limit',
        type=int,
        default=None,
        help='Limit number of questions to evaluate'
    )
    parser.add_argument(
        '--chapter',
        type=str,
        default=None,
        help='Filter by chapter (e.g., "7")'
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
    
    # Run evaluation
    asyncio.run(run_evaluation(
        test_questions=test_questions,
        output_dir=output_dir,
        limit=args.limit,
        filter_chapter=args.chapter
    ))


if __name__ == "__main__":
    main()
