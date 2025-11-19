# Q&A Evaluation

Evaluation framework for the Q&A task with support for multiple metrics and flexible question sampling.

## Features

- **Metrics**:
  - **Exact Match** (MCQ only): Checks if predicted answer matches ground truth
  - **Answer Correctness** (Open-ended only): LLM-as-Judge combining cosine similarity (30%) and LLM score (70%)
  - **Citation Accuracy**: Checks if ground truth video is in retrieved chunks
  - **MRR (Mean Reciprocal Rank)**: Rank of first relevant chunk from source video

- **Question Types**:
  - Multiple Choice Questions (MCQ) - when `"Phương án (nếu có)"` has options
  - Open-ended Questions - when `"Phương án (nếu có)"` is null

- **Flexible Sampling**:
  - Sample specific number of questions (`--n-questions`)
  - Random sampling (`--random`)
  - Filter by chapters (`--chapters`)

## Usage

### Basic Usage

Run evaluation on all questions:
```bash
python run_eval.py
```

### Filter by Chapters

Evaluate only questions from Chương 2 and 3:
```bash
python run_eval.py --chapters 2 3
```

### Sample Questions

Evaluate first 10 questions from Chương 2:
```bash
python run_eval.py --n-questions 10 --chapters 2
```

### Random Sampling

Randomly sample 20 questions from Chương 2 and 3:
```bash
python run_eval.py --n-questions 20 --random --chapters 2 3
```

### Custom Output Directory

```bash
python run_eval.py --output-dir my_results --n-questions 5 --chapters 2
```

## Arguments

- `--test-file`: Path to test questions JSON file (default: `test_questions.json`)
- `--output-dir`: Output directory for results (default: `results/run_TIMESTAMP`)
- `--n-questions`: Number of questions to evaluate (default: all questions)
- `--random`: Randomly sample n questions instead of taking first n
- `--chapters`: Filter by chapters (e.g., `--chapters 2 3` for Chương 2 and 3)

## Test Data Format

The `test_questions.json` file follows this format:

```json
[
    {
        "Chương": 2,
        "Nội dung câu hỏi": "Question text...",
        "Phương án (nếu có)": "a) ... b) ... c) ... d) ..." or null,
        "Đáp án": "Answer text...",
        "Link Video": "https://youtu.be/...",
        "Timestamps": "00:00:30–00:00:50",
        "Video Title": "Video title..." (optional, only for Chương 2 and 3)
    }
]
```

## Output Files

Results are saved to the output directory:

- `evaluations.json`: Detailed results for each question
- `summary.json`: Aggregate statistics and metrics by chapter

## Example Output

```
============================================================
Q&A Evaluation Runner
============================================================
📝 Total questions: 20
📚 Filtered by chapters: [2, 3]
🎲 Random sampling: Yes
💾 Output directory: results/run_20251117_123456
============================================================

[1/20] Evaluating question from Chapter 2...
❓ Trong mô hình máy học có giám sát tổng quát, giá trị dự đoán y~​...
  📚 Retrieving chunks...
  🔄 Reranking to top 10...
  🤖 Generating answer with LLM...
  📊 Calculating metrics...
  ✅ Exact Match: 1.000 (Predicted: b, GT: b)
  📎 Citation Accuracy: 1.000 (GT in retrieved: True)
  🎯 MRR: 1.000 (Rank: 1)

...

============================================================
✅ Evaluation Complete!
============================================================
📊 Summary Statistics:
  • Exact Match (MCQ): 0.850
  • Answer Correctness: 0.742
  • Citation Accuracy: 0.900
  • MRR (Mean Reciprocal Rank): 0.815
```

## Dataset Statistics

Total questions: 306
- Chương 2: 66 questions
- Chương 3: 32 questions
- Chương 4: 22 questions
- Chương 5: 18 questions
- Chương 6: 45 questions
- Chương 7: 45 questions
- Chương 8: 38 questions
- Chương 9: 40 questions

Question types:
- MCQ (with options): 190
- Open-ended (null options): 116

Chương 2 & 3 (with Video Titles): 98 questions
