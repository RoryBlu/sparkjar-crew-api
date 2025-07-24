import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src package to path

from services.crew_api.src.utils.embedding_client import EmbeddingClient
from services.crew_api.src.utils.chroma_client import test_chroma_connection as chroma_test_connection

@pytest.mark.asyncio
async def test_embedding_client_get_embeddings():
    """EmbeddingClient.get_embeddings returns embeddings using mocked httpx."""
    sample = [[0.1, 0.2, 0.3]]
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": sample}
        mock_response.raise_for_status.return_value = None
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        client = EmbeddingClient()
        result = await client.get_embeddings("hello")

        assert result == sample
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()

def test_chroma_test_connection_success():
    """test_chroma_connection returns success with mocked clients."""
    mock_collections = [MagicMock(name="col1"), MagicMock(name="col2")]
    with patch("src.utils.chroma_client.httpx.Client") as mock_httpx, patch(
        "src.utils.chroma_client.get_chroma_client"
    ) as mock_get_client:
        mock_httpx.return_value.__enter__.return_value.get.return_value.status_code = 200
        mock_client = MagicMock()
        mock_client.list_collections.return_value = mock_collections
        mock_get_client.return_value = mock_client

        result = chroma_test_connection()

        assert result["status"] == "success"
        assert result["total_collections"] == len(mock_collections)

