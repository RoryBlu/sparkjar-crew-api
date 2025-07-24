"""
Test configuration and fixtures for Crew API tests.

This file provides common test fixtures and configuration for the crew-api service
without requiring sys.path manipulation.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Ensure the package is available for testing
try:
    import sparkjar_crew
except ImportError:
    # If the package isn't installed, provide helpful error message
    pytest.exit(
        "sparkjar_crew package not found. Please install with: pip install -e .",
        returncode=1
    )

# Set up test environment variables if not already set
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_crew_api_db"

if not os.getenv("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "test_secret_key_for_crew_api_testing_only"

if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "test_openai_key"

if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/test_credentials.json"

@pytest.fixture
def crew_api_config():
    """Provide crew API configuration for testing."""
    return {
        "database_url": os.getenv("DATABASE_URL"),
        "jwt_secret": os.getenv("JWT_SECRET"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "test_mode": True
    }

@pytest.fixture
def mock_crew_job():
    """Provide a mock crew job for testing."""
    return MagicMock(
        id="test-job-id",
        status="pending",
        payload={"test": "data"},
        result=None
    )

@pytest.fixture
def mock_database_session():
    """Provide a mock database session for testing."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    return session

@pytest.fixture
async def mock_async_session():
    """Provide a mock async database session for testing."""
    session = AsyncMock()
    session.execute.return_value = AsyncMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    return session

@pytest.fixture
def project_root():
    """Provide the project root directory."""
    return Path(__file__).parent.parent.parent.parent