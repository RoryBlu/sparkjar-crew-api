"""
Unit tests for Memory Maker Crew Handler.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from src.crews.memory_maker_crew.memory_maker_crew_handler import MemoryMakerCrewHandler


class TestMemoryMakerCrewHandler:
    """Test cases for MemoryMakerCrewHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create a MemoryMakerCrewHandler instance."""
        return MemoryMakerCrewHandler()
        
    @pytest.fixture
    def valid_request_data(self):
        """Create valid request data for testing."""
        return {
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "text_content": """
                Project Alpha is our new AI initiative focusing on natural language processing.
                John Smith is the project lead, working with Sarah Johnson on the technical architecture.
                The project aims to deliver advanced NLP capabilities by Q2 2024.
                Key technologies include transformer models and vector databases.
                Budget has been approved for $2M with a team of 8 engineers.
            """,
            "metadata": {
                "source": "meeting_notes",
                "timestamp": datetime.utcnow().isoformat(),
                "author": "Team Lead",
                "tags": ["project_discussion", "team_info", "AI"]
            }
        }
        
    @pytest.mark.asyncio
    async def test_execute_with_valid_data(self, handler, valid_request_data):
        """Test successful execution with valid data."""
        # Mock the crew
        with patch('src.crews.memory_maker_crew.memory_maker_crew_handler.MemoryMakerCrew') as MockCrew:
            # Mock crew instance and its methods
            mock_crew_instance = MagicMock()
            mock_crew_result = MagicMock()
            mock_crew_result.output = "Extracted 2 entities and 4 observations"
            
            mock_crew_instance.crew.return_value.kickoff.return_value = mock_crew_result
            MockCrew.return_value = mock_crew_instance
            
            # Execute
            result = await handler.execute(valid_request_data)
            
            # Verify result structure
            assert result["status"] == "completed"
            assert "entities_created" in result
            assert "entities_updated" in result
            assert "observations_added" in result
            assert "relationships_created" in result
            assert "extraction_metadata" in result
            
            # Verify crew was called
            MockCrew.assert_called_once_with(
                client_user_id=valid_request_data["client_user_id"],
                actor_type=valid_request_data["actor_type"],
                actor_id=valid_request_data["actor_id"]
            )
            
    @pytest.mark.asyncio
    async def test_execute_missing_required_fields(self, handler):
        """Test execution with missing required fields."""
        # Missing text_content
        invalid_data = {
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4())
        }
        
        result = await handler.execute(invalid_data)
        
        assert result["status"] == "failed"
        assert "Missing required fields" in result["error"]
        assert "text_content" in result["error"]
        
    @pytest.mark.asyncio
    async def test_execute_empty_text_content(self, handler):
        """Test execution with empty text content."""
        request_data = {
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "text_content": ""  # Empty string
        }
        
        result = await handler.execute(request_data)
        
        assert result["status"] == "failed"
        assert "non-empty string" in result["error"]
        
    @pytest.mark.asyncio
    async def test_execute_invalid_text_format(self, handler):
        """Test execution with invalid text format."""
        request_data = {
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "text_content": 12345  # Should be a string
        }
        
        result = await handler.execute(request_data)
        
        assert result["status"] == "failed"
        assert "must be a non-empty string" in result["error"]
        
    @pytest.mark.asyncio
    async def test_execute_with_metadata(self, handler):
        """Test execution with metadata."""
        request_data = {
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "text_content": "This is a test document about Project Beta.",
            "metadata": {
                "source": "email",
                "author": "test@example.com",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Mock the crew
        with patch('src.crews.memory_maker_crew.memory_maker_crew_handler.MemoryMakerCrew') as MockCrew:
            mock_crew_instance = MagicMock()
            mock_crew_result = MagicMock()
            mock_crew_result.output = "Extracted entities from email"
            
            mock_crew_instance.crew.return_value.kickoff.return_value = mock_crew_result
            MockCrew.return_value = mock_crew_instance
            
            result = await handler.execute(request_data)
            
            assert result["status"] == "completed"
            assert "extraction_metadata" in result
        
    def test_parse_crew_results_with_output(self, handler):
        """Test parsing crew results with output attribute."""
        mock_result = MagicMock()
        mock_result.output = "Extracted entities and observations"
        
        parsed = handler._parse_crew_results(mock_result)
        
        assert "summary" in parsed
        assert "entities_created" in parsed
        assert isinstance(parsed["entities_created"], list)
        
    def test_parse_crew_results_without_output(self, handler):
        """Test parsing crew results without output attribute."""
        mock_result = "Simple string result"
        
        parsed = handler._parse_crew_results(mock_result)
        
        assert "summary" in parsed
        assert parsed["summary"] == "Processed text and extracted memories"
        
    @pytest.mark.asyncio
    async def test_execute_with_crew_exception(self, handler, valid_request_data):
        """Test handling of crew execution exception."""
        with patch('src.crews.memory_maker_crew.memory_maker_crew_handler.MemoryMakerCrew') as MockCrew:
            # Mock crew to raise exception
            MockCrew.side_effect = Exception("Crew initialization failed")
            
            result = await handler.execute(valid_request_data)
            
            assert result["status"] == "failed"
            assert "Crew initialization failed" in result["error"]
            assert result["entities_created"] == []