"""
Visualization script for video summary evaluation results.

This script generates visualization reports for evaluation runs, including:
1. QAG scores for all videos with averages
2. Alignment and coverage scores for all videos with averages
3. Cosine similarity scores for all videos with averages
4. Compression ratio (summary_chars / source_chars) with average

Usage:
    python visualize_results.py <run_folder_path>

Example:
    python visualize_results.py results/run_20251117_082859
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List
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


def create_qag_scores_chart(evaluations: Dict, output_path: Path):
    """Create chart showing QAG scores for all videos."""
    results = evaluations['results']
    # Filter out failed evaluations
    successful_results = [r for r in results if 'evaluation' in r]
    video_ids = [r['evaluation']['video_id'] for r in successful_results]
    qag_scores = [r['evaluation']['qag_score'] for r in successful_results]

    # Calculate average
    avg_qag = np.mean(qag_scores)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(video_ids))

    # Create bars
    bars = ax.bar(x, qag_scores, alpha=0.8, color='#e67e22', edgecolor='#d35400', linewidth=0.5)

    # Add average line
    ax.axhline(y=avg_qag, color='#d35400', linestyle='--', linewidth=2,
               label=f'Average QAG: {avg_qag:.3f}')

    # Customize chart
    ax.set_xlabel('Video ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('QAG Score', fontsize=12, fontweight='bold')
    ax.set_title('QAG Scores for All Videos', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(video_ids, rotation=45, ha='right', fontsize=8)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle=':')
    ax.set_ylim(0, 1.05)

    # Add value labels on bars (only for scores below 0.5)
    for i, (bar, score) in enumerate(zip(bars, qag_scores)):
        if score < 0.5:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{score:.2f}', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created QAG scores chart: {output_path}")


def create_alignment_coverage_chart(evaluations: Dict, output_path: Path):
    """Create chart showing alignment and coverage scores for all videos."""
    results = evaluations['results']
    # Filter out failed evaluations
    successful_results = [r for r in results if 'evaluation' in r]
    video_ids = [r['evaluation']['video_id'] for r in successful_results]
    alignment_scores = [r['evaluation']['alignment_score'] for r in successful_results]
    coverage_scores = [r['evaluation']['coverage_score'] for r in successful_results]

    # Calculate averages
    avg_alignment = np.mean(alignment_scores)
    avg_coverage = np.mean(coverage_scores)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(video_ids))
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
    ax.set_xlabel('Video ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Alignment and Coverage Scores for All Videos', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(video_ids, rotation=45, ha='right', fontsize=8)
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


def create_cosine_similarity_chart(evaluations: Dict, output_path: Path):
    """Create chart showing cosine similarity scores for all videos."""
    results = evaluations['results']
    # Filter out failed evaluations
    successful_results = [r for r in results if 'evaluation' in r]
    video_ids = [r['evaluation']['video_id'] for r in successful_results]
    cosine_scores = [r['evaluation']['cosine_similarity'] for r in successful_results]

    # Calculate average
    avg_cosine = np.mean(cosine_scores)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(video_ids))

    # Create bars
    bars = ax.bar(x, cosine_scores, alpha=0.8, color='#9b59b6', edgecolor='#8e44ad', linewidth=0.5)

    # Add average line
    ax.axhline(y=avg_cosine, color='#8e44ad', linestyle='--', linewidth=2,
               label=f'Average Cosine Similarity: {avg_cosine:.3f}')

    # Customize chart
    ax.set_xlabel('Video ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Cosine Similarity', fontsize=12, fontweight='bold')
    ax.set_title('Cosine Similarity Scores for All Videos', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(video_ids, rotation=45, ha='right', fontsize=8)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle=':')
    ax.set_ylim(0, 1.05)

    # Add value labels on bars (only for scores below 0.5)
    for i, (bar, score) in enumerate(zip(bars, cosine_scores)):
        if score < 0.5:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{score:.2f}', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created cosine similarity chart: {output_path}")


def create_compression_ratio_chart(evaluations: Dict, output_path: Path):
    """Create chart showing compression ratios for all videos."""
    results = evaluations['results']
    # Filter out failed evaluations
    successful_results = [r for r in results if 'evaluation' in r]
    video_ids = [r['evaluation']['video_id'] for r in successful_results]
    compression_ratios = [r['evaluation']['compression_ratio'] for r in successful_results]

    avg_ratio = np.mean(compression_ratios)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(video_ids))

    # Create bars
    bars = ax.bar(x, compression_ratios, alpha=0.8, color='#e74c3c', edgecolor='#c0392b', linewidth=0.5)

    # Add average line
    ax.axhline(y=avg_ratio, color='#c0392b', linestyle='--', linewidth=2,
               label=f'Average Ratio: {avg_ratio:.3f}')

    # Customize chart
    ax.set_xlabel('Video ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Compression Ratio (summary/source)', fontsize=12, fontweight='bold')
    ax.set_title('Compression Ratio for All Videos', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(video_ids, rotation=45, ha='right', fontsize=8)
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

    # 1. QAG Scores Chart
    print("Creating QAG scores chart...")
    create_qag_scores_chart(
        evaluations,
        vis_folder / "1_qag_scores.png"
    )

    # 2. Alignment & Coverage Chart
    print("Creating alignment & coverage chart...")
    create_alignment_coverage_chart(
        evaluations,
        vis_folder / "2_alignment_coverage_scores.png"
    )

    # 3. Cosine Similarity Chart
    print("Creating cosine similarity chart...")
    create_cosine_similarity_chart(
        evaluations,
        vis_folder / "3_cosine_similarity.png"
    )

    # 4. Compression Ratio Chart
    print("Creating compression ratio chart...")
    create_compression_ratio_chart(
        evaluations,
        vis_folder / "4_compression_ratios.png"
    )

    # Create summary statistics file
    print("\nCreating summary statistics file...")

    results = evaluations['results']
    # Filter out failed evaluations
    successful_results = [r for r in results if 'evaluation' in r]
    qag_scores = [r['evaluation']['qag_score'] for r in successful_results]
    alignment_scores = [r['evaluation']['alignment_score'] for r in successful_results]
    coverage_scores = [r['evaluation']['coverage_score'] for r in successful_results]
    cosine_scores = [r['evaluation']['cosine_similarity'] for r in successful_results]
    compression_ratios = [r['evaluation']['compression_ratio'] for r in successful_results]

    summary_stats = {
        "run_id": evaluations['run_id'],
        "config": evaluations['config'],
        "total_videos": evaluations['stats']['total'],
        "successful_evaluations": evaluations['stats']['success'],
        "qag_score": {
            "mean": float(np.mean(qag_scores)),
            "min": float(np.min(qag_scores)),
            "max": float(np.max(qag_scores)),
            "median": float(np.median(qag_scores)),
            "std": float(np.std(qag_scores)),
        },
        "alignment_score": {
            "mean": float(np.mean(alignment_scores)),
            "min": float(np.min(alignment_scores)),
            "max": float(np.max(alignment_scores)),
            "median": float(np.median(alignment_scores)),
            "std": float(np.std(alignment_scores)),
        },
        "coverage_score": {
            "mean": float(np.mean(coverage_scores)),
            "min": float(np.min(coverage_scores)),
            "max": float(np.max(coverage_scores)),
            "median": float(np.median(coverage_scores)),
            "std": float(np.std(coverage_scores)),
        },
        "cosine_similarity": {
            "mean": float(np.mean(cosine_scores)),
            "min": float(np.min(cosine_scores)),
            "max": float(np.max(cosine_scores)),
            "median": float(np.median(cosine_scores)),
            "std": float(np.std(cosine_scores)),
        },
        "compression_ratio": {
            "mean": float(np.mean(compression_ratios)),
            "min": float(np.min(compression_ratios)),
            "max": float(np.max(compression_ratios)),
            "median": float(np.median(compression_ratios)),
            "std": float(np.std(compression_ratios)),
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
    print(f"  QAG Score          : {summary_stats['qag_score']['mean']:.3f} "
          f"(min: {summary_stats['qag_score']['min']:.3f}, max: {summary_stats['qag_score']['max']:.3f}, "
          f"median: {summary_stats['qag_score']['median']:.3f}, std: {summary_stats['qag_score']['std']:.3f})")
    print(f"  Alignment Score    : {summary_stats['alignment_score']['mean']:.3f} "
          f"(min: {summary_stats['alignment_score']['min']:.3f}, max: {summary_stats['alignment_score']['max']:.3f}, "
          f"median: {summary_stats['alignment_score']['median']:.3f}, std: {summary_stats['alignment_score']['std']:.3f})")
    print(f"  Coverage Score     : {summary_stats['coverage_score']['mean']:.3f} "
          f"(min: {summary_stats['coverage_score']['min']:.3f}, max: {summary_stats['coverage_score']['max']:.3f}, "
          f"median: {summary_stats['coverage_score']['median']:.3f}, std: {summary_stats['coverage_score']['std']:.3f})")
    print(f"  Cosine Similarity  : {summary_stats['cosine_similarity']['mean']:.3f} "
          f"(min: {summary_stats['cosine_similarity']['min']:.3f}, max: {summary_stats['cosine_similarity']['max']:.3f}, "
          f"median: {summary_stats['cosine_similarity']['median']:.3f}, std: {summary_stats['cosine_similarity']['std']:.3f})")
    print(f"  Compression Ratio  : {summary_stats['compression_ratio']['mean']:.3f} "
          f"(min: {summary_stats['compression_ratio']['min']:.3f}, max: {summary_stats['compression_ratio']['max']:.3f}, "
          f"median: {summary_stats['compression_ratio']['median']:.3f}, std: {summary_stats['compression_ratio']['std']:.3f})")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python visualize_results.py <run_folder_path>")
        print("\nExample:")
        print("  python visualize_results.py results/run_20251117_082859")
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
