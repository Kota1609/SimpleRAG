"""Hybrid retrieval combining BM25 (sparse) and semantic (dense) search with query expansion."""

from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np
from app.models.schemas import Message
from app.core.logging import get_logger

logger = get_logger(__name__)

# Query expansion synonyms for common terms
QUERY_EXPANSIONS = {
    'trip': ['trip', 'travel', 'journey', 'visit', 'stay'],
    'planning': ['planning', 'scheduled', 'booking', 'arranging', 'organizing'],
    'when': ['when', 'date', 'time', 'schedule'],
    'favorite': ['favorite', 'preferred', 'love', 'like', 'enjoy'],
    'restaurant': ['restaurant', 'dining', 'eatery', 'cuisine'],
    'car': ['car', 'vehicle', 'automobile', 'transportation'],
    'have': ['have', 'own', 'possess'],
}


class HybridRetriever:
    """Combines BM25 keyword search with semantic vector search."""
    
    def __init__(self):
        self._bm25: BM25Okapi = None
        self._messages: List[Message] = None
        self._tokenized_corpus: List[List[str]] = None
    
    def index_messages(self, messages: List[Message]) -> None:
        """
        Index messages for BM25 search.
        Combines user name + message text for better keyword matching.
        
        Args:
            messages: List of Message objects to index
        """
        logger.info("indexing_bm25", count=len(messages))
        
        self._messages = messages
        
        # Tokenize corpus: INCLUDE USER NAME for better matching!
        # This way "Layla" in query will match messages from Layla
        self._tokenized_corpus = [
            self._tokenize(f"{msg.user_name} {msg.message}") for msg in messages
        ]
        
        # Create BM25 index
        self._bm25 = BM25Okapi(self._tokenized_corpus)
        
        logger.info("bm25_indexing_complete", count=len(messages))
    
    def search_bm25(self, query: str, top_k: int = 100, use_expansion: bool = True) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search with optional query expansion.
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_expansion: Whether to expand query with synonyms
            
        Returns:
            List of results with message data and BM25 scores
        """
        if self._bm25 is None:
            logger.error("bm25_not_initialized")
            return []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        # QUERY EXPANSION: Add synonyms for better matching
        if use_expansion:
            expanded_tokens = []
            for token in tokenized_query:
                expanded_tokens.append(token)
                if token in QUERY_EXPANSIONS:
                    # Add synonyms
                    expanded_tokens.extend(QUERY_EXPANSIONS[token])
            tokenized_query = list(set(expanded_tokens))  # Remove duplicates
            logger.info("query_expanded", original_tokens=len(tokenized_query), expanded_tokens=len(expanded_tokens))
        
        # Get BM25 scores for all documents
        scores = self._bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                msg = self._messages[idx]
                results.append({
                    'message': msg,
                    'bm25_score': float(scores[idx]),
                    'id': msg.id,
                    'user_name': msg.user_name,
                    'document': msg.message,
                    'timestamp': msg.timestamp.isoformat(),
                })
        
        logger.info("bm25_search_complete", results_count=len(results))
        return results
    
    def hybrid_search(
        self,
        query: str,
        semantic_results: List[Dict[str, Any]],
        bm25_weight: float = 0.5,
        top_k: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Combine BM25 and semantic search results with weighted fusion.
        
        Args:
            query: Search query
            semantic_results: Results from vector search (with distances)
            bm25_weight: Weight for BM25 scores (0-1, default 0.5)
            top_k: Number of final results to return
            
        Returns:
            Reranked and merged results
        """
        # Get BM25 results with QUERY EXPANSION
        bm25_results = self.search_bm25(query, top_k=100, use_expansion=True)
        
        # Create score dictionaries
        bm25_scores = {r['id']: r['bm25_score'] for r in bm25_results}
        
        # Normalize semantic scores (distances -> similarities)
        # Lower distance = higher similarity
        semantic_scores = {}
        for r in semantic_results:
            msg_id = r.get('id')
            distance = r.get('distance', 2.0)
            # Convert distance to similarity (inverse + normalize)
            similarity = 1.0 / (1.0 + distance)
            semantic_scores[msg_id] = similarity
        
        # Normalize BM25 scores
        if bm25_scores:
            max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
            bm25_scores = {k: v / max_bm25 for k, v in bm25_scores.items()}
        
        # Normalize semantic scores
        if semantic_scores:
            max_semantic = max(semantic_scores.values()) if semantic_scores else 1.0
            semantic_scores = {k: v / max_semantic for k, v in semantic_scores.items()}
        
        # Combine scores with weighted fusion
        all_ids = set(bm25_scores.keys()) | set(semantic_scores.keys())
        
        combined_scores = {}
        for msg_id in all_ids:
            bm25_score = bm25_scores.get(msg_id, 0.0)
            semantic_score = semantic_scores.get(msg_id, 0.0)
            
            # Weighted combination
            combined_score = (
                bm25_weight * bm25_score + 
                (1 - bm25_weight) * semantic_score
            )
            combined_scores[msg_id] = combined_score
        
        # Sort by combined score
        sorted_ids = sorted(
            combined_scores.keys(),
            key=lambda x: combined_scores[x],
            reverse=True
        )[:top_k]
        
        # Build final results
        results = []
        for msg_id in sorted_ids:
            # Get message from either source
            msg_data = None
            for r in semantic_results:
                if r.get('id') == msg_id:
                    msg_data = r
                    break
            
            if not msg_data:
                for r in bm25_results:
                    if r['id'] == msg_id:
                        msg_data = {
                            'document': r['document'],
                            'user_name': r['user_name'],
                            'timestamp': r['timestamp'],
                            'id': r['id'],
                            'distance': 0.5  # Placeholder
                        }
                        break
            
            if msg_data:
                msg_data['hybrid_score'] = combined_scores[msg_id]
                msg_data['bm25_score'] = bm25_scores.get(msg_id, 0.0)
                msg_data['semantic_score'] = semantic_scores.get(msg_id, 0.0)
                results.append(msg_data)
        
        logger.info(
            "hybrid_search_complete",
            total_results=len(results),
            bm25_only=len(bm25_scores),
            semantic_only=len(semantic_scores)
        )
        
        return results
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Tokenization: lowercase + remove punctuation + split.
        This ensures 'london?' matches 'london'
        """
        import re
        # Remove punctuation, lowercase, split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return text.split()
    
    @property
    def is_indexed(self) -> bool:
        """Check if BM25 index is ready."""
        return self._bm25 is not None


# Global singleton
_hybrid_retriever = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create the global HybridRetriever instance."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever

