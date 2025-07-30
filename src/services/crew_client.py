"""
HTTP client for communicating with the SparkJAR Crews Service

This client handles crew execution requests to the distributed crews service,
providing retry logic, error handling, and proper authentication.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from config import CREWS_SERVICE_URL
from sparkjar_shared.auth import get_internal_token
from sparkjar_shared.schemas import CrewExecutionRequest, CrewExecutionResponse
from .crew_client_exceptions import (
    CrewClientError,
    CrewNotFoundError,
    CrewExecutionError,
    CrewServiceUnavailableError
)
from .crew_client_config import (
    DEFAULT_CONFIG,
    create_http_client_config,
    get_error_for_status_code,
    is_retryable_error,
    format_request_metrics,
    format_crew_execution_metrics
)

logger = logging.getLogger(__name__)


class CrewClient:
    """
    HTTP client for executing crews via the SparkJAR Crews Service
    
    Features:
    - Automatic retry with exponential backoff
    - Connection pooling and timeout handling
    - JWT authentication with token refresh
    - Structured error handling and logging
    - Request tracing and metrics
    """
    
    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize the crew client
        
        Args:
            base_url: Base URL for the crews service (defaults to config)
            config: Client configuration (uses default if None)
        """
        self.base_url = (base_url or CREWS_SERVICE_URL).rstrip('/')
        self.config = config or DEFAULT_CONFIG
        
        # HTTP client configuration
        self.http_config = create_http_client_config(self.config)
        
        # Internal token cache
        self._token_cache = None
        self._token_expires = None
        
        logger.info(
            f"CrewClient initialized for service at {self.base_url}",
            extra={
                "base_url": self.base_url,
                "connect_timeout": self.config.connect_timeout,
                "read_timeout": self.config.read_timeout,
                "max_connections": self.config.max_connections
            }
        )
    
    def _get_auth_token(self) -> str:
        """
        Get or refresh internal authentication token
        
        Returns:
            Valid JWT token for internal service communication
        """
        now = datetime.utcnow()
        
        # Check if cached token is still valid (with configured buffer)
        buffer_minutes = self.config.token_refresh_buffer
        if (self._token_cache and self._token_expires and 
            self._token_expires > now + timedelta(minutes=buffer_minutes)):
            return self._token_cache
        
        # Generate new token
        self._token_cache = get_internal_token()
        self._token_expires = now + timedelta(hours=self.config.token_cache_duration)
        
        logger.debug("Generated new internal authentication token")
        return self._token_cache
    
    def _map_http_error(self, response: httpx.Response) -> CrewClientError:
        """
        Map HTTP response to appropriate exception
        
        Args:
            response: HTTP response object
            
        Returns:
            Appropriate exception for the error
        """
        try:
            error_data = response.json()
            detail = error_data.get('detail', 'Unknown error')
        except (json.JSONDecodeError, KeyError):
            detail = response.text or f"HTTP {response.status_code} error"
        
        return get_error_for_status_code(response.status_code, detail)
    
    @retry(
        stop=stop_after_attempt(DEFAULT_CONFIG.max_retries),
        wait=wait_exponential(
            multiplier=DEFAULT_CONFIG.retry_multiplier,
            min=DEFAULT_CONFIG.retry_min_wait,
            max=DEFAULT_CONFIG.retry_max_wait
        ),
        retry=retry_if_exception_type((
            httpx.ConnectError,
            httpx.TimeoutException,
            CrewServiceUnavailableError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            CrewClientError: On request failure
        """
        url = f"{self.base_url}{endpoint}"
        
        # Add authentication header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self._get_auth_token()}"
        kwargs['headers'] = headers
        
        # Add request ID for tracing
        request_id = kwargs.get('request_id', f"crew-client-{datetime.utcnow().timestamp()}")
        headers['X-Request-ID'] = request_id
        
        start_time = datetime.utcnow()
        logger.info(f"Making {method} request to {endpoint}", extra={'request_id': request_id})
        
        async with httpx.AsyncClient(**self.http_config) as client:
            try:
                response = await client.request(method, url, **kwargs)
                
                # Calculate request duration
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Log with metrics
                metrics = format_request_metrics(
                    method=method,
                    endpoint=endpoint,
                    status_code=response.status_code,
                    duration=duration,
                    request_id=request_id
                )
                
                logger.info(
                    f"Request completed: {method} {endpoint} - {response.status_code}",
                    extra=metrics
                )
                
                return response
                
            except httpx.ConnectError as e:
                logger.error(f"Connection failed to {url}: {e}", extra={'request_id': request_id})
                raise CrewServiceUnavailableError(f"Cannot connect to crews service: {e}")
            
            except httpx.TimeoutException as e:
                logger.error(f"Request timeout to {url}: {e}", extra={'request_id': request_id})
                raise CrewServiceUnavailableError(f"Request timeout: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}", extra={'request_id': request_id})
                raise CrewClientError(f"Request failed: {e}")
    
    async def execute_crew(
        self,
        crew_name: str,
        inputs: Dict[str, Any],
        timeout: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a crew via HTTP call to crews service
        
        Args:
            crew_name: Name of the crew to execute
            inputs: Input parameters for the crew
            timeout: Execution timeout in seconds (default from config)
            request_id: Optional request ID for tracing
            
        Returns:
            Crew execution result
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
            CrewExecutionError: If crew execution fails
            CrewServiceUnavailableError: If service is unavailable
        """
        start_time = datetime.utcnow()
        request_id = request_id or f"execute-{crew_name}-{start_time.timestamp()}"
        
        logger.info(
            f"Executing crew '{crew_name}' via HTTP",
            extra={
                'request_id': request_id,
                'crew_name': crew_name,
                'timeout': timeout or 300
            }
        )
        
        # Prepare request
        request_data = CrewExecutionRequest(
            crew_name=crew_name,
            inputs=inputs,
            timeout=timeout or self.config.default_crew_timeout
        )
        
        try:
            # Make HTTP request
            response = await self._make_request(
                method="POST",
                endpoint="/execute_crew",
                json=request_data.dict(),
                request_id=request_id
            )
            
            # Handle HTTP errors
            if not response.is_success:
                raise self._map_http_error(response)
            
            # Parse response
            result_data = response.json()
            execution_result = CrewExecutionResponse(**result_data)
            
            # Calculate total execution time
            total_time = (datetime.utcnow() - start_time).total_seconds()
            
            if execution_result.success:
                # Log success with metrics
                metrics = format_crew_execution_metrics(
                    crew_name=crew_name,
                    success=True,
                    execution_time=execution_result.execution_time,
                    total_time=total_time,
                    request_id=request_id
                )
                
                logger.info(
                    f"Crew '{crew_name}' executed successfully in {total_time:.2f}s",
                    extra=metrics
                )
                
                return {
                    "success": True,
                    "result": execution_result.result,
                    "execution_time": execution_result.execution_time,
                    "total_time": total_time,
                    "crew_name": crew_name,
                    "request_id": request_id,
                    "timestamp": execution_result.timestamp
                }
            else:
                # Log failure with metrics
                metrics = format_crew_execution_metrics(
                    crew_name=crew_name,
                    success=False,
                    execution_time=execution_result.execution_time,
                    total_time=total_time,
                    error=execution_result.error,
                    request_id=request_id
                )
                
                logger.error(
                    f"Crew '{crew_name}' execution failed: {execution_result.error}",
                    extra=metrics
                )
                
                raise CrewExecutionError(
                    f"Crew execution failed: {execution_result.error}"
                )
                
        except (CrewClientError, CrewNotFoundError, CrewExecutionError):
            # Re-raise known exceptions
            raise
            
        except Exception as e:
            total_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                f"Unexpected error executing crew '{crew_name}': {e}",
                extra={
                    'request_id': request_id,
                    'crew_name': crew_name,
                    'total_time': total_time,
                    'error': str(e)
                }
            )
            raise CrewClientError(f"Unexpected error: {e}")
    
    async def list_crews(self, request_id: Optional[str] = None) -> List[str]:
        """
        List available crews from the service
        
        Args:
            request_id: Optional request ID for tracing
            
        Returns:
            List of available crew names
            
        Raises:
            CrewServiceUnavailableError: If service is unavailable
        """
        request_id = request_id or f"list-crews-{datetime.utcnow().timestamp()}"
        
        logger.info("Listing available crews", extra={'request_id': request_id})
        
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/crews",
                request_id=request_id
            )
            
            if not response.is_success:
                raise self._map_http_error(response)
            
            data = response.json()
            crew_names = list(data.get('available_crews', {}).keys())
            
            logger.info(
                f"Found {len(crew_names)} available crews",
                extra={'request_id': request_id, 'crew_count': len(crew_names)}
            )
            
            return crew_names
            
        except CrewClientError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to list crews: {e}",
                extra={'request_id': request_id, 'error': str(e)}
            )
            raise CrewServiceUnavailableError(f"Failed to list crews: {e}")
    
    async def health_check(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check health of the crews service
        
        Args:
            request_id: Optional request ID for tracing
            
        Returns:
            Health status information
            
        Raises:
            CrewServiceUnavailableError: If service is unavailable
        """
        request_id = request_id or f"health-check-{datetime.utcnow().timestamp()}"
        
        logger.debug("Checking crews service health", extra={'request_id': request_id})
        
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health",
                request_id=request_id
            )
            
            if not response.is_success:
                raise self._map_http_error(response)
            
            health_data = response.json()
            
            logger.debug(
                f"Crews service health: {health_data.get('status', 'unknown')}",
                extra={'request_id': request_id}
            )
            
            return health_data
            
        except CrewClientError:
            raise
        except Exception as e:
            logger.error(
                f"Health check failed: {e}",
                extra={'request_id': request_id, 'error': str(e)}
            )
            raise CrewServiceUnavailableError(f"Health check failed: {e}")
    
    async def close(self):
        """Close the client and cleanup resources"""
        # Clear token cache
        self._token_cache = None
        self._token_expires = None
        
        logger.info("CrewClient closed")


# Global client instance
_crew_client = None


def get_crew_client() -> CrewClient:
    """Get the global CrewClient instance"""
    global _crew_client
    if _crew_client is None:
        _crew_client = CrewClient()
    return _crew_client


async def close_crew_client():
    """Close the global crew client"""
    global _crew_client
    if _crew_client is not None:
        await _crew_client.close()
        _crew_client = None