"""Service to fetch member messages from external API."""

import httpx
from typing import List, Optional
from datetime import datetime, timedelta
from app.models.schemas import Message, MessagesResponse
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class DataFetcher:
    """Fetches and caches member messages from the external API."""
    
    def __init__(self):
        self.settings = get_settings()
        self._cache: Optional[List[Message]] = None
        self._cache_time: Optional[datetime] = None
        
    async def fetch_all_messages(self, force_refresh: bool = False) -> List[Message]:
        """
        Fetch all messages from the API with caching.
        
        Args:
            force_refresh: Force refresh cache even if valid
            
        Returns:
            List of Message objects
        """
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            logger.info("returning_cached_messages", count=len(self._cache))
            return self._cache
        
        logger.info("fetching_messages_from_api", url=self.settings.messages_api_url)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch with high limit to get all messages
                response = await client.get(
                    self.settings.messages_api_url,
                    params={"limit": 10000}
                )
                response.raise_for_status()
                
                data = response.json()
                messages_response = MessagesResponse(**data)
                
                self._cache = messages_response.items
                self._cache_time = datetime.now()
                
                logger.info(
                    "messages_fetched_successfully",
                    total=messages_response.total,
                    fetched=len(messages_response.items)
                )
                
                return self._cache
                
        except httpx.HTTPError as e:
            logger.error("failed_to_fetch_messages", error=str(e))
            raise Exception(f"Failed to fetch messages: {str(e)}")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        
        cache_age = datetime.now() - self._cache_time
        max_age = timedelta(seconds=self.settings.cache_ttl_seconds)
        
        return cache_age < max_age
    
    def get_cached_messages(self) -> Optional[List[Message]]:
        """Get cached messages without fetching."""
        return self._cache


# Global singleton instance
_data_fetcher: Optional[DataFetcher] = None


def get_data_fetcher() -> DataFetcher:
    """Get or create the global DataFetcher instance."""
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher

