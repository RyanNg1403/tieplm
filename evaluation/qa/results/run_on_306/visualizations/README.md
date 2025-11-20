# Q&A Evaluation Visualizations

Visualizations for 306 questions across chapters 2-9.

## Generated Files

### 1. `overall_metrics.png`
Overall performance: Exact Match (93.7%), Answer Correctness (72.6%), Citation Accuracy (95.1%), MRR (0.825)

### 2. `by_chapter_analysis.png`
Chapter-wise performance comparison across all metrics.

### 3. `metric_distributions.png`
Statistical distributions for Exact Match, Answer Correctness, Citation Accuracy, and MRR.

### 4. `retrieval_analysis.png`
Retrieval quality: rank distribution and cumulative Recall@K.

## Usage

```bash
# Default: run_on_306
python evaluation/qa/visualize_results.py

# Specify directory
python evaluation/qa/visualize_results.py results/run_on_100
```

Requires: `matplotlib`, `seaborn`, `numpy`
