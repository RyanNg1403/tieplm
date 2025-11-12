"""Evaluation metrics."""


class Evaluator:
    """Base evaluator class."""
    
    def calculate_metrics(self, predictions, ground_truth):
        """Calculate evaluation metrics."""
        pass


class QAEvaluator(Evaluator):
    """Q&A specific metrics."""
    pass


class SummaryEvaluator(Evaluator):
    """Summarization specific metrics (ROUGE, etc.)."""
    pass

