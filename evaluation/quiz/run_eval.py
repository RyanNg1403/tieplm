"""
Quiz QAG evaluation runner.

Usage:
    python evaluation/quiz/run_eval.py --num-cases 5
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)

from eval_service import QuizQAGEvaluator


class EvaluationRunner:
    """Run multiple evaluation cases and save structured outputs."""

    def __init__(self, results_dir: str, question_type: str = "open_ended"):
        self.base_results_dir = Path(results_dir)
        self.base_results_dir.mkdir(parents=True, exist_ok=True)

        self.run_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.results_dir = self.base_results_dir / f"run_{self.run_timestamp}"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.question_type = question_type
        self.evaluator = QuizQAGEvaluator()
        print(f"📁 Results will be stored in {self.results_dir}")

    async def run(self, num_cases: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for idx in range(1, num_cases + 1):
            case_id = f"quiz_eval_{idx:03d}"
            print(f"\n{'='*80}")
            print(f"🚀 Running case {idx}/{num_cases} (ID: {case_id})")
            print(f"{'='*80}")

            case_result = await self.evaluator.evaluate_case(
                case_id=case_id,
                question_type=self.question_type,
            )
            results.append(case_result)

            self._save_generations(results)
            self._save_evaluations(results)

        return results

    def _save_generations(self, results: List[Dict[str, Any]]):
        data = {
            "run_info": {
                "run_id": f"run_{self.run_timestamp}",
                "timestamp": self.run_timestamp,
                "total_cases": len(results),
                "model": os.getenv("EVAL_MODEL", "gpt-5-nano"),
                "question_type": self.question_type,
            },
            "cases": [],
        }

        for res in results:
            entry = {
                "case_id": res["case_id"],
                "timestamp": res.get("timestamp"),
                "chunk": res.get("chunk"),
            }

            if res.get("error"):
                entry["error"] = res["error"]
            else:
                entry.update(
                    {
                        "question": res.get("question"),
                        "question_type": res.get("question_type"),
                    }
                )

                if self.question_type == "mcq":
                    entry.update(
                        {
                            "options": res.get("options"),
                            "correct_answer": res.get("correct_answer"),
                            "predicted_answer": res.get("predicted_answer"),
                            "score": res.get("score"),
                        }
                    )
                else:
                    entry.update(
                        {
                            "reference_answer": res.get("reference_answer"),
                            "qa_answer": res.get("qa_answer"),
                            "key_points": res.get("key_points"),
                            "embedding_similarity": res.get(
                                "embedding_similarity"
                            ),
                        }
                    )

            data["cases"].append(entry)

        path = self.results_dir / "generations.json"
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2, ensure_ascii=False)
        print(f"💾 Saved generations to {path}")

    def _save_evaluations(self, results: List[Dict[str, Any]]):
        successful = [r for r in results if not r.get("error")]

        if self.question_type == "mcq":
            scores = [r.get("score") for r in successful if r.get("score") is not None]
        else:
            scores = [
                r.get("embedding_similarity")
                for r in successful
                if r.get("embedding_similarity") is not None
            ]

        statistics = self._compute_stats(scores) if scores else {"error": "No scores"}

        data = {
            "run_info": {
                "run_id": f"run_{self.run_timestamp}",
                "timestamp": self.run_timestamp,
                "total_cases": len(results),
                "successful_cases": len(successful),
                "failed_cases": len(results) - len(successful),
                "question_type": self.question_type,
            },
            "statistics": statistics,
            "scores": [],
        }

        for res in results:
            entry = {
                "case_id": res["case_id"],
                "question": res.get("question"),
            }

            if res.get("error"):
                entry["error"] = res["error"]
            else:
                if self.question_type == "mcq":
                    entry.update(
                        {
                            "score": res.get("score"),
                            "predicted_answer": res.get("predicted_answer"),
                            "correct_answer": res.get("correct_answer"),
                        }
                    )
                else:
                    entry.update(
                        {
                            "embedding_similarity": res.get(
                                "embedding_similarity"
                            ),
                            "reference_answer": res.get("reference_answer"),
                            "qa_answer": res.get("qa_answer"),
                        }
                    )

            data["scores"].append(entry)

        path = self.results_dir / "evaluations.json"
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2, ensure_ascii=False)
        print(f"📊 Saved evaluations to {path}")
        self._print_summary(statistics, len(results), len(successful))

    def _compute_stats(self, scores: List[float]) -> Dict[str, Any]:
        if not scores:
            return {"error": "No scores"}

        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        mean = sum(sorted_scores) / n
        median = (
            sorted_scores[n // 2]
            if n % 2 == 1
            else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        )

        variance = sum((s - mean) ** 2 for s in sorted_scores) / n if n > 1 else 0.0

        return {
            "mean": round(mean, 4),
            "median": round(median, 4),
            "min": round(min(sorted_scores), 4),
            "max": round(max(sorted_scores), 4),
            "std": round(variance**0.5, 4),
        }

    def _print_summary(self, statistics: Dict[str, Any], total: int, successful: int):
        print(f"\n{'='*80}")
        print("📊 QUIZ QAG EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total cases: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")

        if "mean" in statistics:
            if self.question_type == "mcq":
                print("\nMCQ accuracy statistics:")
            else:
                print("\nEmbedding similarity statistics:")

            print(f"  Mean:   {statistics['mean']:.4f}")
            print(f"  Median: {statistics['median']:.4f}")
            print(f"  Min:    {statistics['min']:.4f}")
            print(f"  Max:    {statistics['max']:.4f}")
            print(f"  Std:    {statistics['std']:.4f}")
        else:
            print("\n⚠️  No statistics available.")

        print(f"{'='*80}\n")


async def main():
    parser = argparse.ArgumentParser(description="Quiz QAG Evaluation Runner")
    parser.add_argument(
        "--num-cases",
        type=int,
        default=5,
        help="Number of random quiz questions to generate and evaluate",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results",
        help="Directory to store evaluation outputs",
    )
    parser.add_argument(
        "--question-type",
        type=str,
        choices=["open_ended", "mcq"],
        default="open_ended",
        help="Type of quiz questions to evaluate",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    results_dir = script_dir / args.results_dir

    runner = EvaluationRunner(
        results_dir=str(results_dir),
        question_type=args.question_type,
    )
    await runner.run(num_cases=args.num_cases)

    print(f"\n✅ Evaluation finished. Final results: {runner.results_dir}")


if __name__ == "__main__":
    asyncio.run(main())

