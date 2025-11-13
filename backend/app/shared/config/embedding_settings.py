"""Embedding and chunking configuration settings."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class EmbeddingSettings(BaseSettings):
    """Settings for embedding configuration."""
    
    # Embedding Model
    embedding_provider: str = "openai"
    embedding_model_name: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_batch_size: int = 100
    
    # LLM for Contextual Chunking
    model_provider: str = "openai"
    model_name: str = "gpt-5-mini"
    llm_max_retries: int = 3
    llm_timeout: int = 60
    llm_temperature: float = 0.3
    
    # Chunking Configuration
    time_window: int = 60
    chunk_overlap: int = 10
    context_token_limit: int = 200
    enable_contextual_chunking: bool = True
    
    # Retrieval Configuration
    retrieval_top_k: int = 20
    retrieval_score_threshold: float = 0.7
    enable_reranking: bool = False
    reranker_model: Optional[str] = "cohere"
    reranker_top_k: int = 5
    
    # Pipeline Configuration
    log_level: str = "INFO"
    log_dir: str = "logs"
    max_workers: int = 4
    enable_progress_bar: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Optional[EmbeddingSettings] = None


def get_embedding_settings() -> EmbeddingSettings:
    """Get or create global embedding settings instance."""
    global _settings
    if _settings is None:
        _settings = EmbeddingSettings()
    return _settings

