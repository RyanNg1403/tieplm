"""
Visualization script for Q&A evaluation results.

Generates comprehensive plots for QA evaluation metrics including:
- Exact Match (MCQ)
- Answer Correctness (Open-ended)
- Citation Accuracy
- MRR (Mean Reciprocal Rank)
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["font.size"] = 10


class QAResultsVisualizer:
    """Visualizer for QA evaluation results."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

        # Load data
        self.evaluations = self._load_json(results_dir / "evaluations.json")
        self.summary = self._load_json(results_dir / "summary.json")

        # Output directory for plots
        self.output_dir = results_dir / "visualizations"
        self.output_dir.mkdir(exist_ok=True)

    def _load_json(self, filepath: Path) -> Any:
        """Load JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def plot_overall_metrics(self):
        """Generate overview of all metrics."""
        avg_metrics = self.summary["average_metrics"]

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(
            f"Q&A Evaluation Overview - {self.summary['total_questions']} Questions",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Main Metrics Bar Chart
        ax1 = axes[0, 0]
        metrics = ["Exact Match\n(MCQ)", "Answer\nCorrectness", "Citation\nAccuracy", "MRR"]
        values = [
            avg_metrics["exact_match"],
            avg_metrics["answer_correctness"],
            avg_metrics["citation_accuracy"],
            avg_metrics["mrr"],
        ]
        colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"]

        bars = ax1.bar(metrics, values, color=colors, alpha=0.7, edgecolor="black")
        ax1.set_ylabel("Score", fontweight="bold")
        ax1.set_title("Average Performance Across Metrics", fontweight="bold", fontsize=12)
        ax1.set_ylim(0, 1.1)
        ax1.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5, linewidth=1)

        # Add value labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{val:.3f}\n({val*100:.1f}%)",
                ha="center",
                va="bottom",
                fontweight="bold",
            )
        ax1.grid(True, alpha=0.3, axis="y")

        # 2. Answer Correctness Breakdown
        ax2 = axes[0, 1]
        ac_metrics = ["Combined", "LLM Score", "Cosine Sim"]
        ac_values = [
            avg_metrics["answer_correctness"],
            avg_metrics["answer_correctness_llm"],
            avg_metrics["answer_correctness_cosine"],
        ]

        bars = ax2.bar(ac_metrics, ac_values, color=["#e74c3c", "#c0392b", "#e67e22"], alpha=0.7, edgecolor="black")
        ax2.set_ylabel("Score", fontweight="bold")
        ax2.set_title("Answer Correctness Breakdown (Open-Ended)", fontweight="bold", fontsize=12)
        ax2.set_ylim(0, 1.1)

        for bar, val in zip(bars, ac_values):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{val:.3f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )
        ax2.grid(True, alpha=0.3, axis="y")

        # 3. Statistics Summary
        ax3 = axes[1, 0]
        ax3.axis("off")

        stats_text = f"""
        EVALUATION SUMMARY
        ═══════════════════════════════════════

        Total Questions:        {self.summary['total_questions']}
        Successful:             {self.summary['successful_evaluations']}
        Failed:                 {self.summary['failed_evaluations']}

        AVERAGE METRICS
        ───────────────────────────────────────
        Exact Match (MCQ):      {avg_metrics['exact_match']:.3f} ({avg_metrics['exact_match']*100:.1f}%)
        Answer Correctness:     {avg_metrics['answer_correctness']:.3f} ({avg_metrics['answer_correctness']*100:.1f}%)
          ├─ LLM Score:         {avg_metrics['answer_correctness_llm']:.3f}
          └─ Cosine Similarity: {avg_metrics['answer_correctness_cosine']:.3f}
        Citation Accuracy:      {avg_metrics['citation_accuracy']:.3f} ({avg_metrics['citation_accuracy']*100:.1f}%)
        MRR:                    {avg_metrics['mrr']:.3f}

        Timestamp:              {self.summary['timestamp'][:19]}
        """

        ax3.text(
            0.1,
            0.5,
            stats_text,
            fontsize=10,
            family="monospace",
            verticalalignment="center",
            bbox=dict(boxstyle="round", facecolor="#ecf0f1", alpha=0.8),
        )

        # 4. Question Type Distribution
        ax4 = axes[1, 1]

        mcq_count = sum(1 for e in self.evaluations if e.get("question_type") == "mcq")
        open_ended_count = self.summary["total_questions"] - mcq_count

        sizes = [mcq_count, open_ended_count]
        labels = [f"MCQ\n({mcq_count})", f"Open-Ended\n({open_ended_count})"]
        colors = ["#3498db", "#e74c3c"]
        explode = (0.05, 0.05)

        ax4.pie(sizes, explode=explode, labels=labels, colors=colors, autopct="%1.1f%%",
                shadow=True, startangle=90, textprops={"fontweight": "bold", "fontsize": 11})
        ax4.set_title("Question Type Distribution", fontweight="bold", fontsize=12)

        plt.tight_layout()
        output_path = self.output_dir / "overall_metrics.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Overall metrics visualization saved to: {output_path}")
        plt.close()

    def plot_by_chapter(self):
        """Generate chapter-wise performance analysis."""
        by_chapter = self.summary["by_chapter"]
        chapters = sorted(by_chapter.keys(), key=int)

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Performance by Chapter", fontsize=16, fontweight="bold")

        # 1. Exact Match by Chapter
        ax1 = axes[0, 0]
        em_scores = [by_chapter[ch].get("exact_match", 0) for ch in chapters]
        bars = ax1.bar(chapters, em_scores, color="#3498db", alpha=0.7, edgecolor="black")
        ax1.set_xlabel("Chapter", fontweight="bold")
        ax1.set_ylabel("Exact Match Score", fontweight="bold")
        ax1.set_title("Exact Match (MCQ) by Chapter", fontweight="bold", fontsize=12)
        ax1.set_ylim(0, 1.1)
        ax1.axhline(
            y=self.summary["average_metrics"]["exact_match"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Overall Avg: {self.summary['average_metrics']['exact_match']:.3f}",
        )
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis="y")

        for bar, val in zip(bars, em_scores):
            if val > 0:
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    val,
                    f"{val:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        # 2. Citation Accuracy by Chapter
        ax2 = axes[0, 1]
        ca_scores = [by_chapter[ch].get("citation_accuracy", 0) for ch in chapters]
        bars = ax2.bar(chapters, ca_scores, color="#2ecc71", alpha=0.7, edgecolor="black")
        ax2.set_xlabel("Chapter", fontweight="bold")
        ax2.set_ylabel("Citation Accuracy Score", fontweight="bold")
        ax2.set_title("Citation Accuracy by Chapter", fontweight="bold", fontsize=12)
        ax2.set_ylim(0, 1.1)
        ax2.axhline(
            y=self.summary["average_metrics"]["citation_accuracy"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Overall Avg: {self.summary['average_metrics']['citation_accuracy']:.3f}",
        )
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis="y")

        for bar, val in zip(bars, ca_scores):
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                val,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        # 3. MRR by Chapter
        ax3 = axes[1, 0]
        mrr_scores = [by_chapter[ch].get("mrr", 0) for ch in chapters]
        bars = ax3.bar(chapters, mrr_scores, color="#f39c12", alpha=0.7, edgecolor="black")
        ax3.set_xlabel("Chapter", fontweight="bold")
        ax3.set_ylabel("MRR Score", fontweight="bold")
        ax3.set_title("Mean Reciprocal Rank by Chapter", fontweight="bold", fontsize=12)
        ax3.set_ylim(0, 1.1)
        ax3.axhline(
            y=self.summary["average_metrics"]["mrr"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Overall Avg: {self.summary['average_metrics']['mrr']:.3f}",
        )
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis="y")

        for bar, val in zip(bars, mrr_scores):
            ax3.text(
                bar.get_x() + bar.get_width() / 2.0,
                val,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        # 4. Answer Correctness by Chapter (for chapters with open-ended questions)
        ax4 = axes[1, 1]

        chapters_with_ac = [ch for ch in chapters if "answer_correctness" in by_chapter[ch]]
        ac_scores = [by_chapter[ch]["answer_correctness"] for ch in chapters_with_ac]

        if chapters_with_ac:
            bars = ax4.bar(chapters_with_ac, ac_scores, color="#e74c3c", alpha=0.7, edgecolor="black")
            ax4.set_xlabel("Chapter", fontweight="bold")
            ax4.set_ylabel("Answer Correctness Score", fontweight="bold")
            ax4.set_title("Answer Correctness by Chapter (Open-Ended)", fontweight="bold", fontsize=12)
            ax4.set_ylim(0, 1.1)
            ax4.axhline(
                y=self.summary["average_metrics"]["answer_correctness"],
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Overall Avg: {self.summary['average_metrics']['answer_correctness']:.3f}",
            )
            ax4.legend()
            ax4.grid(True, alpha=0.3, axis="y")

            for bar, val in zip(bars, ac_scores):
                ax4.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    val,
                    f"{val:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )
        else:
            ax4.text(0.5, 0.5, "No open-ended questions", ha="center", va="center", fontsize=12)
            ax4.axis("off")

        plt.tight_layout()
        output_path = self.output_dir / "by_chapter_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Chapter analysis visualization saved to: {output_path}")
        plt.close()

    def plot_metric_distributions(self):
        """Generate distribution plots for all metrics."""
        # Extract metrics from evaluations
        exact_matches = []
        answer_correctness_scores = []
        citation_accuracies = []
        mrr_scores = []

        for eval_item in self.evaluations:
            metrics = eval_item.get("metrics", {})

            if "exact_match" in metrics:
                exact_matches.append(metrics["exact_match"]["score"])

            if "answer_correctness" in metrics:
                answer_correctness_scores.append(metrics["answer_correctness"]["combined_score"])

            if "citation_accuracy" in metrics:
                citation_accuracies.append(metrics["citation_accuracy"]["score"])

            if "mrr" in metrics:
                mrr_scores.append(metrics["mrr"]["mrr_score"])

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Metric Distributions", fontsize=16, fontweight="bold")

        # 1. Exact Match Distribution
        if exact_matches:
            ax1 = axes[0, 0]
            unique, counts = np.unique(exact_matches, return_counts=True)
            bars = ax1.bar(unique, counts, color="#3498db", alpha=0.7, edgecolor="black", width=0.4)
            ax1.set_xlabel("Exact Match Score", fontweight="bold")
            ax1.set_ylabel("Frequency", fontweight="bold")
            ax1.set_title(f"Exact Match Distribution (n={len(exact_matches)})", fontweight="bold", fontsize=12)
            ax1.set_xticks([0, 1])
            ax1.set_xticklabels(["Incorrect (0)", "Correct (1)"])

            for x, count in zip(unique, counts):
                ax1.text(x, count, f"{count}\n({count/len(exact_matches)*100:.1f}%)",
                        ha="center", va="bottom", fontweight="bold")

        # 2. Answer Correctness Distribution
        if answer_correctness_scores:
            ax2 = axes[0, 1]
            n, bins, patches = ax2.hist(
                answer_correctness_scores,
                bins=20,
                color="#e74c3c",
                alpha=0.7,
                edgecolor="black",
            )

            # Color bars by value
            for i, patch in enumerate(patches):
                bin_center = (bins[i] + bins[i + 1]) / 2
                if bin_center >= 0.8:
                    patch.set_facecolor("#27ae60")
                elif bin_center >= 0.6:
                    patch.set_facecolor("#f39c12")
                else:
                    patch.set_facecolor("#e74c3c")

            ax2.axvline(
                np.mean(answer_correctness_scores),
                color="blue",
                linestyle="--",
                linewidth=2,
                label=f"Mean: {np.mean(answer_correctness_scores):.3f}",
            )
            ax2.set_xlabel("Answer Correctness Score", fontweight="bold")
            ax2.set_ylabel("Frequency", fontweight="bold")
            ax2.set_title(f"Answer Correctness Distribution (n={len(answer_correctness_scores)})",
                         fontweight="bold", fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3, axis="y")

        # 3. Citation Accuracy Distribution
        if citation_accuracies:
            ax3 = axes[1, 0]
            unique, counts = np.unique(citation_accuracies, return_counts=True)
            bars = ax3.bar(unique, counts, color="#2ecc71", alpha=0.7, edgecolor="black", width=0.4)
            ax3.set_xlabel("Citation Accuracy Score", fontweight="bold")
            ax3.set_ylabel("Frequency", fontweight="bold")
            ax3.set_title(f"Citation Accuracy Distribution (n={len(citation_accuracies)})",
                         fontweight="bold", fontsize=12)
            ax3.set_xticks([0, 1])
            ax3.set_xticklabels(["Not Found (0)", "Found (1)"])

            for x, count in zip(unique, counts):
                ax3.text(x, count, f"{count}\n({count/len(citation_accuracies)*100:.1f}%)",
                        ha="center", va="bottom", fontweight="bold")

        # 4. MRR Distribution
        if mrr_scores:
            ax4 = axes[1, 1]
            n, bins, patches = ax4.hist(
                mrr_scores,
                bins=20,
                color="#f39c12",
                alpha=0.7,
                edgecolor="black",
            )
            ax4.axvline(
                np.mean(mrr_scores),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Mean: {np.mean(mrr_scores):.3f}",
            )
            ax4.set_xlabel("MRR Score", fontweight="bold")
            ax4.set_ylabel("Frequency", fontweight="bold")
            ax4.set_title(f"MRR Distribution (n={len(mrr_scores)})", fontweight="bold", fontsize=12)
            ax4.legend()
            ax4.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        output_path = self.output_dir / "metric_distributions.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Metric distributions visualization saved to: {output_path}")
        plt.close()

    def plot_retrieval_analysis(self):
        """Generate retrieval quality analysis."""
        # Extract MRR ranks
        ranks = []
        for eval_item in self.evaluations:
            mrr = eval_item.get("metrics", {}).get("mrr", {})
            rank = mrr.get("rank")
            if rank is not None:
                ranks.append(rank)

        if not ranks:
            print("⚠ No MRR rank data available for retrieval analysis")
            return

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle("Retrieval Quality Analysis (MRR)", fontsize=16, fontweight="bold")

        # 1. Rank Distribution
        ax1 = axes[0]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1

        sorted_ranks = sorted(rank_counts.keys())
        counts = [rank_counts[r] for r in sorted_ranks]

        colors = ["#27ae60" if r == 1 else "#3498db" if r <= 3 else "#f39c12" if r <= 5 else "#e74c3c"
                  for r in sorted_ranks]

        bars = ax1.bar(sorted_ranks, counts, color=colors, alpha=0.7, edgecolor="black")
        ax1.set_xlabel("Rank of First Relevant Document", fontweight="bold")
        ax1.set_ylabel("Frequency", fontweight="bold")
        ax1.set_title("Distribution of First Relevant Document Rank", fontweight="bold", fontsize=12)
        ax1.set_xticks(sorted_ranks)

        for bar, val in zip(bars, counts):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                str(val),
                ha="center",
                va="bottom",
                fontsize=9,
            )

        # 2. Cumulative Recall@K
        ax2 = axes[1]

        recall_at_k = {}
        for k in range(1, 11):
            recall_at_k[k] = sum(1 for r in ranks if r <= k) / len(ranks)

        k_values = list(recall_at_k.keys())
        recall_values = list(recall_at_k.values())

        ax2.plot(k_values, recall_values, marker="o", linewidth=2, markersize=8, color="#9b59b6")
        ax2.fill_between(k_values, recall_values, alpha=0.3, color="#9b59b6")
        ax2.set_xlabel("Top-K Retrieved Documents", fontweight="bold")
        ax2.set_ylabel("Recall@K", fontweight="bold")
        ax2.set_title("Cumulative Recall@K", fontweight="bold", fontsize=12)
        ax2.set_xticks(k_values)
        ax2.set_ylim(0, 1.05)
        ax2.grid(True, alpha=0.3)

        # Add value labels
        for k, recall in zip(k_values, recall_values):
            if k in [1, 3, 5, 10]:
                ax2.text(k, recall, f"{recall:.2%}", ha="center", va="bottom", fontsize=9, fontweight="bold")

        plt.tight_layout()
        output_path = self.output_dir / "retrieval_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Retrieval analysis visualization saved to: {output_path}")
        plt.close()

    def generate_all_visualizations(self):
        """Generate all visualizations."""
        print("\n" + "=" * 60)
        print("Q&A EVALUATION RESULTS VISUALIZATION")
        print("=" * 60 + "\n")

        print("Generating overall metrics visualization...")
        self.plot_overall_metrics()

        print("Generating chapter-wise analysis...")
        self.plot_by_chapter()

        print("Generating metric distributions...")
        self.plot_metric_distributions()

        print("Generating retrieval analysis...")
        self.plot_retrieval_analysis()

        print("\n" + "=" * 60)
        print("ALL VISUALIZATIONS GENERATED SUCCESSFULLY!")
        print(f"Output directory: {self.output_dir}")
        print("=" * 60 + "\n")

        # Print summary
        avg_metrics = self.summary["average_metrics"]
        print("SUMMARY:")
        print(f"  Total Questions:        {self.summary['total_questions']}")
        print(f"  Exact Match (MCQ):      {avg_metrics['exact_match']:.3f} ({avg_metrics['exact_match']*100:.1f}%)")
        print(f"  Answer Correctness:     {avg_metrics['answer_correctness']:.3f} ({avg_metrics['answer_correctness']*100:.1f}%)")
        print(f"  Citation Accuracy:      {avg_metrics['citation_accuracy']:.3f} ({avg_metrics['citation_accuracy']*100:.1f}%)")
        print(f"  MRR:                    {avg_metrics['mrr']:.3f}")
        print()


def main():
    """Main entry point."""
    # Get the results directory from command line or use default
    if len(sys.argv) > 1:
        results_dir = Path(sys.argv[1])
    else:
        # Default to run_on_306
        script_dir = Path(__file__).parent
        results_dir = script_dir / "results" / "run_on_306"

    if not results_dir.exists():
        print(f"Error: Results directory not found at {results_dir}")
        print(f"\nUsage: python {Path(__file__).name} [results_directory]")
        print(f"Example: python {Path(__file__).name} results/run_on_100")
        sys.exit(1)

    # Check if required files exist
    required_files = [
        results_dir / "evaluations.json",
        results_dir / "summary.json",
    ]

    for filepath in required_files:
        if not filepath.exists():
            print(f"Error: Required file not found: {filepath}")
            sys.exit(1)

    # Create visualizer and generate plots
    visualizer = QAResultsVisualizer(results_dir)
    visualizer.generate_all_visualizations()


if __name__ == "__main__":
    main()
