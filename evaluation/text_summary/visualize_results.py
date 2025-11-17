"""
Visualization script for text summary evaluation results.

This script generates visualization reports for evaluation runs, including:
1. Alignment and coverage scores for all 50 questions with averages
2. Compression ratio (summary_chars / original_text_chars) with average

Usage:
    python visualize_results.py <run_folder_path>

Example:
    python visualize_results.py results/run_20251114_182637
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np


def load_evaluation_data(run_folder: Path) -> Dict:
    """Load evaluations.json from a run folder."""
    eval_path = run_folder / "evaluations.json"

    if not eval_path.exists():
        raise FileNotFoundError(f"evaluations.json not found in {run_folder}")

    with open(eval_path, 'r', encoding='utf-8') as f:
        evaluations = json.load(f)

    return evaluations


def create_alignment_coverage_chart(evaluations: Dict, output_path: Path):
    """Create chart showing alignment and coverage scores for all questions."""
    scores = evaluations['scores']
    question_ids = [s['question_id'] for s in scores]
    alignment_scores = [s['alignment_score'] for s in scores]
    coverage_scores = [s['coverage_score'] for s in scores]

    # Calculate averages
    avg_alignment = evaluations['statistics']['alignment']['mean']
    avg_coverage = evaluations['statistics']['coverage']['mean']

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(question_ids))
    width = 0.35

    # Create bars
    bars1 = ax.bar(x - width/2, alignment_scores, width, label='Alignment Score', alpha=0.8, color='#3498db')
    bars2 = ax.bar(x + width/2, coverage_scores, width, label='Coverage Score', alpha=0.8, color='#2ecc71')

    # Add average lines
    ax.axhline(y=avg_alignment, color='#2980b9', linestyle='--', linewidth=2,
               label=f'Avg Alignment: {avg_alignment:.3f}')
    ax.axhline(y=avg_coverage, color='#27ae60', linestyle='--', linewidth=2,
               label=f'Avg Coverage: {avg_coverage:.3f}')

    # Customize chart
    ax.set_xlabel('Question ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Alignment and Coverage Scores for All Questions', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(question_ids, rotation=45, ha='right', fontsize=8)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle=':')
    ax.set_ylim(0, 1.05)

    # Add value labels on bars (only for scores below 0.5)
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        height1 = bar1.get_height()
        height2 = bar2.get_height()
        if height1 < 0.5:
            ax.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.02,
                   f'{height1:.2f}', ha='center', va='bottom', fontsize=7)
        if height2 < 0.5:
            ax.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.02,
                   f'{height2:.2f}', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created alignment & coverage chart: {output_path}")


def create_compression_ratio_chart(evaluations: Dict, output_path: Path):
    """Create chart showing compression ratios for all questions."""
    scores = evaluations['scores']
    question_ids = [s['question_id'] for s in scores]

    # Calculate compression ratios
    compression_ratios = []
    for s in scores:
        ratio = s['summary_chars'] / s['original_text_chars'] if s['original_text_chars'] > 0 else 0
        compression_ratios.append(ratio)

    avg_ratio = np.mean(compression_ratios)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(question_ids))

    # Create bars
    bars = ax.bar(x, compression_ratios, alpha=0.8, color='#e74c3c', edgecolor='#c0392b', linewidth=0.5)

    # Add average line
    ax.axhline(y=avg_ratio, color='#c0392b', linestyle='--', linewidth=2,
               label=f'Average Ratio: {avg_ratio:.3f}')

    # Customize chart
    ax.set_xlabel('Question ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Compression Ratio (summary/source)', fontsize=12, fontweight='bold')
    ax.set_title('Compression Ratio for All Questions', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(question_ids, rotation=45, ha='right', fontsize=8)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle=':')

    # Add value labels on bars (only for outliers)
    for i, (bar, ratio) in enumerate(zip(bars, compression_ratios)):
        if ratio > avg_ratio * 1.2 or ratio < avg_ratio * 0.8:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{ratio:.2f}', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created compression ratio chart: {output_path}")




def generate_visualizations(run_folder: Path):
    """Generate all visualizations for a run folder."""
    print(f"\n{'='*60}")
    print(f"Generating visualizations for: {run_folder.name}")
    print(f"{'='*60}\n")

    # Load data
    print("Loading evaluation data...")
    evaluations = load_evaluation_data(run_folder)

    # Create visualizations folder inside run folder
    vis_folder = run_folder / "visualizations"
    vis_folder.mkdir(exist_ok=True)

    # 1. Alignment & Coverage Chart
    print("Creating alignment & coverage chart...")
    create_alignment_coverage_chart(
        evaluations,
        vis_folder / "1_alignment_coverage_scores.png"
    )

    # 2. Compression Ratio Chart
    print("Creating compression ratio chart...")
    create_compression_ratio_chart(
        evaluations,
        vis_folder / "2_compression_ratios.png"
    )

    # Create summary statistics file
    print("\nCreating summary statistics file...")
    summary_stats = {
        "run_id": evaluations['run_info']['run_id'],
        "timestamp": evaluations['run_info']['timestamp'],
        "total_questions": evaluations['run_info']['total_questions'],
        "alignment": {
            "mean": evaluations['statistics']['alignment']['mean'],
            "min": evaluations['statistics']['alignment']['min'],
            "max": evaluations['statistics']['alignment']['max'],
        },
        "coverage": {
            "mean": evaluations['statistics']['coverage']['mean'],
            "min": evaluations['statistics']['coverage']['min'],
            "max": evaluations['statistics']['coverage']['max'],
        },
        "compression_ratio": {
            "mean": float(np.mean([s['summary_chars'] / s['original_text_chars']
                                   for s in evaluations['scores']])),
            "min": float(min([s['summary_chars'] / s['original_text_chars']
                             for s in evaluations['scores']])),
            "max": float(max([s['summary_chars'] / s['original_text_chars']
                             for s in evaluations['scores']])),
        }
    }

    with open(vis_folder / "summary_statistics.json", 'w', encoding='utf-8') as f:
        json.dump(summary_stats, f, indent=2, ensure_ascii=False)

    print(f"✓ Created summary statistics: {vis_folder / 'summary_statistics.json'}")

    print(f"\n{'='*60}")
    print(f"✓ All visualizations saved to: {vis_folder}")
    print(f"{'='*60}\n")

    # Print summary
    print("Summary Statistics:")
    print(f"  Alignment Score    : {summary_stats['alignment']['mean']:.3f} "
          f"(min: {summary_stats['alignment']['min']:.3f}, max: {summary_stats['alignment']['max']:.3f})")
    print(f"  Coverage Score     : {summary_stats['coverage']['mean']:.3f} "
          f"(min: {summary_stats['coverage']['min']:.3f}, max: {summary_stats['coverage']['max']:.3f})")
    print(f"  Compression Ratio  : {summary_stats['compression_ratio']['mean']:.3f} "
          f"(min: {summary_stats['compression_ratio']['min']:.3f}, max: {summary_stats['compression_ratio']['max']:.3f})")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python visualize_results.py <run_folder_path>")
        print("\nExample:")
        print("  python visualize_results.py results/run_20251114_182637")
        print("\nOr to visualize all runs:")
        print("  python visualize_results.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Visualize all runs in results folder
        results_dir = Path(__file__).parent / "results"
        if not results_dir.exists():
            print(f"Error: Results directory not found: {results_dir}")
            sys.exit(1)

        run_folders = [f for f in results_dir.iterdir() if f.is_dir() and f.name.startswith('run_')]
        if not run_folders:
            print(f"Error: No run folders found in {results_dir}")
            sys.exit(1)

        print(f"Found {len(run_folders)} run folder(s)")
        for run_folder in sorted(run_folders):
            try:
                generate_visualizations(run_folder)
            except Exception as e:
                print(f"Error processing {run_folder.name}: {e}")
                continue
    else:
        # Visualize single run
        run_folder = Path(sys.argv[1])
        if not run_folder.exists():
            print(f"Error: Run folder not found: {run_folder}")
            sys.exit(1)

        generate_visualizations(run_folder)


if __name__ == "__main__":
    main()
