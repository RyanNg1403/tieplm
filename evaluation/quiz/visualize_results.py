"""
Visualization script for quiz evaluation results.

Generates comprehensive plots for both MCQ and open-ended question evaluations,
including accuracy metrics, score distributions, and comparative analysis.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["font.size"] = 10


class QuizResultsVisualizer:
    """Visualizer for quiz evaluation results."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.mcq_dir = results_dir / "mcq"
        self.open_ended_dir = results_dir / "open_ended"

        # Load data
        self.mcq_data = self._load_json(self.mcq_dir / "evaluations.json")
        self.open_ended_data = self._load_json(
            self.open_ended_dir / "evaluations.json"
        )

        # Output directory for plots
        self.output_dir = results_dir / "visualizations"
        self.output_dir.mkdir(exist_ok=True)

    def _load_json(self, filepath: Path) -> Dict[str, Any]:
        """Load JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def plot_mcq_results(self):
        """Generate visualizations for MCQ evaluation results."""
        scores = [item["score"] for item in self.mcq_data["scores"]]
        stats = self.mcq_data["statistics"]
        run_info = self.mcq_data["run_info"]

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(
            f"MCQ Evaluation Results - {run_info['total_cases']} Questions",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Accuracy Bar Chart
        ax1 = axes[0, 0]
        correct = sum(scores)
        incorrect = len(scores) - correct
        categories = ["Correct", "Incorrect"]
        values = [correct, incorrect]
        colors = ["#2ecc71", "#e74c3c"]

        bars = ax1.bar(categories, values, color=colors, alpha=0.7, edgecolor="black")
        ax1.set_ylabel("Number of Questions", fontweight="bold")
        ax1.set_title("MCQ Accuracy Overview", fontweight="bold", fontsize=12)
        ax1.set_ylim(0, max(values) * 1.2)

        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{val}\n({val/len(scores)*100:.1f}%)",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # 2. Score Distribution
        ax2 = axes[0, 1]
        unique, counts = np.unique(scores, return_counts=True)
        ax2.bar(unique, counts, color="#3498db", alpha=0.7, edgecolor="black", width=0.4)
        ax2.set_xlabel("Score (0=Wrong, 1=Correct)", fontweight="bold")
        ax2.set_ylabel("Frequency", fontweight="bold")
        ax2.set_title("Score Distribution", fontweight="bold", fontsize=12)
        ax2.set_xticks([0, 1])

        # Add counts on bars
        for x, count in zip(unique, counts):
            ax2.text(x, count, str(count), ha="center", va="bottom", fontweight="bold")

        # 3. Statistics Summary
        ax3 = axes[1, 0]
        ax3.axis("off")

        stats_text = f"""
        STATISTICS SUMMARY
        ═══════════════════════════════

        Total Cases:        {run_info['total_cases']}
        Successful:         {run_info['successful_cases']}
        Failed:             {run_info['failed_cases']}

        Accuracy:           {stats['mean']*100:.1f}%
        Median Score:       {stats['median']}
        Min Score:          {stats['min']}
        Max Score:          {stats['max']}
        Std Deviation:      {stats['std']:.4f}

        Run ID:             {run_info['run_id']}
        Timestamp:          {run_info['timestamp']}
        """

        ax3.text(
            0.1,
            0.5,
            stats_text,
            fontsize=11,
            family="monospace",
            verticalalignment="center",
            bbox=dict(boxstyle="round", facecolor="#ecf0f1", alpha=0.8),
        )

        # 4. Cumulative Performance
        ax4 = axes[1, 1]
        cumulative_correct = np.cumsum(scores)
        questions = np.arange(1, len(scores) + 1)
        cumulative_accuracy = (cumulative_correct / questions) * 100

        ax4.plot(
            questions,
            cumulative_accuracy,
            linewidth=2,
            color="#9b59b6",
            marker="o",
            markersize=3,
            alpha=0.7,
        )
        ax4.axhline(
            y=stats["mean"] * 100,
            color="#e74c3c",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {stats['mean']*100:.1f}%",
        )
        ax4.set_xlabel("Question Number", fontweight="bold")
        ax4.set_ylabel("Cumulative Accuracy (%)", fontweight="bold")
        ax4.set_title("Cumulative Accuracy Over Questions", fontweight="bold", fontsize=12)
        ax4.legend(loc="lower right")
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 105)

        plt.tight_layout()
        output_path = self.output_dir / "mcq_evaluation_results.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ MCQ visualization saved to: {output_path}")
        plt.close()

    def plot_open_ended_results(self):
        """Generate visualizations for open-ended evaluation results."""
        similarities = [
            item["embedding_similarity"] for item in self.open_ended_data["scores"]
        ]
        stats = self.open_ended_data["statistics"]
        run_info = self.open_ended_data["run_info"]

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(
            f"Open-Ended Question Evaluation Results - {run_info['total_cases']} Questions",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Similarity Distribution (Histogram)
        ax1 = axes[0, 0]
        n, bins, patches = ax1.hist(
            similarities,
            bins=20,
            color="#16a085",
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

        ax1.axvline(
            stats["mean"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {stats['mean']:.3f}",
        )
        ax1.axvline(
            stats["median"],
            color="blue",
            linestyle="--",
            linewidth=2,
            label=f"Median: {stats['median']:.3f}",
        )
        ax1.set_xlabel("Embedding Similarity Score", fontweight="bold")
        ax1.set_ylabel("Frequency", fontweight="bold")
        ax1.set_title("Similarity Score Distribution", fontweight="bold", fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis="y")

        # 2. Box Plot
        ax2 = axes[0, 1]
        box = ax2.boxplot(
            similarities,
            vert=True,
            patch_artist=True,
            widths=0.5,
            showmeans=True,
            meanprops=dict(marker="D", markerfacecolor="red", markersize=8),
        )

        for patch in box["boxes"]:
            patch.set_facecolor("#3498db")
            patch.set_alpha(0.7)

        ax2.set_ylabel("Embedding Similarity Score", fontweight="bold")
        ax2.set_title("Similarity Score Box Plot", fontweight="bold", fontsize=12)
        ax2.set_xticklabels(["All Questions"])
        ax2.grid(True, alpha=0.3, axis="y")

        # Add statistics annotations
        stats_text = (
            f"Min: {stats['min']:.3f}\n"
            f"Q1: {np.percentile(similarities, 25):.3f}\n"
            f"Median: {stats['median']:.3f}\n"
            f"Q3: {np.percentile(similarities, 75):.3f}\n"
            f"Max: {stats['max']:.3f}"
        )
        ax2.text(
            1.3,
            stats["median"],
            stats_text,
            fontsize=9,
            verticalalignment="center",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

        # 3. Performance Categories
        ax3 = axes[1, 0]

        # Categorize scores
        excellent = sum(1 for s in similarities if s >= 0.85)
        good = sum(1 for s in similarities if 0.7 <= s < 0.85)
        fair = sum(1 for s in similarities if 0.5 <= s < 0.7)
        poor = sum(1 for s in similarities if s < 0.5)

        categories = ["Excellent\n(≥0.85)", "Good\n(0.70-0.85)", "Fair\n(0.50-0.70)", "Poor\n(<0.50)"]
        values = [excellent, good, fair, poor]
        colors = ["#27ae60", "#3498db", "#f39c12", "#e74c3c"]

        bars = ax3.bar(categories, values, color=colors, alpha=0.7, edgecolor="black")
        ax3.set_ylabel("Number of Questions", fontweight="bold")
        ax3.set_title("Performance Categories", fontweight="bold", fontsize=12)

        # Add value labels and percentages
        for bar, val in zip(bars, values):
            height = bar.get_height()
            if val > 0:
                ax3.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{val}\n({val/len(similarities)*100:.1f}%)",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                )

        # 4. Statistics Summary
        ax4 = axes[1, 1]
        ax4.axis("off")

        stats_text = f"""
        STATISTICS SUMMARY
        ═══════════════════════════════

        Total Cases:        {run_info['total_cases']}
        Successful:         {run_info['successful_cases']}
        Failed:             {run_info['failed_cases']}

        Mean Similarity:    {stats['mean']:.4f}
        Median:             {stats['median']:.4f}
        Min:                {stats['min']:.4f}
        Max:                {stats['max']:.4f}
        Std Deviation:      {stats['std']:.4f}

        25th Percentile:    {np.percentile(similarities, 25):.4f}
        75th Percentile:    {np.percentile(similarities, 75):.4f}

        Run ID:             {run_info['run_id']}
        Timestamp:          {run_info['timestamp']}
        """

        ax4.text(
            0.1,
            0.5,
            stats_text,
            fontsize=11,
            family="monospace",
            verticalalignment="center",
            bbox=dict(boxstyle="round", facecolor="#ecf0f1", alpha=0.8),
        )

        plt.tight_layout()
        output_path = self.output_dir / "open_ended_evaluation_results.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Open-ended visualization saved to: {output_path}")
        plt.close()

    def plot_comparison(self):
        """Generate comparison plots between MCQ and open-ended questions."""
        mcq_scores = [item["score"] for item in self.mcq_data["scores"]]
        oe_scores = [
            item["embedding_similarity"] for item in self.open_ended_data["scores"]
        ]

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle(
            "MCQ vs Open-Ended Question Performance Comparison",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Side-by-side comparison
        ax1 = axes[0]

        question_types = ["MCQ", "Open-Ended"]
        mean_scores = [
            self.mcq_data["statistics"]["mean"],
            self.open_ended_data["statistics"]["mean"],
        ]

        bars = ax1.bar(
            question_types,
            mean_scores,
            color=["#3498db", "#16a085"],
            alpha=0.7,
            edgecolor="black",
            width=0.5,
        )

        ax1.set_ylabel("Average Score", fontweight="bold")
        ax1.set_title("Average Performance by Question Type", fontweight="bold", fontsize=12)
        ax1.set_ylim(0, 1.1)

        # Add value labels
        for bar, val in zip(bars, mean_scores):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{val:.3f}\n({val*100:.1f}%)",
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=11,
            )

        ax1.grid(True, alpha=0.3, axis="y")

        # 2. Distribution comparison (Violin plot)
        ax2 = axes[1]

        data_to_plot = [mcq_scores, oe_scores]
        positions = [1, 2]

        parts = ax2.violinplot(
            data_to_plot,
            positions=positions,
            showmeans=True,
            showmedians=True,
            widths=0.7,
        )

        # Color the violin plots
        colors = ["#3498db", "#16a085"]
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)

        ax2.set_xticks(positions)
        ax2.set_xticklabels(question_types)
        ax2.set_ylabel("Score", fontweight="bold")
        ax2.set_title("Score Distribution Comparison", fontweight="bold", fontsize=12)
        ax2.grid(True, alpha=0.3, axis="y")
        ax2.set_ylim(-0.1, 1.1)

        plt.tight_layout()
        output_path = self.output_dir / "comparison_results.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Comparison visualization saved to: {output_path}")
        plt.close()

    def plot_detailed_analysis(self):
        """Generate detailed analysis plots."""
        similarities = [
            item["embedding_similarity"] for item in self.open_ended_data["scores"]
        ]

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle(
            "Detailed Open-Ended Question Analysis",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Question-by-Question Performance
        ax1 = axes[0]
        questions = range(1, len(similarities) + 1)

        colors = [
            "#27ae60" if s >= 0.85 else "#3498db" if s >= 0.7 else "#f39c12" if s >= 0.5 else "#e74c3c"
            for s in similarities
        ]

        ax1.scatter(questions, similarities, c=colors, alpha=0.6, s=50, edgecolors="black", linewidth=0.5)
        ax1.axhline(
            y=self.open_ended_data["statistics"]["mean"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {self.open_ended_data['statistics']['mean']:.3f}",
        )

        # Add threshold lines
        ax1.axhline(y=0.85, color="#27ae60", linestyle=":", alpha=0.5, label="Excellent (≥0.85)")
        ax1.axhline(y=0.70, color="#3498db", linestyle=":", alpha=0.5, label="Good (≥0.70)")
        ax1.axhline(y=0.50, color="#f39c12", linestyle=":", alpha=0.5, label="Fair (≥0.50)")

        ax1.set_xlabel("Question Number", fontweight="bold")
        ax1.set_ylabel("Embedding Similarity", fontweight="bold")
        ax1.set_title("Question-by-Question Performance", fontweight="bold", fontsize=12)
        ax1.legend(loc="lower right", fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 1.05)

        # 2. Cumulative Average
        ax2 = axes[1]
        cumulative_avg = np.cumsum(similarities) / np.arange(1, len(similarities) + 1)

        ax2.plot(questions, cumulative_avg, linewidth=2, color="#9b59b6", marker="o", markersize=3, alpha=0.7)
        ax2.axhline(
            y=self.open_ended_data["statistics"]["mean"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Final Mean: {self.open_ended_data['statistics']['mean']:.3f}",
        )
        ax2.fill_between(
            questions,
            cumulative_avg,
            self.open_ended_data["statistics"]["mean"],
            alpha=0.2,
            color="#9b59b6",
        )

        ax2.set_xlabel("Question Number", fontweight="bold")
        ax2.set_ylabel("Cumulative Average Similarity", fontweight="bold")
        ax2.set_title("Cumulative Performance Trend", fontweight="bold", fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 1.05)

        plt.tight_layout()
        output_path = self.output_dir / "detailed_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Detailed analysis visualization saved to: {output_path}")
        plt.close()

    def generate_all_visualizations(self):
        """Generate all visualizations."""
        print("\n" + "=" * 60)
        print("QUIZ EVALUATION RESULTS VISUALIZATION")
        print("=" * 60 + "\n")

        print("Generating MCQ visualizations...")
        self.plot_mcq_results()

        print("Generating Open-Ended visualizations...")
        self.plot_open_ended_results()

        print("Generating comparison visualizations...")
        self.plot_comparison()

        print("Generating detailed analysis...")
        self.plot_detailed_analysis()

        print("\n" + "=" * 60)
        print("ALL VISUALIZATIONS GENERATED SUCCESSFULLY!")
        print(f"Output directory: {self.output_dir}")
        print("=" * 60 + "\n")

        # Print summary
        print("SUMMARY:")
        print(f"  MCQ Accuracy:              {self.mcq_data['statistics']['mean']*100:.1f}%")
        print(f"  Open-Ended Avg Similarity: {self.open_ended_data['statistics']['mean']:.3f}")
        print(f"  Total Questions Evaluated: {self.mcq_data['run_info']['total_cases'] + self.open_ended_data['run_info']['total_cases']}")
        print()


def main():
    """Main entry point."""
    # Get the results directory
    script_dir = Path(__file__).parent
    results_dir = script_dir / "results"

    if not results_dir.exists():
        print(f"Error: Results directory not found at {results_dir}")
        sys.exit(1)

    # Check if required files exist
    required_files = [
        results_dir / "mcq" / "evaluations.json",
        results_dir / "open_ended" / "evaluations.json",
    ]

    for filepath in required_files:
        if not filepath.exists():
            print(f"Error: Required file not found: {filepath}")
            sys.exit(1)

    # Create visualizer and generate plots
    visualizer = QuizResultsVisualizer(results_dir)
    visualizer.generate_all_visualizations()


if __name__ == "__main__":
    main()
