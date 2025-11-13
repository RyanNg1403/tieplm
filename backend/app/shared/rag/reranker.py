"""Local reranking using cross-encoder models."""
import os
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder


class LocalReranker:
    """
    Reranker using local cross-encoder model.
    
    Cross-encoders jointly encode query and document, providing more accurate
    relevance scores than bi-encoders (embedding models).
    """
    
    def __init__(self, model_name: str = None, batch_size: int = None):
        """
        Initialize reranker with cross-encoder model.
        
        Args:
            model_name: HuggingFace model name (default from env)
            batch_size: Batch size for inference (default from env)
        """
        self.model_name = model_name or os.getenv(
            "RERANKER_MODEL", 
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self.batch_size = batch_size or int(os.getenv("RERANKER_BATCH_SIZE", "32"))
        self.top_k = int(os.getenv("RERANKER_TOP_K", "10"))
        
        print(f"Loading reranker model: {self.model_name}...")
        self.model = CrossEncoder(self.model_name)
        print(f"✅ Reranker loaded successfully")
    
    def rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder.
        
        Args:
            query: User query string
            results: List of retrieval results with 'metadata' containing 'text'
            top_k: Number of top results to return (default from env)
        
        Returns:
            Reranked results with 'rerank_score' added
        """
        if not results:
            return []
        
        top_k = top_k or self.top_k
        
        # Prepare query-document pairs for cross-encoder
        pairs = []
        for result in results:
            # Extract text from metadata
            text = result.get("metadata", {}).get("text", "")
            if text:
                pairs.append([query, text])
            else:
                # Fallback if text not in metadata
                pairs.append([query, ""])
        
        # Get cross-encoder scores (batch inference)
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False
        )
        
        # Add rerank scores to results
        for result, score in zip(results, scores):
            result["rerank_score"] = float(score)
        
        # Sort by rerank score (descending) and take top-K
        reranked = sorted(
            results, 
            key=lambda x: x.get("rerank_score", 0), 
            reverse=True
        )[:top_k]
        
        return reranked
    
    async def rerank_async(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Async wrapper for rerank (runs in sync since cross-encoder is CPU-bound).
        
        For production, consider running in a thread pool executor.
        """
        return self.rerank(query, results, top_k)


# Singleton instance
_local_reranker = None

def get_local_reranker() -> LocalReranker:
    """Get singleton local reranker instance."""
    global _local_reranker
    if _local_reranker is None:
        _local_reranker = LocalReranker()
    return _local_reranker
