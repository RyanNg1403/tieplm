"""RAG retriever with hybrid search (Vector + BM25)."""
import os
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from ..embeddings.embedder import OpenAIEmbedder
from ..database.vector_db import VectorDBClient
from ..database.postgres import PostgresClient
from ..database.models import Chunk, Video


class RAGRetriever:
    """Hybrid retriever combining vector search and BM25."""
    
    def __init__(
        self,
        vector_db_client: VectorDBClient = None,
        postgres_client: PostgresClient = None,
        embedder: OpenAIEmbedder = None
    ):
        self.vector_db = vector_db_client or VectorDBClient()
        self.postgres = postgres_client or PostgresClient()
        self.embedder = embedder or OpenAIEmbedder()
        
        # Load RAG configuration from environment
        self.top_k_vector = int(os.getenv("RAG_TOP_K_VECTOR", "150"))
        self.top_k_bm25 = int(os.getenv("RAG_TOP_K_BM25", "150"))
        self.score_threshold = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.5"))
        
        # BM25 index (will be built on first retrieval)
        self.bm25_index = None
        self.bm25_corpus = []
        self.bm25_chunk_ids = []
    
    def build_bm25_index(self):
        """Build BM25 index from all chunks in PostgreSQL."""
        print("Building BM25 index from database...")
        
        with self.postgres.session_scope() as session:
            chunks = session.query(Chunk).all()
            
            # Tokenize corpus (simple whitespace tokenization)
            self.bm25_corpus = []
            self.bm25_chunk_ids = []
            
            for chunk in chunks:
                # Simple tokenization: lowercase + split
                tokenized = chunk.text.lower().split()
                self.bm25_corpus.append(tokenized)
                self.bm25_chunk_ids.append(chunk.qdrant_id)
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(self.bm25_corpus)
            print(f"✅ BM25 index built with {len(self.bm25_corpus)} chunks")
    
    def search_bm25(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Search using BM25 lexical matching."""
        if self.bm25_index is None:
            self.build_bm25_index()
        
        top_k = top_k or self.top_k_bm25
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Get top-K indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        # Return results with scores and qdrant_ids
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                results.append({
                    "qdrant_id": self.bm25_chunk_ids[idx],
                    "score": float(scores[idx]),
                    "method": "bm25"
                })
        
        return results
    
    def search_vector(
        self, 
        query: str, 
        top_k: int = None,
        chapter_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search using vector similarity."""
        top_k = top_k or self.top_k_vector
        
        # Embed query
        query_embedding = self.embedder.embed(query)
        
        # Build filters if chapter specified
        filters = None
        if chapter_filter:
            # Pass chapter filter to vector_db (handles list with MatchAny)
            filters = {"chapter": chapter_filter}
        
        # Search Qdrant
        results = self.vector_db.search(
            query_vector=query_embedding,
            top_k=top_k,
            filters=filters,
            score_threshold=self.score_threshold
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "qdrant_id": result["id"],
                "score": result["score"],
                "method": "vector",
                "payload": result["payload"]
            })
        
        return formatted_results
    
    def combine_results(
        self, 
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        final_top_k: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Combine vector and BM25 results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score(d) = sum(1 / (k + rank(d)))
        where k=60 is a constant, rank(d) is the rank of document d in each list.
        """
        K = 60  # RRF constant
        rrf_scores = {}
        result_data = {}
        
        # Add vector results
        for rank, result in enumerate(vector_results, start=1):
            qdrant_id = result["qdrant_id"]
            rrf_scores[qdrant_id] = rrf_scores.get(qdrant_id, 0) + (1 / (K + rank))
            if qdrant_id not in result_data:
                result_data[qdrant_id] = result
        
        # Add BM25 results
        for rank, result in enumerate(bm25_results, start=1):
            qdrant_id = result["qdrant_id"]
            rrf_scores[qdrant_id] = rrf_scores.get(qdrant_id, 0) + (1 / (K + rank))
            if qdrant_id not in result_data:
                result_data[qdrant_id] = result
        
        # Sort by RRF score and take top-K
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:final_top_k]
        
        # Build final results with RRF scores
        combined = []
        for qdrant_id in sorted_ids:
            result = result_data[qdrant_id].copy()
            result["rrf_score"] = rrf_scores[qdrant_id]
            combined.append(result)
        
        return combined
    
    def enrich_with_metadata(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich results with metadata from PostgreSQL."""
        if not results:
            return []
        
        # Get qdrant_ids from results
        qdrant_ids = [r["qdrant_id"] for r in results]
        
        # Fetch chunks and video metadata from PostgreSQL
        with self.postgres.session_scope() as session:
            chunks = session.query(Chunk, Video).join(
                Video, Chunk.video_id == Video.id
            ).filter(
                Chunk.qdrant_id.in_(qdrant_ids)
            ).all()
            
            # Create mapping of qdrant_id to metadata
            metadata_map = {}
            for chunk, video in chunks:
                metadata_map[chunk.qdrant_id] = {
                    "chunk_id": chunk.id,
                    "video_id": video.id,
                    "chapter": video.chapter,
                    "video_title": video.title,
                    "video_url": video.url,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "text": chunk.text
                }
        
        # Enrich results with metadata
        enriched = []
        for result in results:
            qdrant_id = result["qdrant_id"]
            if qdrant_id in metadata_map:
                result["metadata"] = metadata_map[qdrant_id]
                enriched.append(result)
        
        return enriched
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 150,
        chapter_filter: Optional[List[str]] = None,
        use_bm25: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using hybrid search.
        
        Args:
            query: User query string
            top_k: Number of results to return after combining
            chapter_filter: Optional list of chapters to filter (e.g., ["Chương 2", "Chương 3"])
            use_bm25: Whether to use BM25 in addition to vector search
        
        Returns:
            List of enriched results with metadata, sorted by relevance
        """
        # Step 1: Vector search
        vector_results = self.search_vector(
            query=query,
            top_k=self.top_k_vector,
            chapter_filter=chapter_filter
        )
        
        # Step 2: BM25 search (if enabled)
        if use_bm25:
            bm25_results = self.search_bm25(query, top_k=self.top_k_bm25)
            
            # Step 3: Combine using RRF
            combined_results = self.combine_results(
                vector_results=vector_results,
                bm25_results=bm25_results,
                final_top_k=top_k
            )
        else:
            # Use only vector results
            combined_results = vector_results[:top_k]
        
        # Step 4: Enrich with metadata from PostgreSQL
        enriched_results = self.enrich_with_metadata(combined_results)
        
        return enriched_results


# Singleton instance
_rag_retriever = None

def get_rag_retriever() -> RAGRetriever:
    """Get singleton RAG retriever instance."""
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever
