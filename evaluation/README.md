# Evaluation Module

Performance evaluation framework for all four AI tasks: Text Summary, Q&A, Video Summary, and Quiz Generation.

## Status: ✅ Complete

All four tasks have been evaluated with comprehensive metrics and datasets.

## Directory Structure

```
evaluation/
├── text_summary/
│   ├── eval_service.py
│   ├── run_eval.py
│   ├── add_cosine_similarity.py
│   ├── visualize_results.py
│   ├── test_questions.json          # 50 test questions
│   └── results/
│       ├── ms-marco-MiniLM-L-6-v2/  # Baseline reranker
│       ├── bge-reranker-v2-m3/      # BGE reranker
│       └── Vietnamese_Reranker/     # Vietnamese reranker
│           ├── evaluations.json
│           ├── generations.json
│           └── visualizations/
│               └── summary_statistics.json
├── qa/
│   ├── eval_service.py
│   ├── run_eval.py
│   ├── test_questions.json          # 306 test questions
│   └── results/
│       ├── run_on_100/              # 100 questions
│       └── run_on_306/              # Full dataset
│           ├── evaluations.json
│           └── summary.json
├── video_summary/
│   ├── eval_service.py
│   ├── run_eval.py
│   ├── visualize_results.py
│   └── results/
│       └── final_results_on_62_videos/
│           ├── evaluations.json
│           └── visualizations/
│               └── summary_statistics.json
└── quiz/
    ├── eval_service.py
    ├── prompts.py
    ├── run_eval.py
    └── results/
        ├── mcq/
        │   ├── evaluations.json
        │   └── generations.json
        └── open_ended/
            ├── evaluations.json
            └── generations.json
```

## Task Evaluations

### 1. Text Summary
**Metrics**: QAG (Question-Answer Generation), Cosine Similarity
- **Dataset**: 50 questions across 8 chapters
- **Reranker Comparison**: 3 models tested (ms-marco, BGE, Vietnamese)
- **Scores**: Coverage, Alignment, Compression Ratio
- **Results**: `text_summary/results/*/evaluations.json`

### 2. Q&A
**Metrics**: Exact Match, Answer Correctness, Citation Accuracy, MRR
- **Dataset**: 306 questions (190 MCQ, 116 open-ended) from chapters 2-9
- **Question Types**: Multiple choice and open-ended
- **Citation Tracking**: Video source accuracy
- **Results**: `qa/results/run_on_306/evaluations.json`

### 3. Video Summary
**Metrics**: QAG, Cosine Similarity
- **Dataset**: 62 videos
- **QAG Questions**: 15 per video
- **Comparison**: Transcript vs generated summary
- **Results**: `video_summary/results/final_results_on_62_videos/evaluations.json`

### 4. Quiz Generation
**Metrics**: Cosine Similarity (short-answer), Accuracy (MCQ)
- **Types**: Multiple choice and short-answer
- **Answer Validation**: Embedding similarity and exact match
- **Results**: `quiz/results/{mcq,open_ended}/evaluations.json`

## Usage

### Text Summary Evaluation
```bash
cd evaluation/text_summary
python run_eval.py --all
python visualize_results.py
```

### Q&A Evaluation
```bash
cd evaluation/qa
python run_eval.py                    # All 306 questions
python run_eval.py --n-questions 100  # Sample 100
python run_eval.py --chapters 2 3     # Filter by chapters
```

### Video Summary Evaluation
```bash
cd evaluation/video_summary
python run_eval.py
python visualize_results.py
```

### Quiz Evaluation
```bash
cd evaluation/quiz
python run_eval.py
```

## Results Files

Each evaluation produces:
- **evaluations.json**: Detailed per-item results
- **summary.json**: Aggregate statistics
- **generations.json**: Generated outputs (when applicable)
- **visualizations/**: Charts and summary statistics

## Evaluation Metrics

- **QAG**: Question-Answer Generation for summarization quality
- **Cosine Similarity**: Semantic similarity between texts
- **Exact Match**: Perfect answer matching (MCQ)
- **Answer Correctness**: LLM-judged answer quality (open-ended)
- **Citation Accuracy**: Source attribution correctness
- **MRR**: Mean Reciprocal Rank for retrieval quality
- **Compression Ratio**: Summary length vs source length

## Configuration

Add to `.env`:
```bash
EVAL_MODEL=gpt-5-mini
EVAL_SUMMARIZATION_THRESHOLD=0.5
```
