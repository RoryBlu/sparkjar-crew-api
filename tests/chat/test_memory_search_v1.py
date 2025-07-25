"""
Unit tests for Hierarchical Memory Searcher.

KISS: Test core functionality, mock external calls.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.chat.models import ChatRequestV1, MemoryEntity
from src.chat.services.memory_search_v1 import (
    HierarchicalMemorySearcher,
    MemorySearchResult,
    SimpleMemoryCache
)


class TestSimpleMemoryCache:
    """Test the simple in-memory cache."""
    
    def test_cache_stores_and_retrieves(self):
        """Test basic cache operations."""
        cache = SimpleMemoryCache(ttl_minutes=15)
        
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        
        assert result == {"data": "value1"}
        
    def test_cache_expiration(self):
        """Test that expired entries return None."""
        cache = SimpleMemoryCache(ttl_minutes=15)
        
        # Set with past timestamp
        past_time = datetime.utcnow() - timedelta(minutes=20)
        cache._cache["expired_key"] = ({"data": "old"}, past_time)
        
        result = cache.get("expired_key")
        assert result is None
        assert "expired_key" not in cache._cache
        
    def test_cache_size_limit(self):
        """Test cache doesn't grow unbounded."""
        cache = SimpleMemoryCache(ttl_minutes=15)
        
        # Add more than limit
        for i in range(1100):
            cache.set(f"key_{i}", f"value_{i}")
            
        assert len(cache._cache) <= 1000
        
    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = SimpleMemoryCache(ttl_minutes=15)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        assert len(cache._cache) == 0


