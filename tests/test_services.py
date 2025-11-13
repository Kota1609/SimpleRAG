"""Tests for service layer components."""

import pytest
from app.services import (
    get_data_fetcher,
    get_embedding_service,
    get_vector_store,
    get_llm_service,
)


@pytest.mark.asyncio
async def test_data_fetcher_fetch_messages():
    """Test fetching messages from the API."""
    fetcher = get_data_fetcher()
    
    messages = await fetcher.fetch_all_messages()
    
    assert len(messages) > 0
    assert messages[0].id is not None
    assert messages[0].user_name is not None
    assert messages[0].message is not None
    
    # Check that we got all messages
    assert len(messages) > 3000


@pytest.mark.asyncio
async def test_data_fetcher_caching():
    """Test that data fetcher uses caching."""
    fetcher = get_data_fetcher()
    
    # First fetch
    messages1 = await fetcher.fetch_all_messages()
    
    # Second fetch should use cache
    messages2 = await fetcher.fetch_all_messages()
    
    # Should return same data
    assert len(messages1) == len(messages2)
    assert messages1[0].id == messages2[0].id


def test_embedding_service_load_model():
    """Test loading the embedding model."""
    embedder = get_embedding_service()
    
    embedder.load_model()
    
    assert embedder.is_loaded


def test_embedding_service_generate_embedding():
    """Test generating a single embedding."""
    embedder = get_embedding_service()
    embedder.load_model()
    
    text = "This is a test message"
    embedding = embedder.generate_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # Dimension of all-MiniLM-L6-v2
    assert all(isinstance(x, float) for x in embedding)


def test_embedding_service_batch_generation():
    """Test generating embeddings in batch."""
    embedder = get_embedding_service()
    embedder.load_model()
    
    texts = [
        "First message",
        "Second message",
        "Third message"
    ]
    
    embeddings = embedder.generate_embeddings_batch(texts)
    
    assert len(embeddings) == 3
    assert all(len(emb) == 384 for emb in embeddings)


def test_vector_store_initialization():
    """Test vector store initialization."""
    vector_store = get_vector_store()
    
    vector_store.initialize()
    
    assert vector_store.is_initialized
    assert vector_store.get_count() >= 0


def test_vector_store_search():
    """Test vector store search functionality."""
    embedder = get_embedding_service()
    embedder.load_model()
    
    vector_store = get_vector_store()
    vector_store.initialize()
    
    # Generate query embedding
    query = "planning a trip to London"
    query_embedding = embedder.generate_embedding(query)
    
    # Search
    results = vector_store.search(query_embedding, top_k=5)
    
    assert 'documents' in results
    assert 'metadatas' in results
    assert 'distances' in results
    
    if len(results['documents']) > 0:
        # Check result structure
        assert len(results['documents']) <= 5
        assert all(isinstance(doc, str) for doc in results['documents'])


def test_llm_service_initialization():
    """Test LLM service initialization."""
    llm_service = get_llm_service()
    
    llm_service.initialize()
    
    assert llm_service.is_initialized


def test_llm_service_answer_generation():
    """Test LLM answer generation."""
    llm_service = get_llm_service()
    llm_service.initialize()
    
    question = "What is mentioned in these messages?"
    context_messages = [
        {
            'document': 'I need to book a flight to Paris',
            'user_name': 'Test User',
            'timestamp': '2024-01-01T00:00:00',
            'distance': 0.3
        },
        {
            'document': 'The hotel in Paris was excellent',
            'user_name': 'Test User',
            'timestamp': '2024-01-02T00:00:00',
            'distance': 0.4
        }
    ]
    
    result = llm_service.generate_answer(question, context_messages)
    
    assert 'answer' in result
    assert 'confidence' in result
    assert 'sources' in result
    
    assert len(result['answer']) > 0
    assert result['confidence'] in ['high', 'medium', 'low']
    assert len(result['sources']) > 0


@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    """Test the complete pipeline from fetching to answering."""
    # Fetch data
    fetcher = get_data_fetcher()
    messages = await fetcher.fetch_all_messages()
    assert len(messages) > 0
    
    # Load embedder
    embedder = get_embedding_service()
    embedder.load_model()
    assert embedder.is_loaded
    
    # Generate query embedding
    query = "trip to London"
    query_embedding = embedder.generate_embedding(query)
    assert len(query_embedding) == 384
    
    # Search vector store
    vector_store = get_vector_store()
    vector_store.initialize()
    results = vector_store.search(query_embedding, top_k=5)
    assert len(results['documents']) > 0
    
    # Generate answer
    llm_service = get_llm_service()
    llm_service.initialize()
    
    context_messages = [
        {
            'document': doc,
            'user_name': meta['user_name'],
            'timestamp': meta['timestamp'],
            'distance': dist
        }
        for doc, meta, dist in zip(
            results['documents'],
            results['metadatas'],
            results['distances']
        )
    ]
    
    result = llm_service.generate_answer(query, context_messages)
    assert 'answer' in result
    assert len(result['answer']) > 0

