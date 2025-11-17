# Video Summary Evaluation

This directory contains the evaluation service for video summarization tasks using QAG (Question-Answer Generation) metrics and cosine similarity.

## Overview

The evaluation service assesses video summaries based on:

1. **QAG (Question-Answer Generation)**:
   - Generates 15 closed-ended questions from the video transcript
   - Measures **Coverage**: How much detail from the transcript is included in the summary
   - Measures **Alignment**: Factual alignment between transcript and summary
   - Overall score is the minimum of coverage and alignment

2. **Cosine Similarity**:
   - Computes semantic similarity between the full transcript and summary
   - Uses OpenAI embeddings (text-embedding-3-small by default)
   - Handles long transcripts by chunking and averaging embeddings

3. **Character Counts**:
   - Tracks source (transcript) and summary lengths
   - Computes compression ratio

## Files

- **`eval_service.py`**: Core evaluation logic with `VideoSummaryEvaluator` class
- **`run_eval.py`**: Script to evaluate all video summaries from the database
- **`test_eval.py`**: Quick test script with sample data
- **`results/`**: Directory where evaluation results are saved

## Usage

### 1. Test the Evaluation Service

Run a quick test with sample data:

```bash
cd /Users/PhatNguyen/Desktop/tieplm
python3 evaluation/video_summary/test_eval.py
```

### 2. Evaluate All Video Summaries

Evaluate all video summaries stored in the database:

```bash
cd /Users/PhatNguyen/Desktop/tieplm
python3 evaluation/video_summary/run_eval.py
```

**Options:**
- `--limit N`: Evaluate only the first N summaries
- `--n-questions N`: Number of QAG questions to generate (default: 15)
- `--results-dir DIR`: Directory to save results (default: `results`)

**Examples:**
```bash
# Evaluate first 5 summaries
python3 evaluation/video_summary/run_eval.py --limit 5

# Use 20 QAG questions instead of 15
python3 evaluation/video_summary/run_eval.py --n-questions 20

# Evaluate first 3 summaries with 10 questions
python3 evaluation/video_summary/run_eval.py --limit 3 --n-questions 10
```

### 3. Use Programmatically

```python
from evaluation.video_summary.eval_service import get_video_summary_evaluator

# Initialize evaluator with 15 questions
evaluator = get_video_summary_evaluator(n_questions=15)

# Evaluate a summary
result = evaluator.evaluate_summary(
    video_id="video_001",
    summary="Your generated summary...",
    transcript="Full video transcript..."
)

# Access results
print(f"QAG Score: {result['qag_score']:.4f}")
print(f"Coverage: {result['coverage_score']:.4f}")
print(f"Alignment: {result['alignment_score']:.4f}")
print(f"Cosine Similarity: {result['cosine_similarity']:.4f}")
print(f"Compression Ratio: {result['compression_ratio']:.2%}")
```

## Results Format

Results are saved in `results/run_<timestamp>/evaluations.json`:

```json
{
  "run_id": "run_20250117_153045",
  "config": {
    "n_questions": 15,
    "limit": null
  },
  "stats": {
    "total": 10,
    "success": 10,
    "qag_sum": 7.23,
    "alignment_sum": 7.45,
    "coverage_sum": 7.01,
    "cosine_sum": 8.12
  },
  "results": [
    {
      "video_id": "video_001",
      "summary_preview": "Deep learning sử dụng neural networks...",
      "evaluation": {
        "video_id": "video_001",
        "qag_score": 0.7234,
        "coverage_score": 0.7012,
        "alignment_score": 0.7456,
        "cosine_similarity": 0.8123,
        "source_chars": 15234,
        "summary_chars": 3456,
        "compression_ratio": 0.2268,
        "n_questions": 15,
        "evaluation_model": "gpt-5-nano",
        "timestamp": "2025-01-17T15:30:45.123Z"
      }
    }
  ]
}
```

## Configuration

Set these environment variables in `.env`:

```bash
# Evaluation model for QAG
EVAL_MODEL=gpt-5-nano

# QAG threshold for success (default: 0.5)
EVAL_SUMMARIZATION_THRESHOLD=0.5

# OpenAI API key (required for embeddings and QAG)
OPENAI_API_KEY=your_api_key_here
```

## Comparison with Text Summary Evaluation

| Aspect | Text Summary | Video Summary |
|--------|-------------|---------------|
| **Source** | RAG-retrieved chunks | Full video transcript |
| **QAG Questions** | 10 | 15 (longer content) |
| **Retrieval** | Yes (with reranking) | No (uses full transcript) |
| **Cosine Similarity** | Not used | Yes (transcript vs summary) |
| **Character Tracking** | Basic | Detailed with compression ratio |

## Why 15 Questions?

Video transcripts are typically longer and more comprehensive than RAG-retrieved chunks, so we use:
- **15 questions** for video summaries (vs 10 for text summaries)
- This ensures adequate coverage of the broader content in video transcripts
- Provides more granular evaluation of both coverage and alignment

## Troubleshooting

**Error: "Transcript not found"**
- Ensure transcripts exist in `ingestion/transcripts/` directory
- Check that video_id matches the transcript filename or is contained in it

**Error: "Could not initialize OpenAI embedder"**
- Verify `OPENAI_API_KEY` is set in `.env`
- Check internet connection and OpenAI API status

**Low scores across all summaries**
- Check that summaries are actually generated (not empty)
- Verify transcripts loaded correctly
- Consider adjusting `EVAL_SUMMARIZATION_THRESHOLD` in `.env`