class TestHierarchicalMemorySearcher:
    """Test the hierarchical memory searcher."""
    
    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client."""
        client = AsyncMock()
        return client
        
    @pytest.fixture
    def searcher(self, mock_memory_client):
        """Create a searcher with mocked client."""
        return HierarchicalMemorySearcher(mock_memory_client)
        
    @pytest.fixture
    def sample_request(self):
        """Create a sample chat request."""
        return ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="How do I optimize database queries?",
            mode="agent",
            include_realms={
                "include_own": True,
                "include_class": True,
                "include_skills": True,
                "include_client": True
            },
            context_depth=2
        )
        
    async def test_search_with_cache_hit(self, searcher, sample_request):
        """Test that cache hits avoid memory service calls."""
        client_id = uuid4()
        
        # Pre-populate cache
        cached_result = MemorySearchResult(
            memories=[{"entity_name": "cached_memory"}],
            realms_accessed={"synth": 1},
            relationships_traversed=2,
            query_time_ms=50
        )
        
        cache_key = searcher._generate_cache_key(
            query=sample_request.message,
            actor_id=str(sample_request.actor_id),
            client_id=str(client_id),
            realms=sample_request.include_realms
        )
        searcher.cache.set(cache_key, cached_result)
        
        # Search should return cached result
        result = await searcher.search_with_precedence(sample_request, client_id)
        
        assert result.memories == cached_result.memories
        assert searcher.memory_client.search_relevant_memories.called is False
        
    async def test_search_calls_memory_service(self, searcher, sample_request, mock_memory_client):
        """Test that search calls memory service on cache miss."""
        client_id = uuid4()
        
        # Mock memory service response
        mock_memories = [
            MagicMock(
                entity_name="db_optimization",
                metadata={"hierarchy_level": "synth_class"},
                dict=lambda: {
                    "entity_name": "db_optimization",
                    "metadata": {"hierarchy_level": "synth_class"}
                }
            ),
            MagicMock(
                entity_name="company_policy",
                metadata={"hierarchy_level": "client"},
                dict=lambda: {
                    "entity_name": "company_policy", 
                    "metadata": {"hierarchy_level": "client"}
                }
            )
        ]
        
        mock_memory_client.search_relevant_memories.return_value = mock_memories
        
        # Perform search
        result = await searcher.search_with_precedence(sample_request, client_id)
        
        # Verify memory service was called
        assert mock_memory_client.search_relevant_memories.called
        assert len(result.memories) == 2
        assert result.realms_accessed["synth_class"] == 1
        assert result.realms_accessed["client"] == 1
        
    async def test_precedence_ordering(self, searcher, sample_request, mock_memory_client):
        """Test that memories are ordered by precedence."""
        client_id = uuid4()
        
        # Mock memories from different realms
        mock_memories = [
            MagicMock(
                entity_name="synth_memory",
                metadata={},
                actor_type="synth",
                dict=lambda: {
                    "entity_name": "synth_memory",
                    "metadata": {},
                    "actor_type": "synth"
                }
            ),
            MagicMock(
                entity_name="class_memory",
                metadata={"hierarchy_level": "synth_class"},
                dict=lambda: {
                    "entity_name": "class_memory",
                    "metadata": {"hierarchy_level": "synth_class"}
                }
            ),
            MagicMock(
                entity_name="client_policy", 
                metadata={"hierarchy_level": "client"},
                dict=lambda: {
                    "entity_name": "client_policy",
                    "metadata": {"hierarchy_level": "client"}
                }
            )
        ]
        
        mock_memory_client.search_relevant_memories.return_value = mock_memories
        
        result = await searcher.search_with_precedence(sample_request, client_id)
        
        # Client memory should be first due to precedence
        assert result.memories[0]["entity_name"] == "client_policy"
        assert result.memories[1]["entity_name"] == "synth_memory"
        assert result.memories[2]["entity_name"] == "class_memory"
        
    async def test_deduplication(self, searcher, sample_request, mock_memory_client):
        """Test that duplicate memories are removed."""
        client_id = uuid4()
        
        # Mock duplicate memories from different realms
        mock_memories = [
            MagicMock(
                entity_name="same_memory",
                metadata={},
                actor_type="synth",
                dict=lambda: {
                    "entity_name": "same_memory",
                    "metadata": {},
                    "actor_type": "synth"
                }
            ),
            MagicMock(
                entity_name="same_memory",
                metadata={"hierarchy_level": "client"},
                dict=lambda: {
                    "entity_name": "same_memory",
                    "metadata": {"hierarchy_level": "client"}
                }
            )
        ]
        
        mock_memory_client.search_relevant_memories.return_value = mock_memories
        
        result = await searcher.search_with_precedence(sample_request, client_id)
        
        # Should only have one memory (client version due to precedence)
        assert len(result.memories) == 1
        assert result.memories[0]["metadata"]["hierarchy_level"] == "client"
        
    async def test_error_handling(self, searcher, sample_request, mock_memory_client):
        """Test graceful degradation on memory service error."""
        client_id = uuid4()
        
        # Mock memory service error
        mock_memory_client.search_relevant_memories.side_effect = Exception("Service down")
        
        # Should return empty result, not crash
        result = await searcher.search_with_precedence(sample_request, client_id)
        
        assert result.memories == []
        assert result.realms_accessed == {}
        assert result.query_time_ms > 0  # Should still track time
        
    def test_cache_key_generation(self, searcher):
        """Test cache key generation is deterministic."""
        query = "test query"
        actor_id = str(uuid4())
        client_id = str(uuid4())
        realms = {"include_own": True, "include_class": True}
        
        key1 = searcher._generate_cache_key(query, actor_id, client_id, realms)
        key2 = searcher._generate_cache_key(query, actor_id, client_id, realms)
        
        assert key1 == key2
        
        # Different query should produce different key
        key3 = searcher._generate_cache_key("different", actor_id, client_id, realms)
        assert key3 != key1
        
    def test_realm_determination(self, searcher):
        """Test realm determination from memory metadata."""
        # Client memory
        assert searcher._determine_realm({
            "metadata": {"hierarchy_level": "client"}
        }) == "client"
        
        # Synth class memory
        assert searcher._determine_realm({
            "metadata": {"hierarchy_level": "synth_class"}
        }) == "synth_class"
        
        # Fallback to actor_type
        assert searcher._determine_realm({
            "actor_type": "synth"
        }) == "synth"
        
        # Default
        assert searcher._determine_realm({}) == "synth"