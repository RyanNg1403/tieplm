# Quiz Generation Evaluation

Evaluation of quiz generation quality using answer validation metrics.

## Files

```
quiz/
├── eval_service.py       # Evaluation service
├── prompts.py            # Evaluation prompts
├── run_eval.py           # Runner script
└── results/
    ├── mcq/              # Multiple choice results
    │   ├── evaluations.json
    │   └── generations.json
    └── open_ended/       # Short-answer results
        ├── evaluations.json
        └── generations.json
```

## Evaluation Process

1. **Generate Quiz**: Random chunk sampling → quiz generation via quiz service
2. **Answer Questions**: QA service answers using context only
3. **Validate Answers**: Compare generated answers with ground truth

## Metrics

- **MCQ**: Accuracy (exact option match: A/B/C/D/IDK)
- **Short-Answer**: Cosine similarity between generated and ground truth answers

## Usage

```bash
# Run evaluation for both question types
python run_eval.py
```

## Results

Each result folder contains:
- `evaluations.json`: Per-question validation scores
- `generations.json`: Generated quiz questions and answers
