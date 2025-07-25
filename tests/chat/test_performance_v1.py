"""
Basic Performance Tests for Chat with Memory v1.

KISS: Test with realistic loads, measure response times.
"""

import asyncio
import time
from datetime import datetime
from statistics import mean, median
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.chat.models import ChatRequestV1, MemorySearchResult
from src.chat.processors.chat_processor_v1 import ChatProcessorV1
from src.chat.services.memory_search_v1 import HierarchicalMemorySearcher
from src.chat.services.session_manager_v1 import RedisSessionManager
from src.chat.services.conversation_store_v1 import ConversationMemoryStore
from src.chat.middleware.rate_limiter_v1 import RateLimiter


class TestPerformance:
    """Basic performance tests for chat system."""
    
    @pytest.fixture
    async def mock_dependencies(self):
        """Setup mocked dependencies for performance testing."""
        with patch('src.chat.services.session_manager_v1.redis.from_url') as redis_mock:
            # Mock Redis
            redis_client = AsyncMock()
            redis_client.ping = AsyncMock(return_value=True)
            redis_client.get = AsyncMock(return_value=None)
            redis_client.setex = AsyncMock(return_value=True)
            redis_client.incr = AsyncMock(return_value=1)
            redis_client.expire = AsyncMock(return_value=True)
            redis_client.pipeline = MagicMock(return_value=redis_client)
            redis_client.execute = AsyncMock(return_value=[1, True, 1, True])
            redis_mock.return_value = redis_client
            
            # Mock Memory Client
            memory_client = AsyncMock()
            memory_client.search_relevant_memories = AsyncMock(return_value=[])
            memory_client._make_request = AsyncMock(return_value={"entity": {"id": "test"}})
            
            # Mock LLM Client
            llm_client = MagicMock()
            
            yield {
                "redis": redis_client,
                "memory": memory_client,
                "llm": llm_client
            }
            
    @pytest.fixture
    async def chat_processor(self, mock_dependencies):
        """Create chat processor for testing."""
        memory_searcher = HierarchicalMemorySearcher(mock_dependencies["memory"])
        session_manager = RedisSessionManager("redis://localhost:6379")
        await session_manager._get_redis()
        conversation_store = ConversationMemoryStore(mock_dependencies["memory"])
        
        return ChatProcessorV1(
            memory_searcher,
            session_manager,
            conversation_store,
            mock_dependencies["llm"]
        )
        
    async def test_response_time_single_request(self, chat_processor):
        """Test response time for single request."""
        client_id = uuid4()
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Test query",
            mode="agent"
        )
        
        start = time.time()
        response = await chat_processor.process_chat_request(request, client_id)
        end = time.time()
        
        response_time_ms = (end - start) * 1000
        
        # Should respond within 2 seconds
        assert response_time_ms < 2000
        print(f"Single request response time: {response_time_ms:.2f}ms")
        
    async def test_concurrent_requests(self, chat_processor):
        """Test handling concurrent requests."""
        client_id = uuid4()
        concurrent_users = 50
        
        async def make_request(user_num: int):
            request = ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message=f"Test query from user {user_num}",
                mode="agent" if user_num % 2 == 0 else "tutor"
            )
            
            start = time.time()
            response = await chat_processor.process_chat_request(request, client_id)
            end = time.time()
            
            return (end - start) * 1000
            
        # Run concurrent requests
        tasks = [make_request(i) for i in range(concurrent_users)]
        response_times = await asyncio.gather(*tasks)
        
        # Calculate statistics
        avg_time = mean(response_times)
        median_time = median(response_times)
        max_time = max(response_times)
        
        print(f"\nConcurrent Request Statistics ({concurrent_users} users):")
        print(f"Average response time: {avg_time:.2f}ms")
        print(f"Median response time: {median_time:.2f}ms")
        print(f"Max response time: {max_time:.2f}ms")
        
        # P95 should be under 2 seconds
        p95_index = int(len(response_times) * 0.95)
        p95_time = sorted(response_times)[p95_index]
        assert p95_time < 2000
        
    async def test_memory_search_performance(self, mock_dependencies):
        """Test memory search performance with varying result sizes."""
        memory_searcher = HierarchicalMemorySearcher(mock_dependencies["memory"])
        client_id = uuid4()
        
        # Test with different memory result sizes
        test_sizes = [10, 50, 100, 500]
        
        for size in test_sizes:
            # Mock memories
            memories = [
                MagicMock(
                    entity_name=f"memory_{i}",
                    metadata={},
                    dict=lambda i=i: {"entity_name": f"memory_{i}", "metadata": {}}
                )
                for i in range(size)
            ]
            mock_dependencies["memory"].search_relevant_memories.return_value = memories
            
            request = ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message="Test search query",
                mode="agent"
            )
            
            start = time.time()
            result = await memory_searcher.search_with_precedence(request, client_id)
            end = time.time()
            
            search_time_ms = (end - start) * 1000
            print(f"Memory search with {size} results: {search_time_ms:.2f}ms")
            
            # Should handle even large result sets efficiently
            assert search_time_ms < 1000
            
    async def test_rate_limiting_performance(self, mock_dependencies):
        """Test rate limiter performance under load."""
        rate_limiter = RateLimiter(
            "redis://localhost:6379",
            requests_per_minute=20,
            requests_per_hour=200
        )
        rate_limiter._redis = mock_dependencies["redis"]
        
        user_id = uuid4()
        check_times = []
        
        # Simulate rapid requests
        for i in range(30):
            start = time.time()
            allowed, headers = await rate_limiter.check_rate_limit(user_id)
            end = time.time()
            
            check_times.append((end - start) * 1000)
            
            # Should start rejecting after 20
            if i < 20:
                assert allowed
            else:
                assert not allowed
                
        avg_check_time = mean(check_times)
        print(f"\nRate limit check average time: {avg_check_time:.2f}ms")
        
        # Rate limit checks should be fast
        assert avg_check_time < 50
        
    async def test_session_management_performance(self, mock_dependencies):
        """Test session management performance."""
        session_manager = RedisSessionManager("redis://localhost:6379")
        session_manager._redis = mock_dependencies["redis"]
        
        # Create many sessions
        session_times = []
        sessions = []
        
        for i in range(100):
            request = ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message="Test",
                mode="agent"
            )
            
            start = time.time()
            session = await session_manager.create_or_get_session(request)
            end = time.time()
            
            session_times.append((end - start) * 1000)
            sessions.append(session)
            
        avg_create_time = mean(session_times)
        print(f"\nSession creation average time: {avg_create_time:.2f}ms")
        
        # Session operations should be fast
        assert avg_create_time < 100
        
        # Test retrieval performance
        retrieval_times = []
        for session in sessions[:20]:
            start = time.time()
            retrieved = await session_manager.get_session(session.session_id)
            end = time.time()
            
            retrieval_times.append((end - start) * 1000)
            
        avg_retrieval_time = mean(retrieval_times)
        print(f"Session retrieval average time: {avg_retrieval_time:.2f}ms")
        
        assert avg_retrieval_time < 50
        
    async def test_memory_usage_stability(self, chat_processor):
        """Test memory usage remains stable over many requests."""
        import gc
        import sys
        
        client_id = uuid4()
        
        # Get initial memory baseline
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Process many requests
        for i in range(100):
            request = ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message=f"Test query {i}",
                mode="agent" if i % 2 == 0 else "tutor"
            )
            
            response = await chat_processor.process_chat_request(request, client_id)
            
            # Periodically check memory
            if i % 20 == 0:
                gc.collect()
                current_objects = len(gc.get_objects())
                growth = current_objects - initial_objects
                print(f"After {i} requests, object growth: {growth}")
                
        # Final memory check
        gc.collect()
        final_objects = len(gc.get_objects())
        total_growth = final_objects - initial_objects
        
        print(f"\nTotal object growth after 100 requests: {total_growth}")
        
        # Should not have excessive memory growth
        # Allow some growth for caching
        assert total_growth < 10000  # Reasonable threshold