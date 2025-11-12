"""Generate embeddings for transcripts."""


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
    
    def chunk_transcript(self, transcript: dict, chunk_duration: int = 60) -> list[dict]:
        """Chunk transcript by time windows."""
        pass
    
    async def generate_embeddings(self, chunks: list[dict]) -> list[dict]:
        """Generate embeddings for transcript chunks."""
        pass

