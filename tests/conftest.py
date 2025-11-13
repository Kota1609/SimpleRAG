"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_questions():
    """Sample questions for testing."""
    return [
        "When is Layla planning her trip to London?",
        "How many cars does Vikram Desai have?",
        "What are Amina's favorite restaurants?",
        "What restaurants has Amina mentioned?",
        "Which member mentioned Paris?",
    ]

