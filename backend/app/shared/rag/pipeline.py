"""RAG orchestration pipeline."""


class RAGPipeline:
    """End-to-end RAG pipeline."""
    
    def __init__(self, retriever, reranker=None):
        self.retriever = retriever
        self.reranker = reranker
    
    async def run(self, query: str, top_k: int = 5, filters: dict = None):
        """Run complete RAG pipeline."""
        pass

