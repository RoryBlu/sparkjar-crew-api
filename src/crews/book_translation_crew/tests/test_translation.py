"""
Test Book Translation Crew
Simple tests to validate the translation functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the handler and main function
from ..book_translation_crew_handler import BookTranslationCrewHandler
from ..main import translate_pages_batch, query_book_pages


class TestBookTranslationCrew:
    """Test cases for book translation crew."""
    
    def test_handler_initialization(self):
        """Test that handler initializes correctly."""
        handler = BookTranslationCrewHandler()
        assert handler is not None
        assert hasattr(handler, 'execute')
        assert hasattr(handler, 'validate_request')
    
    def test_validate_request_success(self):
        """Test request validation with valid data."""
        handler = BookTranslationCrewHandler()
        
        valid_request = {
            "client_user_id": "test-client-123",
            "book_key": "test/book/path",
            "target_language": "en"
        }
        
        assert handler.validate_request(valid_request) is True
    
    def test_validate_request_missing_fields(self):
        """Test request validation with missing required fields."""
        handler = BookTranslationCrewHandler()
        
        # Missing book_key
        invalid_request = {
            "client_user_id": "test-client-123"
        }
        
        assert handler.validate_request(invalid_request) is False
    
    def test_validate_request_invalid_language(self):
        """Test request validation with invalid language."""
        handler = BookTranslationCrewHandler()
        
        invalid_request = {
            "client_user_id": "test-client-123",
            "book_key": "test/book/path",
            "target_language": "xyz"  # Invalid language
        }
        
        assert handler.validate_request(invalid_request) is False
    
    def test_validate_request_invalid_batch_size(self):
        """Test request validation with invalid batch size."""
        handler = BookTranslationCrewHandler()
        
        # Batch size too large
        invalid_request = {
            "client_user_id": "test-client-123",
            "book_key": "test/book/path",
            "batch_size": 100  # Max is 50
        }
        
        assert handler.validate_request(invalid_request) is False
    
    @patch('src.crews.book_translation_crew.crew.build_translation_crew')
    def test_translate_pages_batch(self, mock_build_crew):
        """Test batch translation functionality."""
        # Mock the crew
        mock_crew = Mock()
        mock_crew.kickoff.return_value = """Page 1:
        This is the translated text for page 1.
        
        ---PAGE_BREAK---
        
        Page 2:
        This is the translated text for page 2."""
        
        mock_build_crew.return_value = mock_crew
        
        # Test pages
        pages = [
            {
                "page_number": 1,
                "page_text": "Este es el texto de la página 1."
            },
            {
                "page_number": 2,
                "page_text": "Este es el texto de la página 2."
            }
        ]
        
        # Call the function
        result = translate_pages_batch(pages, "en")
        
        # Verify
        assert "PAGE_BREAK" in result
        assert "Page 1:" in result
        assert "Page 2:" in result
        mock_crew.kickoff.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_book_pages(self):
        """Test querying book pages from database."""
        # Mock database session
        mock_page = Mock()
        mock_page.page_number = 1
        mock_page.page_text = "Test text"
        mock_page.file_name = "test.pdf"
        mock_page.language_code = "es"
        mock_page.book_title = "Test Book"
        mock_page.book_author = "Test Author"
        mock_page.ocr_metadata = {"test": "metadata"}
        
        with patch('src.crews.book_translation_crew.main.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_page]
            mock_session.execute.return_value = mock_result
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Call the function
            pages = await query_book_pages("test-client", "test-book")
            
            # Verify
            assert len(pages) == 1
            assert pages[0]["page_number"] == 1
            assert pages[0]["page_text"] == "Test text"
    
    def test_kickoff_no_pages_found(self):
        """Test kickoff when no pages are found."""
        with patch('src.crews.book_translation_crew.main.asyncio.run') as mock_run:
            mock_run.return_value = []  # No pages
            
            inputs = {
                "client_user_id": "test-client",
                "book_key": "test-book"
            }
            
            from ..main import kickoff
            result = kickoff(inputs)
            
            assert result["status"] == "failed"
            assert "No original pages found" in result["error"]
            assert result["pages_translated"] == 0


# Sample test data for integration testing
SAMPLE_PAGES = [
    {
        "page_number": 1,
        "page_text": "El barón vivía en un castillo grande.",
        "file_name": "page_001.pdf",
        "language_code": "es",
        "book_title": "El Barón",
        "book_author": "Unknown"
    },
    {
        "page_number": 2,
        "page_text": "Tenía muchos sirvientes y riquezas.",
        "file_name": "page_002.pdf",
        "language_code": "es",
        "book_title": "El Barón",
        "book_author": "Unknown"
    },
    {
        "page_number": 3,
        "page_text": "Un día, decidió emprender un viaje.",
        "file_name": "page_003.pdf",
        "language_code": "es",
        "book_title": "El Barón",
        "book_author": "Unknown"
    },
    {
        "page_number": 4,
        "page_text": "El viaje lo llevaría a tierras lejanas.",
        "file_name": "page_004.pdf",
        "language_code": "es",
        "book_title": "El Barón",
        "book_author": "Unknown"
    },
    {
        "page_number": 5,
        "page_text": "Preparó su equipaje con cuidado.",
        "file_name": "page_005.pdf",
        "language_code": "es",
        "book_title": "El Barón",
        "book_author": "Unknown"
    }
]

if __name__ == "__main__":
    # Run basic tests
    test = TestBookTranslationCrew()
    
    print("Testing handler initialization...")
    test.test_handler_initialization()
    print("✓ Handler initialization test passed")
    
    print("\nTesting request validation...")
    test.test_validate_request_success()
    print("✓ Valid request test passed")
    
    test.test_validate_request_missing_fields()
    print("✓ Missing fields test passed")
    
    test.test_validate_request_invalid_language()
    print("✓ Invalid language test passed")
    
    print("\nAll basic tests passed!")