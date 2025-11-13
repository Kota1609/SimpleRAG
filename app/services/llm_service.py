"""LLM service using Groq for answer generation."""

from groq import Groq
from typing import Dict, Any, Optional
import json
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class LLMService:
    """Service for generating answers using Groq LLM."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Groq] = None
    
    def initialize(self) -> None:
        """Initialize the Groq client."""
        if self._client is not None:
            logger.info("llm_client_already_initialized")
            return
        
        logger.info("initializing_groq_client")
        
        try:
            # Add timeout to prevent hanging connections
            self._client = Groq(
                api_key=self.settings.groq_api_key,
                timeout=30.0,  # 30 second timeout
                max_retries=2  # Retry on failure
            )
            logger.info("groq_client_initialized")
        except Exception as e:
            logger.error("failed_to_initialize_groq", error=str(e))
            raise
    
    def generate_answer(
        self,
        question: str,
        context_messages: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an answer to the question using retrieved context.
        
        Args:
            question: User's natural language question
            context_messages: List of relevant message contexts
            
        Returns:
            Dictionary with answer, confidence, and sources
        """
        if self._client is None:
            self.initialize()
        
        # Build context string
        context = self._build_context(context_messages)
        
        # Build prompt
        prompt = self._build_prompt(question, context)
        
        logger.info("generating_answer", question=question, context_count=len(context_messages))
        
        try:
            # Call Groq with explicit timeout
            response = self._client.chat.completions.create(
                model=self.settings.llm_model,
                timeout=25.0,  # Per-request timeout
                messages=[
        {
            "role": "system",
            "content": (
                "You are a concierge assistant analyzing member messages. "
                "Provide direct, specific answers without referencing message numbers. "
                
                "CRITICAL INSTRUCTIONS FOR DATES/TIMES:\n"
                "- Each message has a 'Date:' field showing when it was sent\n"
                "- When someone says 'next month', calculate: message date + 1 month\n"
                "- When someone says 'tomorrow', 'next week', 'starting Monday', calculate the actual date from the message timestamp\n"
                "- ALWAYS extract and state specific dates/times when available\n"
                "- Example: If message dated '2025-10-23' says 'next month', answer should say 'November 2025'\n"
                
                "OTHER INSTRUCTIONS:\n"
                "- For preferences: List specific items mentioned positively\n"
                "- For counting: Count carefully and state the number\n"
                "- Be confident and specific when the information is in the messages\n"
                "- Synthesize information naturally from multiple messages\n"
                "- Write in a natural, conversational tone\n"
                "- Never say 'not explicitly stated' if you can infer it from context + timestamps"
            )
        },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
            
            answer_text = response.choices[0].message.content.strip()
            
            # Extract sources (member names) from context
            sources = list(set(msg['user_name'] for msg in context_messages))
            
            # Determine confidence based on context relevance
            confidence = self._determine_confidence(context_messages)
            
            logger.info(
                "answer_generated",
                answer_length=len(answer_text),
                sources_count=len(sources),
                confidence=confidence
            )
            
            return {
                "answer": answer_text,
                "confidence": confidence,
                "sources": sources
            }
            
        except Exception as e:
            logger.error("failed_to_generate_answer", error=str(e))
            raise Exception(f"Failed to generate answer: {str(e)}")
    
    def _build_context(self, context_messages: list[Dict[str, Any]]) -> str:
        """Build context string from retrieved messages."""
        context_parts = []
        
        for i, msg in enumerate(context_messages, 1):
            # Use original_message if available (from metadata), otherwise use document
            original_msg = msg.get('original_message', msg.get('document', ''))
            
            context_parts.append(
                f"Message {i}:\n"
                f"From: {msg['user_name']}\n"
                f"Date: {msg['timestamp']}\n"
                f"Content: {original_msg}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build the full prompt for the LLM."""
        return f"""Answer this question based on the member messages below.

Question: {question}

Member Messages:
{context}

Provide a direct, natural answer. Don't reference message numbers. Synthesize the information naturally.

Answer:"""
    
    def _determine_confidence(self, context_messages: list[Dict[str, Any]]) -> str:
        """
        Determine confidence level based on context quality.
        
        High: Multiple relevant messages with low distances
        Medium: Some relevant messages
        Low: Few or distant matches
        """
        if not context_messages:
            return "low"
        
        # Check average distance (similarity score) - lower is better
        avg_distance = sum(msg.get('distance', 2.0) for msg in context_messages) / len(context_messages)
        
        # More lenient thresholds since we're retrieving top-30
        if avg_distance < 1.3 and len(context_messages) >= 5:
            return "high"
        elif avg_distance < 1.6 and len(context_messages) >= 3:
            return "medium"
        else:
            return "low"
    
    @property
    def is_initialized(self) -> bool:
        """Check if LLM client is initialized."""
        return self._client is not None


# Global singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLMService instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

