"""Static configuration (Pydantic settings)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "tieplm"
    postgres_user: str = "user"
    postgres_password: str = "password"
    
    # Vector DB
    vector_db_type: str = "qdrant"
    vector_db_host: str = "localhost"
    vector_db_port: int = 6333
    
    # LLM APIs
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    
    # Transcription
    whisper_api_key: str = ""
    deepgram_api_key: str = ""
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

