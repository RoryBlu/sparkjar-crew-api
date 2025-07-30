"""
Configuration and utilities for CrewClient

This module provides configuration constants, error mapping utilities,
and connection pooling settings for the crew client.
"""

from typing import Dict, Type
import httpx
from dataclasses import dataclass

from .crew_client_exceptions import (
    CrewClientError,
    CrewNotFoundError,
    CrewExecutionError,
    CrewServiceUnavailableError
)


@dataclass
class CrewClientConfig:
    """Configuration settings for CrewClient"""
    
    # Timeout settings (in seconds)
    connect_timeout: float = 5.0      # Time to establish connection
    read_timeout: float = 300.0       # Time to read response (5 minutes for crew execution)
    write_timeout: float = 10.0       # Time to write request
    pool_timeout: float = 2.0         # Time to get connection from pool
    
    # Connection pool settings
    max_keepalive_connections: int = 10    # Max persistent connections
    max_connections: int = 20              # Max total connections
    keepalive_expiry: float = 30.0         # Connection keepalive time
    
    # Retry settings
    max_retries: int = 3                   # Maximum retry attempts
    retry_min_wait: float = 1.0            # Minimum wait between retries
    retry_max_wait: float = 10.0           # Maximum wait between retries
    retry_multiplier: float = 1.0          # Exponential backoff multiplier
    
    # Token settings
    token_refresh_buffer: int = 5          # Minutes before expiry to refresh token
    token_cache_duration: int = 23         # Hours to cache token (refresh at 23h)
    
    # Request settings
    default_crew_timeout: int = 300        # Default crew execution timeout
    request_id_prefix: str = "crew-client" # Prefix for generated request IDs


# Default configuration instance
DEFAULT_CONFIG = CrewClientConfig()


# HTTP status code to exception mapping
HTTP_ERROR_MAPPING: Dict[int, Type[CrewClientError]] = {
    400: CrewClientError,           # Bad Request
    401: CrewClientError,           # Unauthorized
    403: CrewClientError,           # Forbidden
    404: CrewNotFoundError,         # Not Found
    422: CrewClientError,           # Unprocessable Entity
    429: CrewServiceUnavailableError,  # Too Many Requests
    500: CrewServiceUnavailableError,  # Internal Server Error
    502: CrewServiceUnavailableError,  # Bad Gateway
    503: CrewServiceUnavailableError,  # Service Unavailable
    504: CrewServiceUnavailableError,  # Gateway Timeout
}


# HTTP exceptions that should trigger retries
RETRYABLE_HTTP_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
)


# HTTP status codes that should trigger retries
RETRYABLE_STATUS_CODES = {
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}


def create_http_client_config(config: CrewClientConfig = None) -> Dict:
    """
    Create httpx client configuration from CrewClientConfig
    
    Args:
        config: Configuration object (uses default if None)
        
    Returns:
        Dictionary of httpx client configuration
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    return {
        "timeout": httpx.Timeout(
            connect=config.connect_timeout,
            read=config.read_timeout,
            write=config.write_timeout,
            pool=config.pool_timeout
        ),
        "limits": httpx.Limits(
            max_keepalive_connections=config.max_keepalive_connections,
            max_connections=config.max_connections,
            keepalive_expiry=config.keepalive_expiry
        ),
        "follow_redirects": True,
        "verify": True,  # SSL verification
    }


def get_error_for_status_code(status_code: int, detail: str = None) -> CrewClientError:
    """
    Get appropriate exception for HTTP status code
    
    Args:
        status_code: HTTP status code
        detail: Error detail message
        
    Returns:
        Appropriate exception instance
    """
    error_class = HTTP_ERROR_MAPPING.get(status_code, CrewClientError)
    
    if detail:
        message = f"HTTP {status_code}: {detail}"
    else:
        message = f"HTTP {status_code} error"
    
    return error_class(message)


def is_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception should trigger a retry
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the error is retryable
    """
    # Check for retryable HTTP exceptions
    if isinstance(exception, RETRYABLE_HTTP_EXCEPTIONS):
        return True
    
    # Check for retryable service errors
    if isinstance(exception, CrewServiceUnavailableError):
        return True
    
    return False


def is_retryable_status_code(status_code: int) -> bool:
    """
    Check if an HTTP status code should trigger a retry
    
    Args:
        status_code: HTTP status code
        
    Returns:
        True if the status code is retryable
    """
    return status_code in RETRYABLE_STATUS_CODES


def format_request_metrics(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    request_id: str = None
) -> Dict:
    """
    Format request metrics for logging
    
    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        duration: Request duration in seconds
        request_id: Optional request ID
        
    Returns:
        Formatted metrics dictionary
    """
    metrics = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_seconds": round(duration, 3),
        "success": 200 <= status_code < 400
    }
    
    if request_id:
        metrics["request_id"] = request_id
    
    return metrics


def format_crew_execution_metrics(
    crew_name: str,
    success: bool,
    execution_time: float = None,
    total_time: float = None,
    error: str = None,
    request_id: str = None
) -> Dict:
    """
    Format crew execution metrics for logging
    
    Args:
        crew_name: Name of the executed crew
        success: Whether execution was successful
        execution_time: Crew execution time in seconds
        total_time: Total request time in seconds
        error: Error message if failed
        request_id: Optional request ID
        
    Returns:
        Formatted metrics dictionary
    """
    metrics = {
        "crew_name": crew_name,
        "success": success,
        "operation": "crew_execution"
    }
    
    if execution_time is not None:
        metrics["execution_time_seconds"] = round(execution_time, 3)
    
    if total_time is not None:
        metrics["total_time_seconds"] = round(total_time, 3)
    
    if error:
        metrics["error"] = error
    
    if request_id:
        metrics["request_id"] = request_id
    
    return metrics