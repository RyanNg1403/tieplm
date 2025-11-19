# Text Summary Evaluation

Evaluation of text summarization using QAG metrics and cosine similarity.

## Files

```
text_summary/
├── eval_service.py              # Evaluation service with QAG metrics
├── run_eval.py                  # Runner script
├── add_cosine_similarity.py     # Add cosine similarity to results
├── visualize_results.py         # Generate visualizations
├── test_questions.json          # 50 test questions (8 chapters)
└── results/
    ├── ms-marco-MiniLM-L-6-v2/  # Baseline reranker results
    ├── bge-reranker-v2-m3/      # BGE reranker results
    └── Vietnamese_Reranker/     # Vietnamese reranker results
        ├── evaluations.json     # Per-question evaluation results
        ├── generations.json     # Generated summaries
        └── visualizations/
            └── summary_statistics.json
```

## Metrics

- **QAG (Question-Answer Generation)**: Coverage and Alignment scores
- **Cosine Similarity**: Semantic similarity between retrieved chunks and summary
- **Compression Ratio**: Summary length vs source length

## Usage

```bash
# Run evaluation
python run_eval.py --all

# Add cosine similarity
python add_cosine_similarity.py

# Generate visualizations
python visualize_results.py
```

## Results

Each reranker comparison in `results/*/evaluations.json` contains:
- Per-question QAG scores (coverage, alignment)
- Cosine similarity scores
- Aggregate statistics
