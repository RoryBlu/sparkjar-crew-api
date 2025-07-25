"""
Unit tests for Enhanced Streaming Infrastructure.

KISS: Test streaming functionality with mocks.
"""

import asyncio
import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.chat.models import ChatResponseV1
from src.chat.streaming.stream_generator_v1 import StreamGeneratorV1, StreamBuffer


class TestStreamGeneratorV1:
    """Test stream generation functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create stream generator."""
        return StreamGeneratorV1(chunk_size=20, chunk_delay_ms=10)
        
    @pytest.fixture
    def sample_response(self):
        """Create sample chat response."""
        return ChatResponseV1(
            session_id=uuid4(),
            message_id=uuid4(),
            message="Test question",
            response="This is a test response that should be chunked properly.",
            mode_used="tutor",
            memory_context_used=["memory1", "memory2"],
            memory_realms_accessed={"synth": 1, "client": 1},
            learning_context={
                "understanding_level": 3,
                "learning_objective": "Test objective",
                "follow_up_questions": ["Question 1?", "Question 2?"],
                "suggested_topics": ["Topic A", "Topic B"]
            },
            relationships_traversed=2,
            memory_query_time_ms=50
        )
        
    async def test_generate_stream_with_metadata(self, generator, sample_response):
        """Test stream generation includes metadata."""
        events = []
        
        async for event in generator.generate_stream(sample_response):
            events.append(event)
            
        # Should have metadata event
        assert any("event: metadata" in e for e in events)
        
        # Should have typing events
        assert any("event: typing" in e and '"status": "started"' in e for e in events)
        assert any("event: typing" in e and '"status": "stopped"' in e for e in events)
        
        # Should have chunks
        chunk_events = [e for e in events if "event: chunk" in e]
        assert len(chunk_events) > 0
        
        # Should have completion
        assert any("event: complete" in e for e in events)
        
    async def test_chunk_text_properly(self, generator):
        """Test text is chunked correctly."""
        text = "This is a test. It should be chunked. Into multiple parts."
        chunks = generator._chunk_text(text)
        
        # Should split on sentences
        assert len(chunks) == 3
        assert chunks[0] == "This is a test."
        
        # Reconstruct should match original
        reconstructed = " ".join(chunks)
        assert reconstructed == text
        
    async def test_search_status_stream(self, generator):
        """Test search status streaming."""
        phases = [
            {"name": "Phase 1", "status": "started"},
            {"name": "Phase 2", "status": "completed"}
        ]
        
        events = []
        async for event in generator.generate_search_status_stream(phases):
            events.append(event)
            
        assert len(events) == 2
        assert all("event: search_status" in e for e in events)
        
    async def test_error_handling(self, generator, sample_response):
        """Test error event generation."""
        # Mock response to raise error
        sample_response.response = None  # Will cause error
        
        events = []
        async for event in generator.generate_stream(sample_response):
            events.append(event)
            
        # Should have error event
        assert any("event: error" in e for e in events)
        
    def test_metadata_event_creation(self, generator, sample_response):
        """Test metadata event has correct structure."""
        metadata = generator._create_metadata_event(sample_response)
        
        assert metadata["mode"] == "tutor"
        assert "learning_context" in metadata
        assert metadata["learning_context"]["understanding_level"] == 3
        assert metadata["memory_context"]["memories_used"] == 2
        
    def test_completion_event_creation(self, generator, sample_response):
        """Test completion event includes follow-ups."""
        completion = generator._create_completion_event(sample_response)
        
        assert "follow_up_questions" in completion
        assert len(completion["follow_up_questions"]) == 2
        assert "suggested_topics" in completion
        assert len(completion["suggested_topics"]) == 2


class TestStreamBuffer:
    """Test stream buffer functionality."""
    
    @pytest.fixture
    def buffer(self):
        """Create stream buffer."""
        return StreamBuffer(max_size=5)
        
    def test_add_chunk(self, buffer):
        """Test adding chunks to buffer."""
        buffer.add_chunk("chunk1")
        buffer.add_chunk("chunk2")
        
        assert len(buffer.buffer) == 2
        assert buffer.buffer == ["chunk1", "chunk2"]
        
    def test_buffer_limit(self, buffer):
        """Test buffer respects size limit."""
        for i in range(10):
            buffer.add_chunk(f"chunk{i}")
            
        assert len(buffer.buffer) == 5
        assert buffer.buffer[0] == "chunk5"  # Oldest removed
        
    def test_get_replay_chunks(self, buffer):
        """Test getting chunks for replay."""
        buffer.add_chunk("chunk1")
        buffer.add_chunk("chunk2")
        buffer.add_chunk("chunk3")
        
        replay = buffer.get_replay_chunks(from_index=1)
        assert replay == ["chunk2", "chunk3"]
        
    def test_error_tracking(self, buffer):
        """Test error tracking and retry logic."""
        assert buffer.should_retry()
        
        buffer.record_error()
        assert buffer.error_count == 1
        assert buffer.should_retry()
        
        # Max out errors
        buffer.record_error()
        buffer.record_error()
        assert buffer.error_count == 3
        assert not buffer.should_retry()
        
    def test_clear(self, buffer):
        """Test clearing buffer."""
        buffer.add_chunk("chunk1")
        buffer.record_error()
        
        buffer.clear()
        
        assert len(buffer.buffer) == 0
        assert buffer.error_count == 0