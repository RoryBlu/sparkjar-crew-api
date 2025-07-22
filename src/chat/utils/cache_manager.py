"""
Performance optimization through caching.
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

import redis.asyncio as redis
from cachetools import TTLCache

from src.chatmodels.context_models import SynthContext
from src.chatmodels.memory_models import MemoryEntity
from src.chatconfig import get_settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for performance optimization."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Redis client for distributed cache
        """
        self.settings = get_settings()
        self.redis_client = redis_client
        
        # Local in-memory caches for ultra-fast access
        self.synth_context_cache = TTLCache(
            maxsize=1000,
            ttl=self.settings.synth_context_cache_ttl_minutes * 60
        )
        
        self.memory_search_cache = TTLCache(
            maxsize=500,
            ttl=self.settings.memory_cache_ttl_minutes * 60
        )
        
        # Cache key prefixes
        self.SYNTH_CONTEXT_PREFIX = "synth_context:"
        self.MEMORY_SEARCH_PREFIX = "memory_search:"
        
    async def get_synth_context(
        self,
        actor_id: UUID,
        client_id: UUID
    ) -> Optional[SynthContext]:
        """
        Get cached SYNTH context.
        
        Args:
            actor_id: SYNTH ID
            client_id: Client ID
            
        Returns:
            Cached context or None
        """
        cache_key = f"{actor_id}:{client_id}"
        
        # Check local cache first
        if cache_key in self.synth_context_cache:
            logger.debug(f"SYNTH context cache hit (local): {cache_key}")
            return self.synth_context_cache[cache_key]
            
        # Check Redis if available
        if self.redis_client:
            try:
                redis_key = f"{self.SYNTH_CONTEXT_PREFIX}{cache_key}"
                cached_data = await self.redis_client.get(redis_key)
                
                if cached_data:
                    logger.debug(f"SYNTH context cache hit (Redis): {cache_key}")
                    context = SynthContext.parse_raw(cached_data)
                    
                    # Store in local cache too
                    self.synth_context_cache[cache_key] = context
                    return context
                    
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
                
        return None
        
    async def set_synth_context(
        self,
        actor_id: UUID,
        client_id: UUID,
        context: SynthContext
    ) -> None:
        """
        Cache SYNTH context.
        
        Args:
            actor_id: SYNTH ID
            client_id: Client ID
            context: Context to cache
        """
        cache_key = f"{actor_id}:{client_id}"
        
        # Store in local cache
        self.synth_context_cache[cache_key] = context
        
        # Store in Redis if available
        if self.redis_client:
            try:
                redis_key = f"{self.SYNTH_CONTEXT_PREFIX}{cache_key}"
                ttl_seconds = self.settings.synth_context_cache_ttl_minutes * 60
                
                await self.redis_client.setex(
                    redis_key,
                    ttl_seconds,
                    context.json()
                )
                
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
                
    async def get_memory_search_results(
        self,
        query: str,
        synth_context: SynthContext,
        search_params: Dict[str, Any]
    ) -> Optional[List[MemoryEntity]]:
        """
        Get cached memory search results.
        
        Args:
            query: Search query
            synth_context: SYNTH context
            search_params: Search parameters
            
        Returns:
            Cached results or None
        """
        # Create cache key from query and context
        cache_key = self._create_memory_search_key(
            query, 
            synth_context.synth_id,
            search_params
        )
        
        # Check local cache
        if cache_key in self.memory_search_cache:
            logger.debug(f"Memory search cache hit: {cache_key[:20]}...")
            return self.memory_search_cache[cache_key]
            
        # Check Redis if available
        if self.redis_client:
            try:
                redis_key = f"{self.MEMORY_SEARCH_PREFIX}{cache_key}"
                cached_data = await self.redis_client.get(redis_key)
                
                if cached_data:
                    logger.debug(f"Memory search cache hit (Redis): {cache_key[:20]}...")
                    # Deserialize memory entities
                    entities_data = json.loads(cached_data)
                    entities = [MemoryEntity(**data) for data in entities_data]
                    
                    # Store in local cache
                    self.memory_search_cache[cache_key] = entities
                    return entities
                    
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
                
        return None
        
    async def set_memory_search_results(
        self,
        query: str,
        synth_context: SynthContext,
        search_params: Dict[str, Any],
        results: List[MemoryEntity]
    ) -> None:
        """
        Cache memory search results.
        
        Args:
            query: Search query
            synth_context: SYNTH context
            search_params: Search parameters
            results: Results to cache
        """
        cache_key = self._create_memory_search_key(
            query,
            synth_context.synth_id,
            search_params
        )
        
        # Store in local cache
        self.memory_search_cache[cache_key] = results
        
        # Store in Redis if available
        if self.redis_client:
            try:
                redis_key = f"{self.MEMORY_SEARCH_PREFIX}{cache_key}"
                ttl_seconds = self.settings.memory_cache_ttl_minutes * 60
                
                # Serialize memory entities
                entities_data = [entity.dict() for entity in results]
                
                await self.redis_client.setex(
                    redis_key,
                    ttl_seconds,
                    json.dumps(entities_data, default=str)
                )
                
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
                
    async def invalidate_synth_context(
        self,
        actor_id: UUID,
        client_id: UUID
    ) -> None:
        """
        Invalidate cached SYNTH context.
        
        Args:
            actor_id: SYNTH ID
            client_id: Client ID
        """
        cache_key = f"{actor_id}:{client_id}"
        
        # Remove from local cache
        self.synth_context_cache.pop(cache_key, None)
        
        # Remove from Redis
        if self.redis_client:
            try:
                redis_key = f"{self.SYNTH_CONTEXT_PREFIX}{cache_key}"
                await self.redis_client.delete(redis_key)
            except Exception as e:
                logger.warning(f"Redis cache delete error: {e}")
                
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        stats = {
            "synth_context_cache": {
                "size": len(self.synth_context_cache),
                "max_size": self.synth_context_cache.maxsize,
                "ttl_minutes": self.settings.synth_context_cache_ttl_minutes
            },
            "memory_search_cache": {
                "size": len(self.memory_search_cache),
                "max_size": self.memory_search_cache.maxsize,
                "ttl_minutes": self.settings.memory_cache_ttl_minutes
            }
        }
        
        # Add Redis stats if available
        if self.redis_client:
            try:
                info = await self.redis_client.info("memory")
                stats["redis"] = {
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected": True
                }
            except Exception:
                stats["redis"] = {"connected": False}
                
        return stats
        
    def _create_memory_search_key(
        self,
        query: str,
        synth_id: UUID,
        search_params: Dict[str, Any]
    ) -> str:
        """
        Create cache key for memory search.
        
        Args:
            query: Search query
            synth_id: SYNTH ID
            search_params: Search parameters
            
        Returns:
            Cache key
        """
        # Create deterministic key from search parameters
        key_data = {
            "query": query.lower().strip(),
            "synth_id": str(synth_id),
            "params": search_params
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()