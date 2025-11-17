# Evaluation Module

Evaluate performance of 4 AI tasks: Q&A, Text Summary, Video Summary, Quiz Generation.

## 📁 Structure

```
evaluation/
├── text_summary/
│   ├── eval_service.py        # Evaluation service
│   ├── run_eval.py            # Evaluation runner script
│   ├── test_questions.json    # Test dataset (50 questions)
│   └── results/               # Evaluation results (gitignored)
├── qa/
│   ├── eval_service.py        # TODO
│   ├── run_eval.py            # TODO
│   └── results/
├── video_summary/
│   ├── eval_service.py        # TODO
│   ├── run_eval.py            # TODO
│   └── results/
└── quiz/
    ├── eval_service.py        # TODO
    ├── run_eval.py            # TODO
    └── results/
```

**Task-Specific Structure:**
Each task folder contains:
- **Evaluation service**: Core evaluation logic
- **Runner script**: Script to execute evaluation
- **Test dataset**: Questions/test cases (JSON)
- **Results folder**: Evaluation results (stored locally, gitignored)

## ✅ Implemented

- ✅ Task-specific folder structure
- ✅ **Text Summary Evaluation**:
  - DeepEval with QAG (Question-Answer Generation) metrics
  - 50 test questions covering all 8 chapters
  - Evaluation service with comprehensiveness-focused prompts
  - Runner script with batch evaluation and statistics
- ✅ **Quiz QAG Evaluation**:
  - Random chunk sampling → quiz question generation via quiz service
  - QA service answers using provided context only (short-answer & MCQ modes)
  - Short-answer metric: embedding cosine similarity
  - MCQ metric: accuracy of selected option (A/B/C/D/IDK)
  - Results saved under `evaluation/quiz/results/`

## ❌ TODO

- ❌ Q&A evaluation
- ❌ Video summary evaluation

## 🚀 Usage

### Text Summarization Evaluation

```bash
# Activate virtual environment
source .venv/bin/activate

# Navigate to text_summary folder
cd evaluation/text_summary

# Run all 50 questions
python run_eval.py --all

# Run specific range
python run_eval.py --start 0 --end 10

# Run specific questions
python run_eval.py --question-id sum_001 sum_002

# Results saved to: evaluation/text_summary/results/
```

### Other Tasks (TODO)

Similar structure for qa/, video_summary/, quiz/ when implemented.

## 📊 Evaluation Metrics

- **Text Summary**: 
  - **QAG-based** (DeepEval SummarizationMetric)
  - Coverage Score: Detail inclusion from original text
  - Alignment Score: Factual accuracy
  - Overall Score: min(coverage, alignment)
  
- **Q&A**: TBD (accuracy, source relevance)
- **Video Summary**: TBD (coverage, coherence)
- **Quiz**: TBD (question quality, difficulty)

## 🔧 Configuration

Add to `.env`:
```bash
# Evaluation Configuration
EVAL_MODEL=gpt-5-mini                    # Model for evaluation
EVAL_SUMMARIZATION_THRESHOLD=0.5         # Pass/fail threshold
```
