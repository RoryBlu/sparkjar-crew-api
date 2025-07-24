"""
Test configuration validation for vanilla CrewAI setup
"""
import os
from unittest.mock import patch

import pytest
from services.crew_api.src.config import (DATABASE_URL_DIRECT, DATABASE_URL_POOLED,
                        OPENAI_API_KEY, OPTIONAL_CONFIG, validate_config)

class TestConfiguration:
    """Test configuration validation and loading."""

    def test_validate_config_with_required_vars(self):
        """Test configuration validation with all required variables set."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'DATABASE_URL_DIRECT': 'postgresql://test:test@localhost:5432/test',
            'DATABASE_URL_POOLED': 'postgresql://test:test@localhost:6543/test'
        }):
            # Import config again to reload with new env vars
            import importlib

            import src.config
            importlib.reload(src.config)
            
            # Should not raise an exception
            assert src.config.validate_config() is True

    def test_validate_config_missing_openai_key(self):
        """Test configuration validation fails when OpenAI key is missing."""
        # Mock the environment without OPENAI_API_KEY
        with patch.dict(os.environ, {
            'DATABASE_URL_DIRECT': 'postgresql://test:test@localhost:5432/test',
            'DATABASE_URL_POOLED': 'postgresql://test:test@localhost:6543/test'
        }, clear=True):
            # Import and reload to get fresh config
            import importlib

            import src.config
            importlib.reload(src.config)
            
            # Now validate_config should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                src.config.validate_config()
            
            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_validate_config_missing_database_url(self):
        """Test configuration validation fails when database URL is missing."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key'
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                # Import config again to reload with new env vars
                import importlib

                import src.config
                importlib.reload(src.config)
                src.config.validate_config()
            
            assert "DATABASE_URL_DIRECT" in str(exc_info.value) or "DATABASE_URL_POOLED" in str(exc_info.value)

    def test_optional_config_detection(self):
        """Test optional configuration detection."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'DATABASE_URL_DIRECT': 'postgresql://test:test@localhost:5432/test',
            'DATABASE_URL_POOLED': 'postgresql://test:test@localhost:6543/test',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SECRET_KEY': 'test-secret',
            'CHROMA_URL': 'https://test-chroma.railway.app'
        }):
            # Import config again to reload with new env vars
            import importlib

            import src.config
            importlib.reload(src.config)
            
            # Check optional configurations are detected
            assert src.config.OPTIONAL_CONFIG['supabase_enabled'] is True
            assert src.config.OPTIONAL_CONFIG['chroma_enabled'] is True

    def test_crewai_config_structure(self):
        """Test CrewAI configuration has expected structure."""
        from services.crew_api.src.config import CREWAI_CONFIG
        
        assert 'default_llm' in CREWAI_CONFIG
        assert 'max_concurrent_jobs' in CREWAI_CONFIG
        assert 'job_timeout' in CREWAI_CONFIG
        assert CREWAI_CONFIG['default_llm'] == 'gpt-4o'

if __name__ == "__main__":
    pytest.main([__file__])
