"""
Unit tests for Chat V1 models.

KISS: Test the important stuff, not every getter/setter.
"""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.chat.models import (
    ChatRequestV1, 
    ChatResponseV1, 
    ChatSessionV1,
    ConversationEntity,
    create_conversation_entity
)


class TestChatRequestV1:
    """Test ChatRequestV1 model validation and defaults."""
    
    def test_minimal_valid_request(self):
        """Test creating request with only required fields."""
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Hello"
        )
        
        assert request.mode == "agent"  # Default
        assert request.include_realms["include_own"] is True
        assert request.context_depth == 2
        assert request.learning_preferences is None
        
    def test_tutor_mode_request(self):
        """Test tutor mode with learning preferences."""
        request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth", 
            actor_id=uuid4(),
            message="Teach me about databases",
            mode="tutor",
            learning_preferences={
                "pace": "slow",
                "depth": "beginner"
            }
        )
        
        assert request.mode == "tutor"
        assert request.learning_preferences["pace"] == "slow"
        
    def test_invalid_mode_rejected(self):
        """Test that invalid modes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message="Hello",
                mode="teacher"  # Invalid
            )
        assert "literal_error" in str(exc_info.value)
        
    def test_context_depth_limits(self):
        """Test context depth validation."""
        # Valid depths
        for depth in [1, 2, 3]:
            request = ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message="Hello",
                context_depth=depth
            )
            assert request.context_depth == depth
            
        # Invalid depths
        for bad_depth in [0, 4, 100]:
            with pytest.raises(ValidationError):
                ChatRequestV1(
                    client_user_id=uuid4(),
                    actor_type="synth",
                    actor_id=uuid4(),
                    message="Hello",
                    context_depth=bad_depth
                )
                
    def test_learning_preferences_size_limit(self):
        """Test that overly complex preferences are rejected."""
        huge_prefs = {f"pref_{i}": "x" * 100 for i in range(20)}
        
        with pytest.raises(ValidationError) as exc_info:
            ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message="Hello",
                learning_preferences=huge_prefs
            )
        assert "too complex" in str(exc_info.value)


class TestChatResponseV1:
    """Test ChatResponseV1 model."""
    
    def test_complete_response(self):
        """Test creating a complete response with all fields."""
        response = ChatResponseV1(
            session_id=uuid4(),
            message_id=uuid4(),
            message="How do I optimize queries?",
            response="Let me explain query optimization...",
            mode_used="tutor",
            memory_context_used=["db_optimization", "indexes"],
            memory_realms_accessed={
                "synth": 1,
                "synth_class": 3,
                "client": 0
            },
            learning_path=["SQL Basics", "Optimization"],
            next_suggested_topics=["Indexes", "Execution Plans"],
            relationships_traversed=5,
            memory_query_time_ms=120
        )
        
        assert response.mode_used == "tutor"
        assert response.memory_realms_accessed["synth_class"] == 3
        assert len(response.learning_path) == 2
        assert response.memory_query_time_ms == 120
        
    def test_minimal_agent_response(self):
        """Test minimal response for agent mode."""
        response = ChatResponseV1(
            session_id=uuid4(),
            message_id=uuid4(),
            message="What time is it?",
            response="I don't have access to current time.",
            mode_used="agent"
        )
        
        assert response.mode_used == "agent"
        assert response.learning_path is None
        assert response.memory_realms_accessed == {}
        assert response.relationships_traversed == 0


class TestChatSessionV1:
    """Test ChatSessionV1 model for Redis storage."""
    
    def test_session_creation(self):
        """Test creating a new session."""
        session = ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="agent",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        assert session.message_count == 0
        assert session.learning_topic is None
        assert len(session.learning_path) == 0
        
    def test_tutor_session_with_state(self):
        """Test tutor session with learning state."""
        session = ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="tutor",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            learning_topic="Database Optimization",
            learning_path=["SQL Basics", "Query Structure"],
            understanding_level=3,
            message_count=5
        )
        
        assert session.mode == "tutor"
        assert session.learning_topic == "Database Optimization"
        assert len(session.learning_path) == 2
        assert session.understanding_level == 3
        
    def test_learning_path_limit(self):
        """Test that learning path is limited to 10 items."""
        long_path = [f"Topic_{i}" for i in range(20)]
        
        session = ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="tutor",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            learning_path=long_path
        )
        
        assert len(session.learning_path) == 10
        assert session.learning_path[0] == "Topic_10"  # Kept last 10
        
    def test_redis_serialization(self):
        """Test session can be serialized for Redis."""
        session = ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="agent",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Serialize
        redis_value = session.to_redis_value()
        assert isinstance(redis_value, str)
        
        # Deserialize
        restored = ChatSessionV1.from_redis_value(redis_value)
        assert restored.session_id == session.session_id
        assert restored.mode == session.mode


class TestConversationEntity:
    """Test conversation storage models."""
    
    def test_create_conversation_entity_helper(self):
        """Test the helper function creates valid entities."""
        entity = create_conversation_entity(
            session_id=uuid4(),
            actor_id=str(uuid4()),
            mode="tutor",
            participant_id=uuid4(),
            message="How do I optimize queries?",
            response="Let's start with understanding indexes...",
            memories_used=["db_optimization", "index_guide", "query_patterns"],
            topic="database optimization"
        )
        
        assert entity.actor_type == "synth"
        assert entity.entity["type"] == "conversation"
        assert entity.entity["name"].startswith("conv_")
        assert len(entity.observations) == 1
        assert len(entity.relationships) == 3  # One per memory
        
    def test_conversation_name_validation(self):
        """Test conversation naming rules."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationEntity(
                actor_type="synth",
                actor_id=str(uuid4()),
                entity={
                    "name": "bad_name",  # Doesn't start with conv_
                    "type": "conversation"
                },
                observations=[]
            )
        assert "must start with 'conv_'" in str(exc_info.value)
        
    def test_observation_limit(self):
        """Test that too many observations are rejected."""
        observations = [
            ConversationObservation(
                value={
                    "user_message": f"Message {i}",
                    "synth_response": f"Response {i}",
                    "mode": "agent"
                }
            )
            for i in range(100)
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            ConversationEntity(
                actor_type="synth",
                actor_id=str(uuid4()),
                entity={
                    "name": "conv_test_12345",
                    "type": "conversation"
                },
                observations=observations
            )
        assert "Too many observations" in str(exc_info.value)
        
    def test_relationship_entity_name_limit(self):
        """Test entity name length validation in relationships."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationRelationship(
                type="discusses",
                to_entity="this_is_a_really_long_entity_name_that_exceeds_fifty_characters",
                to_realm={"actor_type": "synth_class", "actor_id": "24"}
            )
        assert "Entity name too long" in str(exc_info.value)