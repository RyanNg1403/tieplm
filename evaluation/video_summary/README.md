# Video Summary Evaluation

Evaluation of video summarization using QAG metrics and cosine similarity.

## Files

```
video_summary/
├── eval_service.py               # Evaluation service with QAG
├── run_eval.py                   # Runner script
├── visualize_results.py          # Generate visualizations
└── results/
    └── final_results_on_62_videos/
        ├── evaluations.json      # Per-video evaluation results
        └── visualizations/
            └── summary_statistics.json
```

## Dataset

- **Videos**: 62 total
- **Source**: Full video transcripts
- **QAG Questions**: 15 per video

## Metrics

- **QAG**: Coverage and Alignment scores (15 questions per video)
- **Cosine Similarity**: Semantic similarity between transcript and summary
- **Compression Ratio**: Summary length vs transcript length

## Usage

```bash
# Run evaluation on all 62 videos
python run_eval.py

# Limit to first N videos
python run_eval.py --limit 10

# Custom number of QAG questions
python run_eval.py --n-questions 20

# Generate visualizations
python visualize_results.py
```

## Results

`results/final_results_on_62_videos/evaluations.json` contains:
- Per-video QAG scores (coverage, alignment)
- Cosine similarity scores
- Compression ratios
- Aggregate statistics
