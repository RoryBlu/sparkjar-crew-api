"""
Hierarchical Memory Search Service for Chat V1.

KISS principles:
- Use existing memory service endpoints
- Simple caching with TTL
- No complex state management
- Clear precedence rules
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from src.chat.clients.memory_service import MemoryServiceClient, MemoryServiceError
from src.chat.models import ChatRequestV1

logger = logging.getLogger(__name__)


class MemorySearchResult:
    """Container for memory search results with metadata."""
    
    def __init__(
        self,
        memories: List[Dict[str, Any]],
        realms_accessed: Dict[str, int],
        relationships_traversed: int,
        query_time_ms: int
    ):
        self.memories = memories
        self.realms_accessed = realms_accessed  # Count per realm
        self.relationships_traversed = relationships_traversed
        self.query_time_ms = query_time_ms
        
    def get_memory_names(self) -> List[str]:
        """Extract just the entity names for response."""
        return [m.get("entity_name", m.get("name", "unknown")) for m in self.memories]


class SimpleMemoryCache:
    """
    Simple in-memory cache with TTL.
    
    KISS: No Redis, just a dict with timestamp checking.
    Good enough for 100 concurrent users.
    """
    
    def __init__(self, ttl_minutes: int = 15):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        
    def get(self, key: str) -> Optional[Any]:
        """Get from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove it
                del self._cache[key]
        return None
        
    def set(self, key: str, value: Any):
        """Store in cache with current timestamp."""
        self._cache[key] = (value, datetime.utcnow())
        
        # Simple cleanup - if cache too big, remove oldest
        if len(self._cache) > 1000:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()


class HierarchicalMemorySearcher:
    """
    Searches across all 4 memory realms with proper precedence.
    
    Precedence: CLIENT > SYNTH > SYNTH_CLASS > SKILL_MODULE
    """
    
    def __init__(self, memory_client: MemoryServiceClient):
        self.memory_client = memory_client
        self.cache = SimpleMemoryCache(ttl_minutes=15)
        
    async def search_with_precedence(
        self,
        request: ChatRequestV1,
        client_id: UUID
    ) -> MemorySearchResult:
        """
        Search memories across configured realms with precedence.
        
        Args:
            request: Chat request with search query and realm config
            client_id: Client UUID for context
            
        Returns:
            MemorySearchResult with deduplicated, prioritized memories
        """
        start_time = datetime.utcnow()
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            query=request.message,
            actor_id=str(request.actor_id),
            client_id=str(client_id),
            realms=request.include_realms
        )
        
        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for query: {request.message[:50]}...")
            return cached
            
        try:
            # Perform the search
            result = await self._search_all_realms(
                query=request.message,
                actor_type=request.actor_type,
                actor_id=str(request.actor_id),
                client_id=str(client_id),
                include_realms=request.include_realms,
                context_depth=request.context_depth
            )
            
            # Cache the result
            self.cache.set(cache_key, result)
            
            # Log performance
            logger.info(
                f"Memory search completed in {result.query_time_ms}ms. "
                f"Found {len(result.memories)} memories from "
                f"{sum(result.realms_accessed.values())} total results"
            )
            
            return result
            
        except MemoryServiceError as e:
            logger.error(f"Memory service error: {e}")
            # Return empty result on error - graceful degradation
            return MemorySearchResult(
                memories=[],
                realms_accessed={},
                relationships_traversed=0,
                query_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            
    async def _search_all_realms(
        self,
        query: str,
        actor_type: str,
        actor_id: str,
        client_id: str,
        include_realms: Dict[str, bool],
        context_depth: int
    ) -> MemorySearchResult:
        """
        Internal method to search across all configured realms.
        
        Uses the existing memory service /memory/search endpoint
        with hierarchical parameters.
        """
        start_time = datetime.utcnow()
        
        # Build search parameters
        search_params = {
            "query": query,
            "limit": 50,  # Reasonable limit
            "min_confidence": 0.7
        }
        
        # The memory service should handle realm inclusion
        # based on actor context. For now, we'll make a single call.
        
        try:
            # Search with hierarchical context
            # The memory service client already handles this
            from src.chat.models import SynthContext
            
            # Create minimal synth context for search
            synth_context = SynthContext(
                synth_id=UUID(actor_id),
                synth_class_id=0,  # Will be resolved by memory service
                client_id=UUID(client_id),
                synth_class_config={},
                company_customizations={},
                client_policies={},
                memory_access_scope=[]
            )
            
            # Use existing search method
            raw_memories = await self.memory_client.search_relevant_memories(
                query=query,
                synth_context=synth_context,
                limit=50,
                include_synth_class=include_realms.get("include_class", True),
                include_client=include_realms.get("include_client", True)
            )
            
            # Convert to our format and apply precedence
            memories = []
            realms_accessed = {
                "synth": 0,
                "synth_class": 0,
                "skill_module": 0,
                "client": 0
            }
            
            # Process and categorize memories
            for memory in raw_memories:
                memory_dict = memory.dict() if hasattr(memory, 'dict') else memory
                
                # Determine realm from metadata or actor_type
                realm = self._determine_realm(memory_dict)
                realms_accessed[realm] += 1
                
                memories.append(memory_dict)
                
            # Apply precedence and deduplication
            prioritized = self._apply_precedence(memories)
            
            # Simple relationship count (could be enhanced)
            relationships = context_depth * len(prioritized)
            
            query_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return MemorySearchResult(
                memories=prioritized,
                realms_accessed=realms_accessed,
                relationships_traversed=relationships,
                query_time_ms=query_time
            )
            
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            raise MemoryServiceError(f"Search failed: {e}")
            
    def _determine_realm(self, memory: Dict[str, Any]) -> str:
        """Determine which realm a memory belongs to."""
        # Check metadata for hierarchy level
        metadata = memory.get("metadata", {})
        hierarchy_level = metadata.get("hierarchy_level")
        
        if hierarchy_level == "client":
            return "client"
        elif hierarchy_level == "synth_class":
            return "synth_class"
        elif hierarchy_level == "skill_module":
            return "skill_module"
        else:
            # Check actor_type
            actor_type = memory.get("actor_type", "synth")
            if actor_type == "client":
                return "client"
            elif actor_type == "synth_class":
                return "synth_class"
            else:
                return "synth"
                
    def _apply_precedence(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply precedence rules and remove duplicates.
        
        CLIENT > SYNTH > SYNTH_CLASS > SKILL_MODULE
        """
        # Group by realm
        by_realm = {
            "client": [],
            "synth": [],
            "synth_class": [],
            "skill_module": []
        }
        
        for memory in memories:
            realm = self._determine_realm(memory)
            by_realm[realm].append(memory)
            
        # Combine in precedence order
        prioritized = []
        seen_names: Set[str] = set()
        
        # Order matters!
        for realm in ["client", "synth", "synth_class", "skill_module"]:
            for memory in by_realm[realm]:
                name = memory.get("entity_name", memory.get("name"))
                if name and name not in seen_names:
                    seen_names.add(name)
                    prioritized.append(memory)
                    
        return prioritized
        
    def _generate_cache_key(
        self,
        query: str,
        actor_id: str,
        client_id: str,
        realms: Dict[str, bool]
    ) -> str:
        """Generate a cache key for the search parameters."""
        # Create a stable key from search params
        key_data = {
            "q": query.lower()[:100],  # Normalize and limit
            "a": actor_id,
            "c": client_id,
            "r": sorted(k for k, v in realms.items() if v)
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
        
    def clear_cache(self):
        """Clear the memory cache - useful for testing."""
        self.cache.clear()
        logger.info("Memory search cache cleared")