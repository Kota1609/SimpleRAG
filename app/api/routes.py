"""API routes for Aurora Q&A System."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import QuestionRequest, QuestionResponse, HealthResponse
from app.services import (
    get_data_fetcher,
    get_embedding_service,
    get_vector_store,
    get_llm_service,
    get_hybrid_retriever,
)
from app.core.logging import get_logger
from app.core.config import get_settings
from app import __version__
import time

logger = get_logger(__name__)
router = APIRouter()


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest) -> QuestionResponse:
    """
    Answer a natural language question about member data.
    
    Args:
        request: Question request with the user's question
        
    Returns:
        Answer with confidence, sources, and metadata
    """
    start_time = time.time()
    
    logger.info("question_received", question=request.question)
    
    try:
        # Get services
        embedder = get_embedding_service()
        vector_store = get_vector_store()
        llm_service = get_llm_service()
        hybrid_retriever = get_hybrid_retriever()
        settings = get_settings()
        
        # Ensure everything is initialized
        if not embedder.is_loaded:
            embedder.load_model()
        if not vector_store.is_initialized:
            vector_store.initialize()
        if not llm_service.is_initialized:
            llm_service.initialize()
        
        # Generate embedding for the question
        question_embedding = embedder.generate_embedding(request.question)
        
        # HYBRID SEARCH: Combine semantic (dense) + BM25 (sparse)
        # Step 1: Get semantic search results (top-50 for reranking)
        semantic_results = vector_store.search(
            query_embedding=question_embedding,
            top_k=50  # Get more candidates for reranking
        )
        
        # Convert to format needed for hybrid search
        semantic_results_list = [
            {
                'id': semantic_results['ids'][i],
                'document': semantic_results['documents'][i],
                'user_name': semantic_results['metadatas'][i]['user_name'],
                'timestamp': semantic_results['metadatas'][i]['timestamp'],
                'distance': semantic_results['distances'][i]
            }
            for i in range(len(semantic_results['ids']))
        ]
        
        # Step 2: Combine with BM25 (top 100) and rerank to top 25
        search_results_hybrid = hybrid_retriever.hybrid_search(
            query=request.question,
            semantic_results=semantic_results_list,
            bm25_weight=0.6,  # Favor BM25 slightly for keyword matching
            top_k=25  # Final number of contexts for LLM
        )
        
        # Build context messages for LLM from hybrid results
        context_messages = []
        for result in search_results_hybrid:
            # Try to get metadata from semantic results
            metadata = None
            for sem_res in semantic_results_list:
                if sem_res.get('id') == result.get('id'):
                    # Get metadata from vector store results
                    idx = semantic_results['ids'].index(sem_res['id'])
                    metadata = semantic_results['metadatas'][idx]
                    break
            
            context_messages.append({
                'document': result['document'],
                'user_name': result['user_name'],
                'timestamp': result['timestamp'],
                'original_message': metadata.get('original_message', result['document']) if metadata else result['document'],
                'distance': result.get('distance', 0.5),
                'hybrid_score': result.get('hybrid_score', 0.0)
            })

        
        # Generate answer using LLM
        result = llm_service.generate_answer(
            question=request.question,
            context_messages=context_messages
        )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        logger.info(
            "question_answered",
            question=request.question,
            answer_length=len(result['answer']),
            processing_time_ms=processing_time
        )
        
        return QuestionResponse(
            answer=result['answer'],
            confidence=result['confidence'],
            sources=result['sources'],
            retrieved_contexts=len(context_messages),
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error("error_answering_question", error=str(e), question=request.question)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify service status.
    
    Returns:
        Service health status
    """
    try:
        vector_store = get_vector_store()
        embedder = get_embedding_service()
        
        messages_count = vector_store.get_count()
        embeddings_ready = embedder.is_loaded
        
        return HealthResponse(
            status="healthy",
            version=__version__,
            messages_loaded=messages_count,
            embeddings_ready=embeddings_ready
        )
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


@router.post("/refresh")
async def refresh_data():
    """
    Manually refresh the data cache and reindex.
    
    Returns:
        Success message with count
    """
    try:
        logger.info("manual_refresh_triggered")
        
        # Fetch fresh data
        data_fetcher = get_data_fetcher()
        messages = await data_fetcher.fetch_all_messages(force_refresh=True)
        
        # Generate embeddings
        embedder = get_embedding_service()
        if not embedder.is_loaded:
            embedder.load_model()
        
        texts = [msg.message for msg in messages]
        embeddings = embedder.generate_embeddings_batch(texts)
        
        # Reindex in vector store
        vector_store = get_vector_store()
        if not vector_store.is_initialized:
            vector_store.initialize()
        
        vector_store.index_messages(messages, embeddings)
        
        logger.info("refresh_completed", count=len(messages))
        
        return {
            "status": "success",
            "messages_refreshed": len(messages),
            "message": "Data refreshed and reindexed successfully"
        }
        
    except Exception as e:
        logger.error("refresh_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh data: {str(e)}"
        )

