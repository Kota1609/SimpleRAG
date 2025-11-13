"""Embedding service using Sentence-Transformers."""

from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self.settings = get_settings()
        self._model: Optional[SentenceTransformer] = None
    
    def load_model(self) -> None:
        """Load the embedding model into memory."""
        if self._model is not None:
            logger.info("embedding_model_already_loaded")
            return
        
        logger.info("loading_embedding_model", model=self.settings.embedding_model)
        
        try:
            self._model = SentenceTransformer(self.settings.embedding_model)
            logger.info("embedding_model_loaded_successfully")
        except Exception as e:
            logger.error("failed_to_load_embedding_model", error=str(e))
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if self._model is None:
            self.load_model()
        
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if self._model is None:
            self.load_model()
        
        logger.info("generating_embeddings_batch", count=len(texts))
        
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32
        )
        
        return embeddings.tolist()
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

