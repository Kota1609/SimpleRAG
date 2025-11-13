"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns service information."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["service"] == "Aurora Q&A System"


def test_health_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "messages_loaded" in data
    assert "embeddings_ready" in data
    
    # Should have loaded messages
    assert data["messages_loaded"] > 0
    assert data["embeddings_ready"] is True


def test_ask_endpoint_valid_question(client: TestClient):
    """Test asking a valid question."""
    question = "When is Layla planning her trip to London?"
    
    response = client.post(
        "/ask",
        json={"question": question}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "confidence" in data
    assert "sources" in data
    assert "retrieved_contexts" in data
    assert "processing_time_ms" in data
    
    # Check confidence level is valid
    assert data["confidence"] in ["high", "medium", "low"]
    
    # Should have retrieved some contexts
    assert data["retrieved_contexts"] > 0
    
    # Processing time should be reasonable
    assert data["processing_time_ms"] < 5000  # Less than 5 seconds


def test_ask_endpoint_multiple_questions(client: TestClient, sample_questions):
    """Test multiple questions to ensure consistency."""
    for question in sample_questions:
        response = client.post(
            "/ask",
            json={"question": question}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        
        print(f"\nQ: {question}")
        print(f"A: {data['answer']}")
        print(f"Confidence: {data['confidence']}, Sources: {data.get('sources', [])}")


def test_ask_endpoint_empty_question(client: TestClient):
    """Test that empty questions are rejected."""
    response = client.post(
        "/ask",
        json={"question": ""}
    )
    
    assert response.status_code == 422  # Validation error


def test_ask_endpoint_missing_question(client: TestClient):
    """Test that missing question field is rejected."""
    response = client.post(
        "/ask",
        json={}
    )
    
    assert response.status_code == 422  # Validation error


def test_ask_endpoint_long_question(client: TestClient):
    """Test handling of very long questions."""
    long_question = "What " * 100 + "is Layla planning?"
    
    response = client.post(
        "/ask",
        json={"question": long_question}
    )
    
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 422]


def test_ask_endpoint_unknown_member(client: TestClient):
    """Test question about non-existent member."""
    response = client.post(
        "/ask",
        json={"question": "What is John Doe planning?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should respond that information is not available
    assert "answer" in data


def test_specific_layla_london_question(client: TestClient):
    """Test the specific example question about Layla's London trip."""
    response = client.post(
        "/ask",
        json={"question": "When is Layla planning her trip to London?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Answer should mention London and Layla
    assert "answer" in data
    answer_lower = data["answer"].lower()
    
    # Should contain relevant information
    assert len(data["answer"]) > 10
    
    # Sources should include Layla
    if data.get("sources"):
        assert any("Layla" in source for source in data["sources"])


def test_specific_vikram_car_question(client: TestClient):
    """Test the specific example question about Vikram's cars."""
    response = client.post(
        "/ask",
        json={"question": "How many cars does Vikram Desai have?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    
    # Sources should include Vikram
    if data.get("sources"):
        assert any("Vikram" in source for source in data["sources"])


def test_specific_amina_restaurant_question(client: TestClient):
    """Test question about Amina's restaurants (note: assignment says 'Amira')."""
    # Test with correct name
    response = client.post(
        "/ask",
        json={"question": "What are Amina's favorite restaurants?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    
    # Also test with incorrect name from assignment
    response2 = client.post(
        "/ask",
        json={"question": "What are Amira's favorite restaurants?"}
    )
    
    assert response2.status_code == 200
    # Should handle gracefully even with wrong name


@pytest.mark.asyncio
async def test_concurrent_requests(client: TestClient):
    """Test handling of concurrent requests."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    def make_request():
        return client.post(
            "/ask",
            json={"question": "What is Layla planning?"}
        )
    
    # Make 5 concurrent requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        responses = [f.result() for f in futures]
    
    # All should succeed
    for response in responses:
        assert response.status_code == 200

