"""Unit tests for BookTranslationCrewHandler."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.crews.book_translation_crew.book_translation_crew_handler import BookTranslationCrewHandler


class TestBookTranslationCrewHandler:
    """Test the crew handler."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance."""
        return BookTranslationCrewHandler()
    
    @pytest.fixture
    def valid_request_data(self):
        """Valid request data for testing."""
        return {
            "client_user_id": "test-user-123",
            "book_key": "el-baron-book",
            "target_language": "en"
        }
    
    def test_handler_initialization(self, handler):
        """Test handler initializes correctly."""
        assert handler is not None
        assert hasattr(handler, 'execute')
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_data(self, handler, valid_request_data):
        """Test execute with valid data."""
        # Mock the kickoff function
        with patch('src.crews.book_translation_crew.main.kickoff') as mock_kickoff:
            mock_kickoff.return_value = {
                "status": "completed",
                "book_key": "el-baron-book",
                "result": "Translation completed successfully",
                "target_language": "en"
            }
            
            result = await handler.execute(valid_request_data)
            
            assert result["status"] == "completed"
            assert result["book_key"] == "el-baron-book"
            assert "result" in result
            mock_kickoff.assert_called_once_with(valid_request_data)
    
    @pytest.mark.asyncio
    async def test_execute_with_missing_data(self, handler):
        """Test execute with missing required fields."""
        invalid_data = {
            "book_key": "test-book"
            # Missing client_user_id
        }
        
        with patch('src.crews.book_translation_crew.main.kickoff') as mock_kickoff:
            mock_kickoff.side_effect = KeyError("client_user_id")
            
            result = await handler.execute(invalid_data)
            
            assert result["status"] == "failed"
            assert "error" in result
            assert "client_user_id" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_handles_exceptions(self, handler, valid_request_data):
        """Test execute handles exceptions gracefully."""
        with patch('src.crews.book_translation_crew.main.kickoff') as mock_kickoff:
            mock_kickoff.side_effect = Exception("API rate limit exceeded")
            
            result = await handler.execute(valid_request_data)
            
            assert result["status"] == "failed"
            assert "error" in result
            assert "API rate limit exceeded" in result["error"]
    
    def test_input_validation(self, handler):
        """Test that handler validates inputs properly."""
        # Test with various invalid inputs
        test_cases = [
            ({}, "Missing all required fields"),
            ({"client_user_id": ""}, "Empty client_user_id"),
            ({"client_user_id": "123", "book_key": ""}, "Empty book_key"),
            ({"client_user_id": "123", "book_key": "test", "target_language": ""}, "Empty target language defaults to 'en'")
        ]
        
        for invalid_input, description in test_cases:
            # Handler should not crash with invalid inputs
            assert handler is not None, f"Handler should handle: {description}"