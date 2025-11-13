"""Configuration management for Aurora Q&A System."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    groq_api_key: str = ""
    
    # External API
    messages_api_url: str = "https://november7-730026606190.europe-west1.run.app/messages/"
    
    # Model Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "llama-3.3-70b-versatile"  # Fast and accurate for RAG
    
    # ChromaDB
    chromadb_path: str = "./data/chromadb"
    collection_name: str = "member_messages"
    
    # Cache
    cache_ttl_seconds: int = 3600
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Retrieval
    top_k_results: int = 15
    
    # LLM
    llm_temperature: float = 0.3  # Slightly higher for more creative synthesis
    llm_max_tokens: int = 600
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

