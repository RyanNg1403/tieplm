"""Store data in databases."""


class DataStorage:
    """Store processed data in Postgres and Vector DB."""
    
    def __init__(self, postgres_client, vector_db_client):
        self.postgres = postgres_client
        self.vector_db = vector_db_client
    
    async def store_video_metadata(self, video_data: dict):
        """Store video metadata in Postgres."""
        pass
    
    async def store_embeddings(self, embeddings: list[dict]):
        """Store embeddings in vector database."""
        pass

