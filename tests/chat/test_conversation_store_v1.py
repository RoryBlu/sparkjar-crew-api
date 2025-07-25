"""
Unit tests for Conversation Memory Store.

KISS: Test core storage functionality with mocked memory service.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.chat.models import ChatResponseV1, ChatSessionV1
from src.chat.services.conversation_store_v1 import (
    ConversationMemoryStore,
    ConversationStoreError
)


class TestConversationMemoryStore:
    """Test conversation storage functionality."""
    
    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory service client."""
        client = AsyncMock()
        return client
        
    @pytest.fixture
    def store(self, mock_memory_client):
        """Create a conversation store with mocked client."""
        return ConversationMemoryStore(mock_memory_client)
        
    @pytest.fixture
    def sample_session(self):
        """Create a sample chat session."""
        return ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="tutor",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            learning_topic="Database Optimization",
            message_count=3
        )
        
    @pytest.fixture
    def sample_response(self):
        """Create a sample chat response."""
        return ChatResponseV1(
            session_id=uuid4(),
            message_id=uuid4(),
            message="How do I create indexes?",
            response="To create indexes in SQL, you use the CREATE INDEX statement...",
            mode_used="tutor",
            memory_context_used=["sql_indexes", "query_optimization"],
            memory_realms_accessed={"synth_class": 2},
            learning_path=["SQL Basics", "Indexes"],
            relationships_traversed=5,
            memory_query_time_ms=120
        )
        
    async def test_store_conversation_success(
        self,
        store,
        sample_session,
        sample_response,
        mock_memory_client
    ):
        """Test successful conversation storage."""
        # Mock memory service response
        mock_memory_client._make_request.return_value = {
            "entity": {
                "id": "entity-123",
                "name": f"conv_{sample_session.session_id.hex[:8]}_12345"
            },
            "observations_created": 1,
            "relationships_created": 2
        }
        
        # Store conversation
        entity_id = await store.store_conversation_exchange(
            session=sample_session,
            message="How do I create indexes?",
            response=sample_response,
            memories_used=["sql_indexes", "query_optimization"]
        )
        
        # Verify stored
        assert entity_id == "entity-123"
        
        # Verify memory service called
        assert mock_memory_client._make_request.called
        call_args = mock_memory_client._make_request.call_args
        assert call_args[1]["endpoint"] == "/memory/entities/complete"
        
        # Verify entity structure
        entity_data = call_args[1]["json_data"]
        assert entity_data["actor_type"] == "synth"
        assert entity_data["actor_id"] == sample_session.actor_id
        assert entity_data["entity"]["type"] == "conversation"
        assert entity_data["entity"]["name"].startswith("conv_")
        
        # Verify observations
        assert len(entity_data["observations"]) == 1
        obs = entity_data["observations"][0]
        assert obs["type"] == "message_exchange"
        assert "user_message" in obs["value"]
        assert "synth_response" in obs["value"]
        assert obs["value"]["mode"] == "tutor"
        
        # Verify relationships
        assert len(entity_data["relationships"]) == 2
        for rel in entity_data["relationships"]:
            assert rel["type"] == "references"
            assert rel["to_entity"] in ["sql_indexes", "query_optimization"]
            
    async def test_store_conversation_memory_error(
        self,
        store,
        sample_session,
        sample_response,
        mock_memory_client
    ):
        """Test handling of memory service errors."""
        # Mock memory service error
        mock_memory_client._make_request.side_effect = Exception("Service error")
        
        # Should return None, not crash
        entity_id = await store.store_conversation_exchange(
            session=sample_session,
            message="Test message",
            response=sample_response,
            memories_used=[]
        )
        
        assert entity_id is None
        
    async def test_memory_extraction_queued(
        self,
        store,
        sample_session,
        sample_response,
        mock_memory_client
    ):
        """Test that memory extraction is queued asynchronously."""
        # Mock successful storage
        mock_memory_client._make_request.return_value = {
            "entity": {"id": "entity-456"}
        }
        
        # Patch asyncio.create_task to verify it's called
        with patch('asyncio.create_task') as mock_create_task:
            entity_id = await store.store_conversation_exchange(
                session=sample_session,
                message="Test",
                response=sample_response,
                memories_used=[]
            )
            
            # Verify task created
            assert mock_create_task.called
            
    def test_extract_topic_from_memories(self, store):
        """Test topic extraction from memories."""
        memories = ["database_optimization", "query_performance", "indexes"]
        
        topic = store.extract_topic_from_message(
            message="Tell me about queries",
            memories_used=memories
        )
        
        assert topic == "Database Optimization"
        
    def test_extract_topic_from_message_keywords(self, store):
        """Test topic extraction from message keywords."""
        topic = store.extract_topic_from_message(
            message="How do I optimize database performance?",
            memories_used=[]
        )
        
        assert topic == "Database"
        
    def test_extract_topic_no_match(self, store):
        """Test topic extraction with no matches."""
        topic = store.extract_topic_from_message(
            message="Hello there",
            memories_used=[]
        )
        
        assert topic is None
        
    def test_extract_entities_from_response(self, store):
        """Test entity extraction from response."""
        response = '''
        To optimize queries, you should understand "query execution plans" 
        and how the QueryOptimizer works. The INDEX structures are crucial.
        '''
        
        entities = store.extract_entities_from_response(
            response=response,
            memories_used=["sql_basics"]
        )
        
        # Should include memories used
        assert "sql_basics" in entities
        
        # Should find quoted terms
        assert "query_execution_plans" in entities
        
        # Should limit results
        assert len(entities) <= 20
        
    async def test_message_truncation(
        self,
        store,
        sample_session,
        sample_response,
        mock_memory_client
    ):
        """Test that long messages are truncated."""
        # Mock successful storage
        mock_memory_client._make_request.return_value = {
            "entity": {"id": "entity-789"}
        }
        
        # Very long message
        long_message = "x" * 1000
        sample_response.response = "y" * 1000
        
        await store.store_conversation_exchange(
            session=sample_session,
            message=long_message,
            response=sample_response,
            memories_used=[]
        )
        
        # Check stored observation
        call_args = mock_memory_client._make_request.call_args
        obs_value = call_args[1]["json_data"]["observations"][0]["value"]
        
        # Should be truncated to 500 chars
        assert len(obs_value["user_message"]) == 500
        assert len(obs_value["synth_response"]) == 500
        
    async def test_relationship_limit(
        self,
        store,
        sample_session,
        sample_response,
        mock_memory_client
    ):
        """Test that relationships are limited."""
        # Mock successful storage
        mock_memory_client._make_request.return_value = {
            "entity": {"id": "entity-999"}
        }
        
        # Many memories used
        many_memories = [f"memory_{i}" for i in range(20)]
        
        await store.store_conversation_exchange(
            session=sample_session,
            message="Test",
            response=sample_response,
            memories_used=many_memories
        )
        
        # Check relationships
        call_args = mock_memory_client._make_request.call_args
        relationships = call_args[1]["json_data"]["relationships"]
        
        # Should be limited to 5
        assert len(relationships) == 5