# Q&A Evaluation

Evaluation framework for the Q&A task using 4 key metrics.

## 📊 Evaluation Metrics

### 1. **Answer Correctness** (0-1, higher is better)
- **Embedding Similarity**: Cosine similarity between generated and ground truth answers
- **LLM Score**: GPT-5-mini evaluation of semantic correctness
- **Combined Score**: Weighted average (40% embedding + 60% LLM)

### 2. **Citation Accuracy** (0-1, higher is better)
- **Has Citations**: Presence of [1], [2], [3] citations
- **Valid Citations**: Citations match actual sources
- **Citation Coverage**: Percentage of sources cited
- **Accuracy Score**: Ratio of valid to total citations

### 3. **Source Relevance** (F1-score, 0-1, higher is better)
- **Video Match**: Retrieved sources match ground truth videos
- **Timestamp Overlap**: Retrieved chunks overlap with ground truth timestamps
- **Precision**: Relevant sources / Total retrieved
- **Recall**: Retrieved relevant / Total ground truth
- **F1 Score**: Harmonic mean of precision and recall

### 4. **Hallucination Rate** (0-1, lower is better)
- **LLM-based Detection**: GPT-5-mini checks for fabricated information
- **Grounding Check**: Verifies all claims exist in sources
- **Hallucination Examples**: Specific instances of hallucination

---

## 🚀 Quick Start

### 1. Prepare Test Questions

Create `test_questions.json` with ground truth data:

```json
[
  {
    "chapter": "7",
    "question": "RNN là viết tắt của thuật ngữ gì trong học sâu?",
    "options": null,
    "answer": "RNN là tên viết tắt của mạng Recurrent Neural Network.",
    "video_urls": ["https://youtu.be/_KvZN8-SyvQ"],
    "timestamps": ["00:00:10 - 00:00:40"]
  }
]
```

### 2. Run Evaluation

```bash
# Full evaluation (all questions)
cd evaluation/qa
python run_eval.py

# Evaluate specific chapter
python run_eval.py --chapter 7

# Limit number of questions
python run_eval.py --limit 5

# Custom test file
python run_eval.py --test-file my_questions.json --output-dir my_results/
```

### 3. View Results

Results are saved in `evaluation/qa/results/run_TIMESTAMP/`:
- `evaluations.json`: Individual question evaluations
- `summary.json`: Aggregated statistics

---

## 📁 Project Structure

```
evaluation/qa/
├── README.md                  # This file
├── __init__.py                # Python package init
├── eval_service.py            # Core evaluation logic
├── run_eval.py                # CLI runner script
├── test_questions.json        # Ground truth test questions
└── results/                   # Evaluation results
    ├── run_20251116_140530/
    │   ├── evaluations.json
    │   └── summary.json
    └── ...
```

---

## 📋 Example Output

### Summary Statistics

```json
{
  "total_questions": 8,
  "successful_evaluations": 8,
  "failed_evaluations": 0,
  "average_metrics": {
    "answer_correctness": 0.8234,
    "citation_accuracy": 0.9500,
    "source_relevance_f1": 0.7821,
    "hallucination_score": 0.1200
  },
  "by_chapter": {
    "7": {
      "count": 8,
      "answer_correctness": 0.8234,
      "citation_accuracy": 0.9500,
      "source_relevance_f1": 0.7821,
      "hallucination_score": 0.1200
    }
  }
}
```

### Individual Evaluation

```json
{
  "question": "RNN là viết tắt của thuật ngữ gì trong học sâu?",
  "generated_answer": "RNN là viết tắt của Recurrent Neural Network[1]...",
  "ground_truth_answer": "RNN là tên viết tắt của mạng Recurrent Neural Network.",
  "metrics": {
    "answer_correctness": {
      "embedding_similarity": 0.9234,
      "llm_score": 0.9500,
      "combined_score": 0.9394,
      "explanation": "Câu trả lời chính xác và đầy đủ"
    },
    "citation_accuracy": {
      "has_citations": true,
      "citation_count": 3,
      "valid_citation_count": 3,
      "citation_coverage": 1.0,
      "accuracy_score": 1.0
    },
    "source_relevance": {
      "video_match_count": 1,
      "timestamp_overlap_count": 1,
      "precision": 0.8000,
      "recall": 1.0000,
      "f1_score": 0.8889
    },
    "hallucination_rate": {
      "hallucination_score": 0.0500,
      "has_hallucination": false,
      "hallucination_examples": []
    }
  }
}
```

---

## 🎯 Evaluation Guidelines

### What Makes a Good Q&A Response?

1. **Accurate**: Matches ground truth semantically
2. **Cited**: All claims have [N] citations
3. **Grounded**: Uses correct video sources and timestamps
4. **Faithful**: No hallucinated information

### Threshold Recommendations

- **Answer Correctness**: ≥ 0.7 (good), ≥ 0.8 (excellent)
- **Citation Accuracy**: ≥ 0.9 (all citations should be valid)
- **Source Relevance (F1)**: ≥ 0.6 (decent), ≥ 0.8 (excellent)
- **Hallucination Score**: ≤ 0.2 (acceptable), ≤ 0.1 (excellent)

---

## 🔧 Customization

### Add New Metrics

Edit `eval_service.py` and add methods:

```python
async def _calculate_new_metric(self, generated, ground_truth):
    # Your metric logic here
    return {
        "score": 0.0,
        "details": {}
    }
```

### Modify LLM Prompts

Update prompts in `eval_service.py`:
- `_calculate_answer_correctness()`: LLM evaluation prompt
- `_calculate_hallucination_rate()`: Hallucination detection prompt

---

## 📊 Integration with CI/CD

Run automated evaluation after model updates:

```bash
# In your CI/CD pipeline
python evaluation/qa/run_eval.py --limit 10
```

Set thresholds in deployment scripts:

```python
summary = json.load(open('results/latest/summary.json'))
if summary['average_metrics']['answer_correctness'] < 0.7:
    raise Exception("Q&A quality below threshold!")
```

---

## 🐛 Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'app'`
- **Solution**: Run from `evaluation/qa/` directory or set PYTHONPATH

**Issue**: OpenAI API rate limits
- **Solution**: Add delays or use `--limit` flag

**Issue**: Low source relevance scores
- **Solution**: Check if ground truth video URLs match Qdrant data

---

## 📚 References

- [DeepEval Framework](https://docs.confident-ai.com/)
- [RAGAs Metrics](https://docs.ragas.io/en/stable/concepts/metrics/)
- [Anthropic's Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)

---

**Estimated Time Per Question:** ~10-15 seconds (depends on LLM latency)

**Team Can Iterate Quickly** - Run eval after each prompt change! 🚀
