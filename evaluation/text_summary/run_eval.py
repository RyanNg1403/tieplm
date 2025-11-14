"""
Text Summarization Evaluation Runner

Evaluates text summarization using 50 test questions with DeepEval's QAG metrics.

Usage:
    python evaluation/text_summary/run_eval.py --all
    python evaluation/text_summary/run_eval.py --start 0 --end 10
    python evaluation/text_summary/run_eval.py --question-id sum_001
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

# Load .env from project root (2 levels up from this script)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

print(f"✅ Loaded .env from: {env_path}")
print(f"🔑 OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET'}")

from eval_service import TextSummaryEvaluator


class EvaluationRunner:
    """Runs text summarization evaluation and saves results."""
    
    def __init__(self, test_questions_path: str, results_dir: str):
        """
        Initialize evaluation runner.
        
        Args:
            test_questions_path: Path to test questions JSON
            results_dir: Base directory to save results
        """
        self.test_questions_path = Path(test_questions_path)
        self.base_results_dir = Path(results_dir)
        
        # Create timestamped folder for this run
        self.run_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.results_dir = self.base_results_dir / f"run_{self.run_timestamp}"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Results will be saved to: {self.results_dir}")
        
        # Load test questions
        with open(self.test_questions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.questions = data['questions']
            self.metadata = {k: v for k, v in data.items() if k != 'questions'}
        
        self.evaluator = TextSummaryEvaluator()
        
        print(f"✅ Loaded {len(self.questions)} test questions")
    
    async def evaluate_single(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single question.
        
        Args:
            question_data: Question metadata
        
        Returns:
            Evaluation result
        """
        question_id = question_data['id']
        query = question_data['query']
        
        print(f"\n{'='*80}")
        print(f"🔍 Evaluating: {question_id}")
        print(f"📝 Query: {query}")
        print(f"{'='*80}")
        
        try:
            # Step 1: Generate summary (no chapter filter, search all content)
            generation_start = datetime.utcnow()
            summary_result = await self.evaluator.generate_summary(
                query=query,
                chapters=None  # Search across all chapters
            )
            generation_time = (datetime.utcnow() - generation_start).total_seconds()
            
            if "error" in summary_result:
                print(f"❌ Error generating summary: {summary_result['error']}")
                return {
                    "question_id": question_id,
                    "query": query,
                    "error": summary_result['error'],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            summary = summary_result['summary']
            original_text = summary_result['original_text']
            
            print(f"✅ Summary generated ({generation_time:.2f}s)")
            print(f"📄 Summary length: {len(summary)} chars")
            print(f"📄 Original text length: {len(original_text)} chars")
            
            # Step 2: Evaluate with DeepEval
            eval_start = datetime.utcnow()
            eval_result = self.evaluator.evaluate_summary(
                query=query,
                summary=summary,
                original_text=original_text,
                assessment_questions=None  # Let DeepEval generate questions
            )
            eval_time = (datetime.utcnow() - eval_start).total_seconds()
            
            print(f"✅ Evaluation complete ({eval_time:.2f}s)")
            print(f"📊 Overall Score: {eval_result.get('score', 'N/A'):.4f}")
            print(f"📊 Coverage Score: {eval_result.get('coverage_score', 'N/A')}")
            print(f"📊 Alignment Score: {eval_result.get('alignment_score', 'N/A')}")
            print(f"📊 Success: {eval_result.get('success', False)}")
            
            # Combine results
            summary_chars = len(summary)
            original_chars = len(original_text)

            result = {
                "question_id": question_id,
                "query": query,
                "generation": {
                    "summary": summary,
                    "original_text": original_text,
                    "chunks_retrieved": summary_result.get('chunks_retrieved', 0),
                    "chunks_used": summary_result.get('chunks_used', 0),
                    "summary_chars": summary_chars,
                    "original_text_chars": original_chars,
                    "generation_time_seconds": generation_time
                },
                "evaluation": eval_result,
                "total_time_seconds": generation_time + eval_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error during evaluation: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "question_id": question_id,
                "query": query,
                "generation": None,
                "evaluation": None,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def evaluate_batch(
        self, 
        start_idx: int = 0, 
        end_idx: int = None,
        question_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate a batch of questions.
        
        Args:
            start_idx: Start index (inclusive)
            end_idx: End index (exclusive), None for all
            question_ids: Specific question IDs to evaluate
        
        Returns:
            List of evaluation results
        """
        if question_ids:
            questions_to_eval = [q for q in self.questions if q['id'] in question_ids]
        else:
            end_idx = end_idx or len(self.questions)
            questions_to_eval = self.questions[start_idx:end_idx]
        
        print(f"\n🚀 Starting evaluation of {len(questions_to_eval)} questions")
        print(f"⏰ Started at: {datetime.utcnow().isoformat()}")
        
        results = []
        for i, question_data in enumerate(questions_to_eval, 1):
            print(f"\n📍 Progress: {i}/{len(questions_to_eval)}")
            result = await self.evaluate_single(question_data)
            results.append(result)
        
        return results
    
    def save_aggregated_results(self, results: List[Dict[str, Any]]):
        """Save results in 2 files: generations and evaluations."""
        timestamp = self.run_timestamp
        
        # Separate successful and failed evaluations
        successful_evals = [r for r in results if r.get('evaluation') and not r.get('error')]
        failed_evals = [r for r in results if r.get('error') or not r.get('evaluation')]
        
        # ================================================================
        # FILE 1: generations.json (summaries + original_text + metadata)
        # ================================================================
        generations_data = {
            "run_info": {
                "run_id": f"run_{timestamp}",
                "timestamp": timestamp,
                "total_questions": len(results),
                "successful": len(successful_evals),
                "failed": len(failed_evals),
                "model": os.getenv("EVAL_MODEL", "gpt-5-nano")
            },
            "questions_metadata": self.metadata,
            "generations": []
        }
        
        for result in results:
            gen_entry = {
                "question_id": result['question_id'],
                "query": result['query']
            }
            
            if result.get('generation'):
                gen_entry.update({
                    "summary": result['generation']['summary'],
                    "original_text": result['generation']['original_text'],
                    "chunks_retrieved": result['generation'].get('chunks_retrieved', 0),
                    "chunks_used": result['generation'].get('chunks_used', 0),
                    "generation_time_seconds": result['generation'].get('generation_time_seconds', 0)
                })
            else:
                gen_entry["error"] = result.get('error', 'Unknown error')
            
            generations_data['generations'].append(gen_entry)
        
        generations_file = self.results_dir / "generations.json"
        with open(generations_file, 'w', encoding='utf-8') as f:
            json.dump(generations_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Saved generations to: {generations_file}")
        
        # ================================================================
        # FILE 2: evaluations.json (scores + statistics)
        # ================================================================
        
        # Calculate statistics
        if successful_evals:
            scores = [r['evaluation']['score'] for r in successful_evals]
            coverage_scores = [r['evaluation'].get('coverage_score') for r in successful_evals if r['evaluation'].get('coverage_score') is not None]
            alignment_scores = [r['evaluation'].get('alignment_score') for r in successful_evals if r['evaluation'].get('alignment_score') is not None]
            
            statistics = {
                "overall": {
                    "mean": sum(scores) / len(scores) if scores else 0,
                    "min": min(scores) if scores else 0,
                    "max": max(scores) if scores else 0,
                    "median": sorted(scores)[len(scores)//2] if scores else 0,
                    "std": self._calculate_std(scores) if len(scores) > 1 else 0
                },
                "coverage": {
                    "mean": sum(coverage_scores) / len(coverage_scores) if coverage_scores else None,
                    "min": min(coverage_scores) if coverage_scores else None,
                    "max": max(coverage_scores) if coverage_scores else None
                } if coverage_scores else None,
                    "alignment": {
                        "mean": sum(alignment_scores) / len(alignment_scores) if alignment_scores else None,
                        "min": min(alignment_scores) if alignment_scores else None,
                        "max": max(alignment_scores) if alignment_scores else None
                    } if alignment_scores else None
                }
        else:
            statistics = {
                "error": "No successful evaluations"
            }
        
        evaluations_data = {
            "run_info": {
                "run_id": f"run_{timestamp}",
                "timestamp": timestamp,
                "total_questions": len(results),
                "successful_evaluations": len(successful_evals),
                "failed_evaluations": len(failed_evals),
                "evaluation_model": os.getenv("EVAL_MODEL", "gpt-5-nano"),
                "threshold": float(os.getenv("EVAL_SUMMARIZATION_THRESHOLD", "0.5")),
                "n_questions": int(os.getenv("EVAL_SUMMARIZATION_N_QUESTIONS", "10"))
            },
            "statistics": statistics,
            "scores": []
        }
        
        for result in results:
            score_entry = {
                "question_id": result['question_id'],
                "query": result['query']
            }
            
            if result.get('evaluation'):
                score_entry.update({
                    "score": result['evaluation']['score'],
                    "coverage_score": result['evaluation'].get('coverage_score'),
                    "alignment_score": result['evaluation'].get('alignment_score'),
                    "success": result['evaluation'].get('success', False),
                    "reason": result['evaluation'].get('reason', ''),
                    "summary_chars": result['generation'].get('summary_chars') if result.get('generation') else None,
                    "original_text_chars": result['generation'].get('original_text_chars') if result.get('generation') else None,
                    "evaluation_time_seconds": result.get('total_time_seconds', 0) - result['generation'].get('generation_time_seconds', 0) if result.get('generation') else 0
                })
            else:
                score_entry["error"] = result.get('error', 'Unknown error')
            
            evaluations_data['scores'].append(score_entry)
        
        evaluations_file = self.results_dir / "evaluations.json"
        with open(evaluations_file, 'w', encoding='utf-8') as f:
            json.dump(evaluations_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved evaluations to: {evaluations_file}")
        
        # Print summary to console
        self._print_summary(statistics, len(results), len(successful_evals))
    
    def _calculate_std(self, scores: List[float]) -> float:
        """Calculate standard deviation."""
        if not scores or len(scores) < 2:
            return 0.0
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        return variance ** 0.5
    
    def _print_summary(self, statistics: Dict[str, Any], total: int, successful: int):
        """Print evaluation summary."""
        print(f"\n{'='*80}")
        print("📊 EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Questions: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        
        if statistics.get('overall'):
            overall = statistics['overall']
            print(f"\n📈 Overall Scores:")
            print(f"  Mean:   {overall['mean']:.4f}")
            print(f"  Median: {overall['median']:.4f}")
            print(f"  Min:    {overall['min']:.4f}")
            print(f"  Max:    {overall['max']:.4f}")
            print(f"  Std:    {overall['std']:.4f}")
            
            if statistics.get('coverage'):
                coverage = statistics['coverage']
                print(f"\n📊 Coverage Scores:")
                print(f"  Mean: {coverage['mean']:.4f}")
                print(f"  Min:  {coverage['min']:.4f}")
                print(f"  Max:  {coverage['max']:.4f}")
            
            if statistics.get('alignment'):
                alignment = statistics['alignment']
                print(f"\n📊 Alignment Scores:")
                print(f"  Mean: {alignment['mean']:.4f}")
                print(f"  Min:  {alignment['min']:.4f}")
                print(f"  Max:  {alignment['max']:.4f}")
        
        print(f"{'='*80}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Text Summarization Evaluation Runner")
    parser.add_argument('--all', action='store_true', help="Evaluate all questions")
    parser.add_argument('--start', type=int, default=0, help="Start index (inclusive)")
    parser.add_argument('--end', type=int, default=None, help="End index (exclusive)")
    parser.add_argument('--question-id', type=str, nargs='+', help="Specific question IDs to evaluate")
    parser.add_argument('--questions-file', type=str, default='test_questions.json', help="Test questions file")
    parser.add_argument('--results-dir', type=str, default='results', help="Results directory")
    
    args = parser.parse_args()
    
    # Get paths
    script_dir = Path(__file__).parent
    questions_file = script_dir / args.questions_file
    results_dir = script_dir / args.results_dir
    
    # Create runner
    runner = EvaluationRunner(
        test_questions_path=str(questions_file),
        results_dir=str(results_dir)
    )
    
    # Run evaluation
    if args.all:
        results = await runner.evaluate_batch()
    elif args.question_id:
        results = await runner.evaluate_batch(question_ids=args.question_id)
    else:
        results = await runner.evaluate_batch(start_idx=args.start, end_idx=args.end)
    
    # Save aggregated results
    runner.save_aggregated_results(results)
    
    print(f"\n✅ Evaluation complete!")


if __name__ == "__main__":
    asyncio.run(main())

