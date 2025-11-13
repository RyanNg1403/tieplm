"""Vector database client for Qdrant."""
import os
from typing import List, Dict, Optional, Any
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)


class VectorDBClient:
    """Client for Qdrant vector database."""
    
    def __init__(self, host: str = None, port: int = None, collection_name: str = None):
        """Initialize Qdrant client.
        
        Args:
            host: Qdrant host. If None, will load from QDRANT_HOST env var.
            port: Qdrant port. If None, will load from QDRANT_PORT env var.
            collection_name: Collection name. If None, will load from QDRANT_COLLECTION_NAME env var.
        """
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION_NAME", "cs431_course_transcripts")
        
        self.client = QdrantClient(host=self.host, port=self.port)
        self.vector_size = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    def create_collection(self, recreate: bool = False):
        """Create collection if it doesn't exist.
        
        Args:
            recreate: If True, delete existing collection and create new one.
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name in collection_names:
            if recreate:
                self.client.delete_collection(self.collection_name)
            else:
                print(f"Collection '{self.collection_name}' already exists.")
                return
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            )
        )
        print(f"Created collection '{self.collection_name}' with dimension {self.vector_size}")
    
    def upsert_points(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Insert or update vectors with metadata.
        
        Args:
            vectors: List of embedding vectors.
            payloads: List of metadata dictionaries for each vector.
            ids: Optional list of point IDs. If None, will generate UUIDs.
        
        Returns:
            List of point IDs.
        """
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return ids
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector.
            top_k: Number of top results to return.
            filters: Optional filters (e.g., {"chapter": "Chương 4"}).
            score_threshold: Minimum similarity score threshold.
        
        Returns:
            List of search results with payload and score.
        """
        # Build filter if provided
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                # Handle list values (e.g., multiple chapters) with MatchAny
                if isinstance(value, list):
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchAny(any=value)
                        )
                    )
                else:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
            if conditions:
                query_filter = Filter(must=conditions)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold
        )
        
        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def delete_collection(self):
        """Delete the collection."""
        self.client.delete_collection(self.collection_name)
        print(f"Deleted collection '{self.collection_name}'")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        return self.client.get_collection(self.collection_name)


# Global instance for convenience
_vector_db_client = None


def get_vector_db_client() -> VectorDBClient:
    """Get or create global Qdrant client instance."""
    global _vector_db_client
    if _vector_db_client is None:
        _vector_db_client = VectorDBClient()
    return _vector_db_client

