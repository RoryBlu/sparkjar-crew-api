"""
Unit tests for Redis Session Manager.

KISS: Test core functionality with mocked Redis.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from src.chat.models import ChatRequestV1, ChatSessionV1
from src.chat.services.session_manager_v1 import RedisSessionManager, SessionError


class TestRedisSessionManager:
    """Test the Redis session manager."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        return redis_mock
        
    @pytest.fixture
    async def manager(self, mock_redis):
        """Create a session manager with mocked Redis."""
        with patch('src.chat.services.session_manager_v1.redis.from_url', return_value=mock_redis):
            manager = RedisSessionManager("redis://localhost:6379")
            # Force connection
            await manager._get_redis()
            return manager
            
    @pytest.fixture
    def sample_request(self):
        """Create a sample chat request."""
        return ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Hello",
            mode="agent"
        )
        
    async def test_create_new_session(self, manager, sample_request, mock_redis):
        """Test creating a new session."""
        # Mock Redis operations
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        
        # Create session
        session = await manager.create_or_get_session(sample_request)
        
        # Verify session created
        assert session.client_user_id == sample_request.client_user_id
        assert session.mode == "agent"
        assert session.message_count == 1
        
        # Verify Redis called
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        assert call_args[1]['name'].startswith("chat:session:")
        assert call_args[1]['time'] > 0  # TTL set
        
    async def test_get_existing_session(self, manager, sample_request, mock_redis):
        """Test retrieving an existing session."""
        session_id = uuid4()
        sample_request.session_id = session_id
        
        # Create mock session data
        existing_session = ChatSessionV1(
            session_id=session_id,
            client_user_id=sample_request.client_user_id,
            actor_type="synth",
            actor_id=str(sample_request.actor_id),
            mode="agent",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() + timedelta(hours=23),
            message_count=5
        )
        
        # Mock Redis get
        mock_redis.get = AsyncMock(return_value=existing_session.to_redis_value())
        mock_redis.setex = AsyncMock(return_value=True)
        
        # Get session
        session = await manager.create_or_get_session(sample_request)
        
        # Verify existing session returned with updates
        assert session.session_id == session_id
        assert session.message_count == 6  # Incremented
        assert session.last_activity > existing_session.last_activity
        
    async def test_session_expiration(self, manager, mock_redis):
        """Test that expired sessions are not returned."""
        session_id = uuid4()
        
        # Create expired session
        expired_session = ChatSessionV1(
            session_id=session_id,
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="agent",
            created_at=datetime.utcnow() - timedelta(days=2),
            last_activity=datetime.utcnow() - timedelta(days=2),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            message_count=1
        )
        
        # Mock Redis operations
        mock_redis.get = AsyncMock(return_value=expired_session.to_redis_value())
        mock_redis.delete = AsyncMock(return_value=1)
        
        # Get session should return None
        session = await manager.get_session(session_id)
        assert session is None
        
        # Verify expired session was deleted
        assert mock_redis.delete.called
        
    async def test_mode_switching(self, manager, sample_request, mock_redis):
        """Test switching modes updates session."""
        session_id = uuid4()
        sample_request.session_id = session_id
        sample_request.mode = "tutor"  # Different mode
        
        # Create existing session with different mode
        existing_session = ChatSessionV1(
            session_id=session_id,
            client_user_id=sample_request.client_user_id,
            actor_type="synth",
            actor_id=str(sample_request.actor_id),
            mode="agent",  # Original mode
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=23),
            message_count=1
        )
        
        mock_redis.get = AsyncMock(return_value=existing_session.to_redis_value())
        mock_redis.setex = AsyncMock(return_value=True)
        
        # Get session with mode switch
        session = await manager.create_or_get_session(sample_request)
        
        # Verify mode updated
        assert session.mode == "tutor"
        
    async def test_update_learning_state(self, manager, mock_redis):
        """Test updating tutor mode learning state."""
        session_id = uuid4()
        
        # Create tutor session
        tutor_session = ChatSessionV1(
            session_id=session_id,
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="tutor",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=23),
            learning_topic="Databases",
            learning_path=["SQL Basics"],
            understanding_level=2
        )
        
        mock_redis.get = AsyncMock(return_value=tutor_session.to_redis_value())
        mock_redis.setex = AsyncMock(return_value=True)
        
        # Update learning state
        updated = await manager.update_learning_state(
            session_id=session_id,
            topic="Advanced Databases",
            path_item="Indexes",
            understanding_level=3
        )
        
        assert updated.learning_topic == "Advanced Databases"
        assert "Indexes" in updated.learning_path
        assert updated.understanding_level == 3
        
    async def test_learning_path_limit(self, manager, mock_redis):
        """Test that learning path is limited to 10 items."""
        session_id = uuid4()
        
        # Create session with long path
        long_path = [f"Topic_{i}" for i in range(15)]
        tutor_session = ChatSessionV1(
            session_id=session_id,
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="tutor",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=23),
            learning_path=long_path
        )
        
        # Path should be truncated by validator
        assert len(tutor_session.learning_path) == 10
        
    async def test_delete_session(self, manager, mock_redis):
        """Test deleting a session."""
        session_id = uuid4()
        
        mock_redis.delete = AsyncMock(return_value=1)
        
        result = await manager.delete_session(session_id)
        
        assert result is True
        assert mock_redis.delete.called
        
    async def test_redis_error_handling(self, manager, sample_request, mock_redis):
        """Test handling of Redis errors."""
        # Mock Redis failure
        mock_redis.get = AsyncMock(side_effect=RedisError("Connection lost"))
        
        # Should raise SessionError
        with pytest.raises(SessionError):
            await manager.create_or_get_session(sample_request)
            
    async def test_corrupted_session_data(self, manager, mock_redis):
        """Test handling of corrupted session data."""
        session_id = uuid4()
        
        # Mock corrupted data
        mock_redis.get = AsyncMock(return_value="invalid json {")
        
        # Should return None, not crash
        session = await manager.get_session(session_id)
        assert session is None
        
    async def test_cleanup_expired_sessions(self, manager, mock_redis):
        """Test cleanup of expired sessions."""
        # Create mix of expired and valid sessions
        sessions = []
        for i in range(5):
            expired = i < 3  # First 3 are expired
            session = ChatSessionV1(
                session_id=uuid4(),
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=str(uuid4()),
                mode="agent",
                created_at=datetime.utcnow() - timedelta(days=2 if expired else 0),
                last_activity=datetime.utcnow() - timedelta(days=2 if expired else 0),
                expires_at=datetime.utcnow() - timedelta(hours=1 if expired else -23),
                message_count=1
            )
            sessions.append((f"chat:session:{session.session_id}", session))
            
        # Mock scan and get operations
        mock_redis.scan = AsyncMock(return_value=(0, [s[0] for s in sessions]))
        
        # Mock get to return session data
        async def mock_get(key):
            for k, session in sessions:
                if k == key:
                    return session.to_redis_value()
            return None
            
        mock_redis.get = mock_get
        mock_redis.delete = AsyncMock(return_value=1)
        
        # Run cleanup
        deleted = await manager.cleanup_expired_sessions()
        
        assert deleted == 3  # First 3 were expired
        assert mock_redis.delete.call_count == 3
        
    async def test_close_connection(self, manager, mock_redis):
        """Test closing Redis connection."""
        await manager.close()
        
        assert mock_redis.close.called
        assert manager._redis is None