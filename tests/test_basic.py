"""
Test suite for basic functionality.
Tests core components without requiring full dependency installation.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path

def test_config_loading():
    """Test configuration loading."""
    from services.crew_api.src.config import CHROMA_URL, EMBEDDING_MODEL

    assert CHROMA_URL is not None
    assert EMBEDDING_MODEL == "Alibaba-NLP/gte-multilingual-base"

@patch("src.utils.chroma_client.chromadb")
def test_chroma_client_connection(mock_chromadb):
    """Test ChromaDB client connection."""
    from services.crew_api.src.utils.chroma_client import get_chroma_client

    # Mock the HttpClient
    mock_client = Mock()
    mock_chromadb.HttpClient.return_value = mock_client

    client = get_chroma_client()
    assert client is not None
    mock_chromadb.HttpClient.assert_called_once()

def test_crew_registry():
    """Test crew registry functionality using CREW_REGISTRY."""
    from services.crew_api.src.crews import CREW_REGISTRY
    from services.crew_api.src.crews.base import BaseCrewHandler

    assert isinstance(CREW_REGISTRY, dict)

    # Only registry entries that are classes should be validated as dynamic crews
    dynamic_entries = {
        name: handler
        for name, handler in CREW_REGISTRY.items()
        if isinstance(handler, type)
    }

    assert all(
        issubclass(handler, BaseCrewHandler) for handler in dynamic_entries.values()
    )

def test_static_crew_kickoff_callable():
    """Ensure static crews expose a callable kickoff function."""
    from importlib import import_module

    from services.crew_api.src.crews import CREW_REGISTRY

    for name, entry in CREW_REGISTRY.items():
        if not isinstance(entry, type):
            module = import_module(f"src.crews.{name}")
            kickoff = getattr(module, "kickoff", None)
            assert callable(kickoff), f"Kickoff not callable for {name}"

@pytest.mark.asyncio
async def test_job_service_creation():
    """Test job service basic functionality."""
    with patch("src.services.job_service.get_direct_session"):
        with patch("src.crews.CREW_REGISTRY", {}):
            from services.crew_api.src.services.job_service import JobService

            service = JobService()
            assert service is not None

def test_api_models():
    """Test API model validation."""
    from services.crew_api.src.api.models import CrewJobRequest, CrewJobResponse

    # Test valid request
    request = CrewJobRequest(
        data={
            "job_key": "hello_crew",
            "client_user_id": "test-user",
            "actor_type": "human",
            "actor_id": "test-actor",
        }
    )

    assert request.job_key == "hello_crew"
    assert request.actor_type == "human"

    # Test response
    response = CrewJobResponse(job_id="test-id", status="queued")

    assert response.job_id == "test-id"
    assert response.status == "queued"

@patch("src.api.auth.jwt")
def test_auth_token_creation(mock_jwt):
    """Test authentication token creation."""
    from services.crew_api.src.api.auth import create_token

    mock_jwt.encode.return_value = "test-token"

    token = create_token("test-user", ["sparkjar_internal"])
    assert token == "test-token"
    mock_jwt.encode.assert_called_once()

def test_base_crew_handler():
    """Test base crew handler functionality."""
    from services.crew_api.src.crews.base import BaseCrewHandler

    # Create a test handler
    class TestHandler(BaseCrewHandler):
        async def execute(self, request_data):
            return {"status": "test"}

    handler = TestHandler()
    metadata = handler.get_job_metadata()

    assert "handler_class" in metadata
    assert metadata["handler_class"] == "TestHandler"

def test_embedding_client_initialization():
    """Test embedding client initialization."""
    with patch("httpx.AsyncClient"):
        from services.crew_api.src.utils.embedding_client import EmbeddingClient

        client = EmbeddingClient()
        assert client.model_name == "Alibaba-NLP/gte-multilingual-base"

if __name__ == "__main__":
    pytest.main([__file__])
