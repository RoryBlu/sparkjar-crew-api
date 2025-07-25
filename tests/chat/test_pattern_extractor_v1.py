"""
Unit tests for Pattern Extraction.

KISS: Test pattern identification and metrics.
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.chat.learning.pattern_extractor_v1 import PatternExtractor
from src.chat.models import ChatResponseV1


class TestPatternExtractor:
    """Test pattern extraction functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create pattern extractor."""
        return PatternExtractor()
        
    @pytest.fixture
    def sample_conversation(self):
        """Create sample conversation history."""
        return [
            {
                "message": "How do I create a database index?",
                "response": {
                    "response": "To create an index, use CREATE INDEX. The task is completed.",
                    "mode_used": "agent",
                    "task_context": {
                        "procedures_followed": ["create_index_sop"]
                    }
                }
            },
            {
                "message": "Thanks, that worked perfectly!",
                "response": {
                    "response": "Glad I could help!",
                    "mode_used": "agent"
                }
            }
        ]
        
    def test_extract_patterns(self, extractor, sample_conversation):
        """Test pattern extraction from conversation."""
        patterns = extractor.extract_patterns(sample_conversation)
        
        assert len(patterns) > 0
        assert patterns[0]["type"] == "task_completion"
        assert patterns[0]["success_score"] > 0.8
        
    def test_calculate_success_metrics(self, extractor):
        """Test success metric calculation."""
        response = ChatResponseV1(
            session_id=uuid4(),
            message_id=uuid4(),
            message="Test",
            response="Here is a detailed response with structure.\n\nStep 1: Do this\nStep 2: Do that",
            mode_used="agent",
            memory_context_used=["memory1", "memory2", "memory3"],
            memory_realms_accessed={"synth": 2, "client": 1},
            task_context={
                "procedures_followed": ["procedure1"]
            },
            relationships_traversed=3,
            memory_query_time_ms=100
        )
        
        metrics = extractor.calculate_success_metrics(response)
        
        assert metrics["response_quality"] > 0.5
        assert metrics["memory_relevance"] > 0.5
        assert metrics["task_completion"] == 0.8
        
    def test_calculate_success_with_feedback(self, extractor):
        """Test success calculation with user feedback."""
        response = MagicMock()
        response.response = "Test response"
        response.mode_used = "tutor"
        response.memory_context_used = []
        
        # Positive feedback
        metrics = extractor.calculate_success_metrics(
            response,
            "Thank you, that was perfect!"
        )
        assert metrics["user_satisfaction"] > 0.7
        
        # Negative feedback
        metrics = extractor.calculate_success_metrics(
            response,
            "That doesn't work, still confused"
        )
        assert metrics["user_satisfaction"] < 0.5
        
    def test_identify_successful_patterns(self, extractor):
        """Test filtering patterns by success threshold."""
        patterns = [
            {"type": "pattern1", "success_score": 0.9},
            {"type": "pattern2", "success_score": 0.6},
            {"type": "pattern3", "success_score": 0.8}
        ]
        
        successful = extractor.identify_successful_patterns(patterns, threshold=0.7)
        
        assert len(successful) == 2
        assert successful[0]["success_score"] == 0.9
        assert successful[1]["success_score"] == 0.8
        
    def test_create_pattern_entity(self, extractor):
        """Test pattern entity creation."""
        pattern = {
            "type": "task_completion",
            "trigger": "how-to question",
            "approach": "procedure-following",
            "outcome": "successful",
            "success_score": 0.85,
            "description": "Successfully completed user task"
        }
        
        session_id = uuid4()
        entity = extractor.create_pattern_entity(pattern, session_id)
        
        assert entity["entity"]["type"] == "interaction_pattern"
        assert entity["entity"]["metadata"]["pattern_type"] == "task_completion"
        assert entity["entity"]["metadata"]["success_score"] == 0.85
        assert len(entity["observations"]) == 1
        assert entity["observations"][0]["type"] == "pattern_description"
        
    def test_extract_trigger(self, extractor):
        """Test trigger extraction from messages."""
        assert extractor._extract_trigger("How do I create a table?") == "how-to question"
        assert extractor._extract_trigger("What is an index?") == "definition question"
        assert extractor._extract_trigger("Fix connection error") == "troubleshooting request"
        assert extractor._extract_trigger("Create a new user") == "creation task"
        assert extractor._extract_trigger("Hello there") == "general query"
        
    def test_group_patterns(self, extractor):
        """Test pattern grouping."""
        patterns = [
            {"type": "task", "trigger": "how-to", "success_score": 0.8},
            {"type": "task", "trigger": "how-to", "success_score": 0.9},
            {"type": "learning", "trigger": "what-is", "success_score": 0.7}
        ]
        
        grouped = extractor._group_patterns(patterns)
        
        assert len(grouped) == 2
        # First group should have averaged score
        task_pattern = next(p for p in grouped if p["type"] == "task")
        assert task_pattern["occurrences"] == 2
        assert task_pattern["success_score"] == 0.85