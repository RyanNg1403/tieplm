"""Embedding generation."""


class Embedder:
    """Generate embeddings for text."""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
    
    async def embed(self, text: str):
        """Generate embedding for a single text."""
        pass
    
    async def embed_batch(self, texts: list[str]):
        """Generate embeddings for multiple texts."""
        pass

