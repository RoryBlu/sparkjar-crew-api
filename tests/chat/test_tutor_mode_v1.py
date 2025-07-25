"""
Unit tests for Tutor Mode Processor.

KISS: Test core tutor functionality with mocks.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.chat.models import ChatRequestV1, ChatSessionV1, MemorySearchResult
from src.chat.processors.tutor_mode_v1 import TutorModeProcessor


class TestTutorModeProcessor:
    """Test tutor mode processing."""
    
    @pytest.fixture
    def mock_memory_searcher(self):
        """Create mock memory searcher."""
        searcher = AsyncMock()
        searcher.search_with_precedence = AsyncMock()
        return searcher
        
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()
        
    @pytest.fixture
    def processor(self, mock_memory_searcher, mock_llm_client):
        """Create tutor processor."""
        return TutorModeProcessor(mock_memory_searcher, mock_llm_client)
        
    @pytest.fixture
    def sample_request(self):
        """Create sample request."""
        return ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="How do I create a database index?",
            mode="tutor"
        )
        
    @pytest.fixture
    def sample_session(self):
        """Create sample tutor session."""
        return ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="tutor",
            understanding_level=3,
            learning_topic="Database Optimization",
            learning_path=["SQL Basics"]
        )
        
    async def test_process_request_success(
        self,
        processor,
        sample_request,
        sample_session,
        mock_memory_searcher
    ):
        """Test successful request processing."""
        # Mock memory search
        mock_memory_searcher.search_with_precedence.return_value = MemorySearchResult(
            memories=[
                {
                    "entity_name": "database_indexes",
                    "observations": [{"value": {"content": "Index creation guide"}}]
                }
            ],
            realms_accessed={"synth_class": 1},
            relationships_traversed=2,
            query_time_ms=50
        )
        
        # Process request
        response = await processor.process_request(
            sample_request,
            sample_session,
            uuid4()
        )
        
        # Verify response
        assert response.mode_used == "tutor"
        assert response.memory_context_used == ["database_indexes"]
        assert response.learning_context is not None
        assert "follow_up_questions" in response.learning_context
        assert response.learning_path is not None
        
    def test_assess_understanding_confusion(self, processor):
        """Test understanding assessment detects confusion."""
        level = processor._assess_understanding(
            "I don't understand how indexes work",
            3
        )
        assert level == 2  # Should decrease
        
    def test_assess_understanding_progress(self, processor):
        """Test understanding assessment detects progress."""
        level = processor._assess_understanding(
            "I see, so indexes speed up queries. What about compound indexes?",
            3
        )
        assert level == 4  # Should increase
        
    def test_determine_learning_objective(self, processor):
        """Test learning objective extraction."""
        objective = processor._determine_learning_objective(
            "How do I optimize slow queries?",
            "Database Performance",
            []
        )
        assert "optimize slow queries" in objective
        
    def test_generate_follow_up_questions_beginner(self, processor):
        """Test follow-up questions for beginners."""
        questions = processor._generate_follow_up_questions(
            "Understanding indexes",
            2,  # Low understanding
            []
        )
        
        # Should get simple questions
        assert any("simpler" in q for q in questions)
        
    def test_generate_follow_up_questions_advanced(self, processor):
        """Test follow-up questions for advanced users."""
        questions = processor._generate_follow_up_questions(
            "Understanding indexes",
            4,  # High understanding
            []
        )
        
        # Should get advanced questions
        assert any("alternative" in q or "connect" in q for q in questions)
        
    def test_suggest_next_topics(self, processor):
        """Test topic suggestions."""
        memories = [
            {
                "entity_name": "query_optimization",
                "metadata": {"related_topics": ["indexes", "execution_plans"]}
            }
        ]
        
        suggestions = processor._suggest_next_topics(
            "Database Basics",
            memories,
            3
        )
        
        assert "indexes" in suggestions
        assert "Database Basics" not in suggestions  # No duplicates
        
    def test_build_learning_path(self, processor):
        """Test learning path building."""
        current_path = ["SQL Basics", "Queries"]
        new_path = processor._build_learning_path(
            current_path,
            "Understanding Indexes"
        )
        
        assert "Understanding Indexes" in new_path
        assert len(new_path) == 3
        
    def test_build_learning_path_limit(self, processor):
        """Test learning path stays under limit."""
        # Create path with 10 items
        current_path = [f"Topic {i}" for i in range(10)]
        new_path = processor._build_learning_path(
            current_path,
            "New Topic"
        )
        
        assert len(new_path) == 10  # Limited to 10
        assert "New Topic" in new_path
        assert "Topic 0" not in new_path  # Oldest removed
        
    def test_build_memory_context(self, processor):
        """Test memory context building."""
        memories = [
            {
                "entity_name": "indexes",
                "observations": [
                    {"value": {"content": "Indexes speed up queries"}}
                ]
            },
            {
                "entity_name": "query_plans",
                "observations": [
                    {"value": "Understanding execution plans"}
                ]
            }
        ]
        
        context = processor._build_memory_context(memories)
        
        assert "indexes" in context
        assert "speed up queries" in context
        assert "query_plans" in context