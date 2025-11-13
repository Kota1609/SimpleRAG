"""ChromaDB vector store for semantic search."""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from app.models.schemas import Message
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class VectorStore:
    """Manages the ChromaDB vector database for semantic search."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
    
    def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        if self._client is not None:
            logger.info("vector_store_already_initialized")
            return
        
        logger.info("initializing_chromadb", path=self.settings.chromadb_path)
        
        try:
            self._client = chromadb.PersistentClient(
                path=self.settings.chromadb_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.settings.collection_name,
                metadata={"description": "Member messages for Q&A"}
            )
            
            logger.info(
                "chromadb_initialized",
                collection=self.settings.collection_name,
                count=self._collection.count()
            )
            
        except Exception as e:
            logger.error("failed_to_initialize_chromadb", error=str(e))
            raise
    
    def index_messages(
        self,
        messages: List[Message],
        embeddings: List[List[float]]
    ) -> None:
        """
        Index messages with their embeddings in ChromaDB.
        
        Args:
            messages: List of Message objects
            embeddings: Corresponding embeddings
        """
        if self._collection is None:
            self.initialize()
        
        # Check if already indexed
        current_count = self._collection.count()
        if current_count >= len(messages):
            logger.info("messages_already_indexed", count=current_count)
            return
        
        logger.info("indexing_messages", count=len(messages))
        
        # Prepare data for ChromaDB
        ids = [msg.id for msg in messages]
        
        # ENRICHED DOCUMENTS: Include user name + date in the TEXT for better semantic matching!
        # This allows queries like "When is Layla planning..." to match "Layla Kawaguchi [Date]..."
        documents = [
            f"{msg.user_name} ({msg.timestamp.strftime('%B %d, %Y')}): {msg.message}"
            for msg in messages
        ]
        
        metadatas = [
            {
                "user_id": msg.user_id,
                "user_name": msg.user_name,
                "timestamp": msg.timestamp.isoformat(),
                "original_message": msg.message  # Keep original for display
            }
            for msg in messages
        ]
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(messages), batch_size):
            end_idx = min(i + batch_size, len(messages))
            
            self._collection.add(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
            
            logger.info("indexed_batch", start=i, end=end_idx)
        
        logger.info("indexing_complete", total=self._collection.count())
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Perform semantic search on the vector store.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            Dictionary with ids, documents, metadatas, and distances
        """
        if self._collection is None:
            self.initialize()
        
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        logger.info("search_completed", results_count=len(results['ids'][0]))
        
        return {
            'ids': results['ids'][0],
            'documents': results['documents'][0],
            'metadatas': results['metadatas'][0],
            'distances': results['distances'][0]
        }
    
    def get_count(self) -> int:
        """Get the number of indexed messages."""
        if self._collection is None:
            return 0
        return self._collection.count()
    
    @property
    def is_initialized(self) -> bool:
        """Check if vector store is initialized."""
        return self._collection is not None


# Global singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

