"""
Script to calculate and add cosine similarity scores to existing text summary evaluations.

This script:
1. Reads generations.json to get original texts and summaries
2. Calculates cosine similarity between each pair
3. Updates evaluations.json with the new similarity scores (in place)

Usage:
    python add_cosine_similarity.py <run_folder_path>

Example:
    python add_cosine_similarity.py results/run_20251114_182637
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_cosine_similarity(text1: str, text2: str) -> float:
    """Calculate cosine similarity between two texts using TF-IDF."""
    if not text1 or not text2:
        return 0.0

    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except Exception as e:
        print(f"Error calculating similarity: {e}")
        return 0.0


def load_generations(run_folder: Path) -> Dict:
    """Load generations.json from run folder."""
    gen_path = run_folder / "generations.json"

    if not gen_path.exists():
        raise FileNotFoundError(f"generations.json not found in {run_folder}")

    with open(gen_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_evaluations(run_folder: Path) -> Dict:
    """Load evaluations.json from run folder."""
    eval_path = run_folder / "evaluations.json"

    if not eval_path.exists():
        raise FileNotFoundError(f"evaluations.json not found in {run_folder}")

    with open(eval_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_evaluations(run_folder: Path, evaluations: Dict):
    """Save updated evaluations.json."""
    eval_path = run_folder / "evaluations.json"

    with open(eval_path, 'w', encoding='utf-8') as f:
        json.dump(evaluations, f, indent=2, ensure_ascii=False)


def add_cosine_similarities(run_folder: Path):
    """Add cosine similarity scores to evaluations.json."""
    print(f"\n{'='*60}")
    print(f"Adding cosine similarities to: {run_folder.name}")
    print(f"{'='*60}\n")

    # Load data
    print("Loading generations and evaluations...")
    generations = load_generations(run_folder)
    evaluations = load_evaluations(run_folder)

    # Create mapping from question_id to generation data
    gen_map = {gen['question_id']: gen for gen in generations['generations']}

    # Calculate and add cosine similarities
    print("Calculating cosine similarities...")
    similarities = []

    for i, score_entry in enumerate(evaluations['scores']):
        question_id = score_entry['question_id']

        if question_id not in gen_map:
            print(f"  Warning: No generation found for {question_id}, skipping...")
            continue

        gen_data = gen_map[question_id]
        original_text = gen_data['original_text']
        summary = gen_data['summary']

        # Calculate cosine similarity
        cosine_sim = calculate_cosine_similarity(original_text, summary)
        similarities.append(cosine_sim)

        # Add to evaluations
        evaluations['scores'][i]['cosine_similarity'] = round(cosine_sim, 4)

        print(f"  {question_id}: {cosine_sim:.4f}")

    # Calculate statistics
    if similarities:
        cosine_stats = {
            "mean": float(np.mean(similarities)),
            "min": float(np.min(similarities)),
            "max": float(np.max(similarities)),
            "median": float(np.median(similarities)),
            "std": float(np.std(similarities))
        }

        # Add to statistics section
        evaluations['statistics']['cosine_similarity'] = cosine_stats

    # Save updated evaluations
    print("\nSaving updated evaluations...")
    save_evaluations(run_folder, evaluations)

    print(f"\n{'='*60}")
    print(f"✓ Successfully added cosine similarities!")
    print(f"{'='*60}\n")

    # Print statistics
    if similarities:
        print("Cosine Similarity Statistics:")
        print(f"  Mean   : {cosine_stats['mean']:.4f}")
        print(f"  Median : {cosine_stats['median']:.4f}")
        print(f"  Min    : {cosine_stats['min']:.4f}")
        print(f"  Max    : {cosine_stats['max']:.4f}")
        print(f"  Std    : {cosine_stats['std']:.4f}")
        print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python add_cosine_similarity.py <run_folder_path>")
        print("\nExample:")
        print("  python add_cosine_similarity.py results/run_20251114_182637")
        sys.exit(1)

    run_folder = Path(sys.argv[1])

    if not run_folder.exists():
        print(f"Error: Run folder not found: {run_folder}")
        sys.exit(1)

    if not run_folder.is_dir():
        print(f"Error: Path is not a directory: {run_folder}")
        sys.exit(1)

    add_cosine_similarities(run_folder)


if __name__ == "__main__":
    main()
