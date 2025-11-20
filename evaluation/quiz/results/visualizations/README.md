# Quiz Evaluation Visualizations

Comprehensive visualizations of quiz evaluation results for MCQ and Open-Ended questions.

## Generated Files

### 1. `mcq_evaluation_results.png`
MCQ performance analysis with accuracy overview, score distribution, statistics, and cumulative accuracy trend.

**Results:** 50 questions, 100.0% accuracy

### 2. `open_ended_evaluation_results.png`
Open-ended question quality using embedding similarity: distribution, box plot, performance categories, and statistics.

**Results:** 50 questions, mean similarity 0.803 (80.3%)
- Excellent (≥0.85): 40%
- Good (0.70-0.85): 48%
- Fair (0.50-0.70): 12%

### 3. `comparison_results.png`
Side-by-side comparison of MCQ vs Open-Ended performance with distributions.

### 4. `detailed_analysis.png`
Question-by-question performance scatter plot and cumulative trend analysis.

## Usage

```bash
python evaluation/quiz/visualize_results.py
```

Requires: `matplotlib`, `seaborn`, `numpy`
