"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Message(BaseModel):
    """Member message from the external API."""
    id: str
    user_id: str
    user_name: str
    timestamp: datetime
    message: str


class MessagesResponse(BaseModel):
    """Response from the messages API."""
    total: int
    items: List[Message]


class QuestionRequest(BaseModel):
    """Request model for the /ask endpoint."""
    question: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        description="Natural language question",
        json_schema_extra={"example": "What are Amira's favorite restaurants?"}
    )


class QuestionResponse(BaseModel):
    """Response model for the /ask endpoint."""
    answer: str = Field(..., description="Answer to the question")
    confidence: Optional[str] = Field(None, description="Confidence level: high, medium, low")
    sources: Optional[List[str]] = Field(None, description="Member names referenced")
    retrieved_contexts: Optional[int] = Field(None, description="Number of contexts retrieved")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    messages_loaded: int
    embeddings_ready: bool

