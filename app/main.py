"""Main FastAPI application for Aurora Q&A System."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import router
from app.core import setup_logging, get_logger, get_settings
from app.services import (
    get_data_fetcher,
    get_embedding_service,
    get_vector_store,
    get_llm_service,
    get_hybrid_retriever,
)
from app import __version__

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize all services and load data
    logger.info("application_starting", version=__version__)
    
    try:
        # Get service instances
        data_fetcher = get_data_fetcher()
        embedder = get_embedding_service()
        vector_store = get_vector_store()
        llm_service = get_llm_service()
        hybrid_retriever = get_hybrid_retriever()
        
        # Initialize embedding model
        logger.info("loading_embedding_model")
        embedder.load_model()
        
        # Initialize vector store
        logger.info("initializing_vector_store")
        vector_store.initialize()
        
        # Initialize LLM service
        logger.info("initializing_llm_service")
        llm_service.initialize()
        
        # Check if ChromaDB already has data
        existing_count = vector_store.get_count()
        
        if existing_count > 0:
            logger.info("using_existing_chromadb_index", count=existing_count)
            # Skip API fetch if we already have data
            messages = None
            
            # For BM25, try to fetch but don't fail if API is down
            if not hybrid_retriever.is_indexed:
                try:
                    logger.info("attempting_api_fetch_for_bm25")
                    messages = await data_fetcher.fetch_all_messages()
                    hybrid_retriever.index_messages(messages)
                    logger.info("bm25_indexed_from_api")
                except Exception as e:
                    logger.warning("api_unavailable_loading_from_backup", error=str(e))
                    # Load from backup JSON
                    import json
                    from pathlib import Path
                    from app.models.schemas import Message
                    from datetime import datetime
                    
                    backup_path = Path("./data/messages_backup.json")
                    if backup_path.exists():
                        with open(backup_path, 'r') as f:
                            messages_data = json.load(f)
                        messages = [
                            Message(
                                id=m['id'],
                                user_id=m['user_id'],
                                user_name=m['user_name'],
                                timestamp=datetime.fromisoformat(m['timestamp']),
                                message=m['message']
                            )
                            for m in messages_data
                        ]
                        hybrid_retriever.index_messages(messages)
                        logger.info("bm25_indexed_from_backup", count=len(messages))
                    else:
                        logger.warning("no_backup_file_found_bm25_disabled")
        else:
            # No existing data, must fetch from API
            logger.info("fetching_initial_data")
            messages = await data_fetcher.fetch_all_messages()
            
            logger.info("indexing_messages", count=len(messages))
            
            # Generate embeddings
            texts = [msg.message for msg in messages]
            embeddings = embedder.generate_embeddings_batch(texts)
            
            # Index in vector store
            vector_store.index_messages(messages, embeddings)
            
            # Index BM25
            hybrid_retriever.index_messages(messages)
            
            # Save backup
            import json
            from pathlib import Path
            backup_data = [
                {
                    'id': msg.id,
                    'user_id': msg.user_id,
                    'user_name': msg.user_name,
                    'timestamp': msg.timestamp.isoformat(),
                    'message': msg.message
                }
                for msg in messages
            ]
            Path("./data").mkdir(exist_ok=True)
            with open("./data/messages_backup.json", 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info("indexing_complete_and_backup_saved")
        
        logger.info("application_ready")
        
        yield
        
        # Shutdown
        logger.info("application_shutting_down")
        
    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise


# Create FastAPI app
app = FastAPI(
    title="Aurora Q&A System",
    description="Natural language question answering for member data using RAG",
    version=__version__,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="", tags=["Q&A"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Aurora Q&A System",
        "version": __version__,
        "description": "RAG-based question answering for member data",
        "endpoints": {
            "ask": "POST /ask - Ask a natural language question",
            "health": "GET /health - Check service health",
            "refresh": "POST /refresh - Refresh data cache",
            "docs": "GET /docs - Interactive API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )

