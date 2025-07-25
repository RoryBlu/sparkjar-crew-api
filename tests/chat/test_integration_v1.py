"""
Integration tests for Chat with Memory v1.

KISS: Test full system flow with mocked external services.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.chat.models import ChatRequestV1
from src.chat.processors.chat_processor_v1 import ChatProcessorV1
from src.chat.services.memory_search_v1 import HierarchicalMemorySearcher, MemorySearchResult
from src.chat.services.session_manager_v1 import RedisSessionManager
from src.chat.services.conversation_store_v1 import ConversationMemoryStore
from src.chat.clients.memory_service import MemoryServiceClient


class TestChatIntegration:
    """Test full chat system integration."""
    
    @pytest.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        with patch('src.chat.services.session_manager_v1.redis.from_url') as mock:
            redis_mock = AsyncMock()
            redis_mock.ping = AsyncMock(return_value=True)
            redis_mock.get = AsyncMock(return_value=None)
            redis_mock.setex = AsyncMock(return_value=True)
            redis_mock.delete = AsyncMock(return_value=1)
            mock.return_value = redis_mock
            yield redis_mock
            
    @pytest.fixture
    def mock_memory_client(self):
        """Create mock memory service client."""
        client = AsyncMock(spec=MemoryServiceClient)
        client.search_relevant_memories = AsyncMock(return_value=[])
        client._make_request = AsyncMock(return_value={"entity": {"id": "test-123"}})
        return client
        
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()
        
    @pytest.fixture
    async def chat_processor(self, mock_redis, mock_memory_client, mock_llm_client):
        """Create chat processor with all dependencies."""
        memory_searcher = HierarchicalMemorySearcher(mock_memory_client)
        session_manager = RedisSessionManager("redis://localhost:6379")
        await session_manager._get_redis()  # Force connection
        conversation_store = ConversationMemoryStore(mock_memory_client)
        
        processor = ChatProcessorV1(
            memory_searcher,
            session_manager,
            conversation_store,
            mock_llm_client
        )
        
        return processor
        
    async def test_tutor_mode_flow(self, chat_processor, mock_memory_client):
        """Test complete tutor mode interaction flow."""
        # Setup
        client_id = uuid4()
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="How do I optimize database queries?",
            mode="tutor",
            learning_preferences={"style": "practical"}
        )
        
        # Mock memory search results
        mock_memory_client.search_relevant_memories.return_value = [
            MagicMock(
                entity_name="query_optimization",
                metadata={"hierarchy_level": "synth_class"},
                dict=lambda: {
                    "entity_name": "query_optimization",
                    "metadata": {"hierarchy_level": "synth_class"},
                    "observations": [{"value": {"content": "Use indexes"}}]
                }
            )
        ]
        
        # Process request
        response = await chat_processor.process_chat_request(request, client_id)
        
        # Verify tutor mode processing
        assert response.mode_used == "tutor"
        assert response.learning_context is not None
        assert "understanding_level" in response.learning_context
        assert "follow_up_questions" in response.learning_context
        assert response.memory_context_used == ["query_optimization"]
        
        # Verify conversation was stored
        assert mock_memory_client._make_request.called
        
    async def test_agent_mode_flow(self, chat_processor, mock_memory_client):
        """Test complete agent mode interaction flow."""
        # Setup
        client_id = uuid4()
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Create a database backup",
            mode="agent"
        )
        
        # Mock procedure memory
        mock_memory_client.search_relevant_memories.return_value = [
            MagicMock(
                entity_name="backup_procedure",
                entity={"type": "procedure"},
                metadata={},
                observations=[
                    {"type": "step", "value": "1. Stop service"},
                    {"type": "step", "value": "2. Run backup command"}
                ],
                dict=lambda: {
                    "entity_name": "backup_procedure",
                    "entity": {"type": "procedure"},
                    "metadata": {},
                    "observations": [
                        {"type": "step", "value": "1. Stop service"},
                        {"type": "step", "value": "2. Run backup command"}
                    ]
                }
            )
        ]
        
        # Process request
        response = await chat_processor.process_chat_request(request, client_id)
        
        # Verify agent mode processing
        assert response.mode_used == "agent"
        assert response.task_context is not None
        assert "procedures_followed" in response.task_context
        assert response.memory_context_used == ["backup_procedure"]
        
    async def test_mode_switching(self, chat_processor, mock_redis):
        """Test switching between modes."""
        client_id = uuid4()
        
        # Create initial session in agent mode
        request = ChatRequestV1(
            client_user_id=client_id,
            actor_type="synth",
            actor_id=uuid4(),
            message="Hello",
            mode="agent"
        )
        
        response = await chat_processor.process_chat_request(request, client_id)
        session_id = response.session_id
        
        # Mock session retrieval
        session_data = {
            "session_id": str(session_id),
            "client_user_id": str(client_id),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "mode": "agent",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": datetime.utcnow().isoformat(),
            "message_count": 1
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        # Switch to tutor mode
        updated_session = await chat_processor.switch_mode(
            session_id,
            "tutor",
            client_id
        )
        
        assert updated_session.mode == "tutor"
        assert updated_session.understanding_level == 3  # Default level
        assert updated_session.learning_path == []
        
    async def test_learning_progress_tracking(self, chat_processor, mock_redis):
        """Test learning progress in tutor mode."""
        client_id = uuid4()
        session_id = uuid4()
        
        # Mock tutor session
        session_data = {
            "session_id": str(session_id),
            "client_user_id": str(client_id),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "mode": "tutor",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": datetime.utcnow().isoformat(),
            "message_count": 5,
            "learning_topic": "Database Optimization",
            "understanding_level": 4,
            "learning_path": ["SQL Basics", "Indexes", "Query Plans"]
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        # Get progress
        progress = await chat_processor.get_learning_progress(session_id, client_id)
        
        assert progress["learning_topic"] == "Database Optimization"
        assert progress["understanding_level"] == 4
        assert len(progress["learning_path"]) == 3
        assert progress["message_count"] == 5
        
    async def test_memory_hierarchy(self, chat_processor, mock_memory_client):
        """Test memory hierarchy precedence."""
        client_id = uuid4()
        
        # Mock memories from different realms
        mock_memory_client.search_relevant_memories.return_value = [
            MagicMock(
                entity_name="client_policy",
                metadata={"hierarchy_level": "client"},
                dict=lambda: {
                    "entity_name": "client_policy",
                    "metadata": {"hierarchy_level": "client"}
                }
            ),
            MagicMock(
                entity_name="synth_knowledge",
                metadata={},
                actor_type="synth",
                dict=lambda: {
                    "entity_name": "synth_knowledge",
                    "metadata": {},
                    "actor_type": "synth"
                }
            )
        ]
        
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Test query",
            mode="agent",
            include_realms={
                "include_own": True,
                "include_class": True,
                "include_skills": True,
                "include_client": True
            }
        )
        
        response = await chat_processor.process_chat_request(request, client_id)
        
        # Verify CLIENT memory comes first due to precedence
        assert response.memory_context_used[0] == "client_policy"
        
    async def test_error_recovery(self, chat_processor, mock_memory_client):
        """Test system handles errors gracefully."""
        client_id = uuid4()
        
        # Mock memory service error
        mock_memory_client.search_relevant_memories.side_effect = Exception("Service down")
        
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Test query",
            mode="agent"
        )
        
        # Should handle error gracefully
        response = await chat_processor.process_chat_request(request, client_id)
        
        # Should still return response even with memory service down
        assert response.memory_context_used == []
        assert response.memory_realms_accessed == {}


import json