"""
Integration tests for CrewClient

Tests the HTTP client that communicates with the SparkJAR Crews Service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from datetime import datetime, timedelta

from services.crew_client import CrewClient, get_crew_client
from services.crew_client_exceptions import (
    CrewClientError,
    CrewNotFoundError,
    CrewExecutionError,
    CrewServiceUnavailableError
)


class TestCrewClient:
    """Test cases for CrewClient"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return CrewClient(base_url="http://test-crews-service:8001")
    
    @pytest.fixture
    def mock_token(self):
        """Mock internal token"""
        return "test.jwt.token"
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock successful crew execution response"""
        return {
            "success": True,
            "crew_name": "test_crew",
            "result": "Test crew executed successfully",
            "error": None,
            "execution_time": 45.2,
            "timestamp": "2025-01-01T12:00:00Z"
        }
    
    @pytest.fixture
    def mock_health_data(self):
        """Mock health check response"""
        return {
            "status": "healthy",
            "service": "sparkjar-crews",
            "environment": "test",
            "available_crews": ["test_crew", "another_crew"],
            "timestamp": "2025-01-01T12:00:00Z"
        }
    
    @pytest.fixture
    def mock_crews_list_data(self):
        """Mock crews list response"""
        return {
            "available_crews": {
                "test_crew": {
                    "class_name": "TestCrew",
                    "module": "test.module",
                    "description": "Test crew"
                },
                "another_crew": {
                    "class_name": "AnotherCrew",
                    "module": "another.module",
                    "description": "Another test crew"
                }
            },
            "total_count": 2,
            "timestamp": "2025-01-01T12:00:00Z"
        }
    
    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.base_url == "http://test-crews-service:8001"
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 300.0
        assert client.limits.max_connections == 20
    
    @patch('services.crew_client.get_internal_token')
    def test_get_auth_token_caching(self, mock_get_token, client):
        """Test token caching mechanism"""
        mock_get_token.return_value = "test.token.123"
        
        # First call should generate token
        token1 = client._get_auth_token()
        assert token1 == "test.token.123"
        assert mock_get_token.call_count == 1
        
        # Second call should use cached token
        token2 = client._get_auth_token()
        assert token2 == "test.token.123"
        assert mock_get_token.call_count == 1  # No additional calls
        
        # Simulate token expiration
        client._token_expires = datetime.utcnow() - timedelta(minutes=1)
        token3 = client._get_auth_token()
        assert token3 == "test.token.123"
        assert mock_get_token.call_count == 2  # New token generated
    
    def test_map_http_error(self, client):
        """Test HTTP error mapping"""
        # Test 404 error
        response_404 = Mock()
        response_404.status_code = 404
        response_404.json.return_value = {"detail": "Crew not found"}
        
        error = client._map_http_error(response_404)
        assert isinstance(error, CrewNotFoundError)
        assert "Crew not found" in str(error)
        
        # Test 401 error
        response_401 = Mock()
        response_401.status_code = 401
        response_401.json.return_value = {"detail": "Invalid token"}
        
        error = client._map_http_error(response_401)
        assert isinstance(error, CrewClientError)
        assert "Authentication failed" in str(error)
        
        # Test 500 error
        response_500 = Mock()
        response_500.status_code = 500
        response_500.json.return_value = {"detail": "Internal server error"}
        
        error = client._map_http_error(response_500)
        assert isinstance(error, CrewServiceUnavailableError)
        assert "Service unavailable" in str(error)
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_execute_crew_success(self, mock_get_token, client, mock_response_data):
        """Test successful crew execution"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock successful response
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_response_data
            mock_client.request.return_value = mock_response
            
            result = await client.execute_crew(
                crew_name="test_crew",
                inputs={"test_input": "value"}
            )
            
            assert result["success"] is True
            assert result["crew_name"] == "test_crew"
            assert result["result"] == "Test crew executed successfully"
            assert "execution_time" in result
            assert "total_time" in result
            
            # Verify request was made correctly
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args[0][0] == "POST"  # method
            assert "/execute_crew" in call_args[0][1]  # URL
            assert "json" in call_args[1]  # request body
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_execute_crew_not_found(self, mock_get_token, client):
        """Test crew not found error"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock 404 response
            mock_response = Mock()
            mock_response.is_success = False
            mock_response.status_code = 404
            mock_response.json.return_value = {"detail": "Crew 'nonexistent' not found"}
            mock_client.request.return_value = mock_response
            
            with pytest.raises(CrewNotFoundError) as exc_info:
                await client.execute_crew(
                    crew_name="nonexistent",
                    inputs={"test": "data"}
                )
            
            assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_execute_crew_execution_failure(self, mock_get_token, client):
        """Test crew execution failure"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock successful HTTP response but failed crew execution
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = {
                "success": False,
                "crew_name": "test_crew",
                "result": None,
                "error": "Crew execution failed due to invalid input",
                "execution_time": 10.5,
                "timestamp": "2025-01-01T12:00:00Z"
            }
            mock_client.request.return_value = mock_response
            
            with pytest.raises(CrewExecutionError) as exc_info:
                await client.execute_crew(
                    crew_name="test_crew",
                    inputs={"invalid": "input"}
                )
            
            assert "execution failed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_execute_crew_connection_error(self, mock_get_token, client):
        """Test connection error handling"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock connection error
            mock_client.request.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(CrewServiceUnavailableError) as exc_info:
                await client.execute_crew(
                    crew_name="test_crew",
                    inputs={"test": "data"}
                )
            
            assert "connect" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_execute_crew_timeout(self, mock_get_token, client):
        """Test timeout handling"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock timeout error
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(CrewServiceUnavailableError) as exc_info:
                await client.execute_crew(
                    crew_name="test_crew",
                    inputs={"test": "data"}
                )
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_list_crews_success(self, mock_get_token, client, mock_crews_list_data):
        """Test successful crew listing"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock successful response
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_crews_list_data
            mock_client.request.return_value = mock_response
            
            crews = await client.list_crews()
            
            assert len(crews) == 2
            assert "test_crew" in crews
            assert "another_crew" in crews
            
            # Verify request was made correctly
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args[0][0] == "GET"  # method
            assert "/crews" in call_args[0][1]  # URL
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_health_check_success(self, mock_get_token, client, mock_health_data):
        """Test successful health check"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock successful response
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_health_data
            mock_client.request.return_value = mock_response
            
            health = await client.health_check()
            
            assert health["status"] == "healthy"
            assert health["service"] == "sparkjar-crews"
            assert len(health["available_crews"]) == 2
            
            # Verify request was made correctly
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args[0][0] == "GET"  # method
            assert "/health" in call_args[0][1]  # URL
    
    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client cleanup"""
        # Set some cached data
        client._token_cache = "test.token"
        client._token_expires = datetime.utcnow() + timedelta(hours=1)
        
        await client.close()
        
        # Verify cache is cleared
        assert client._token_cache is None
        assert client._token_expires is None
    
    def test_global_client_singleton(self):
        """Test global client singleton pattern"""
        client1 = get_crew_client()
        client2 = get_crew_client()
        
        assert client1 is client2  # Same instance
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_retry_mechanism(self, mock_get_token, client):
        """Test retry mechanism for transient failures"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # First two calls fail, third succeeds
            mock_client.request.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                Mock(is_success=True, json=lambda: {"status": "healthy"})
            ]
            
            # Should succeed after retries
            result = await client.health_check()
            assert result["status"] == "healthy"
            
            # Verify retry attempts
            assert mock_client.request.call_count == 3
    
    @pytest.mark.asyncio
    @patch('services.crew_client.get_internal_token')
    async def test_request_tracing(self, mock_get_token, client):
        """Test request ID tracing"""
        mock_get_token.return_value = "test.token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = {"status": "healthy"}
            mock_client.request.return_value = mock_response
            
            # Test with custom request ID
            await client.health_check(request_id="test-request-123")
            
            # Verify request ID was added to headers
            call_args = mock_client.request.call_args
            headers = call_args[1]["headers"]
            assert headers["X-Request-ID"] == "test-request-123"
            assert "Authorization" in headers


if __name__ == "__main__":
    pytest.main([__file__])