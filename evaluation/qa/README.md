# Q&A Evaluation

Evaluation of question answering with multiple metrics and flexible sampling.

## Files

```
qa/
├── eval_service.py           # Evaluation service
├── run_eval.py               # Runner script with sampling options
├── test_questions.json       # 306 questions (chapters 2-9)
└── results/
    ├── run_on_100/           # Sample of 100 questions
    └── run_on_306/           # Full dataset
        ├── evaluations.json  # Per-question results
        └── summary.json      # Aggregate statistics
```

## Dataset

- **Total**: 306 questions across chapters 2-9
- **Types**: 190 MCQ, 116 open-ended
- **Distribution**: Chapter 2 (66), Chapter 3 (32), Chapters 4-9 (208)

## Metrics

- **Exact Match** (MCQ): Perfect answer matching
- **Answer Correctness** (Open-ended): LLM-judged quality
- **Citation Accuracy**: Source video attribution correctness
- **MRR**: Mean Reciprocal Rank for retrieval quality

## Usage

```bash
# All 306 questions
python run_eval.py

# Sample 100 questions
python run_eval.py --n-questions 100

# Filter by chapters
python run_eval.py --chapters 2 3

# Random sampling
python run_eval.py --n-questions 20 --random
```

## Results

`results/run_on_306/` contains:
- `evaluations.json`: Detailed per-question metrics
- `summary.json`: Aggregate statistics by chapter and question type
