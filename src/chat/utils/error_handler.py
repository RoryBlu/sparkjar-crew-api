"""
Comprehensive error handling for Chat Interface Service.
"""

import logging
from typing import Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

from fastapi import HTTPException, status
from httpx import HTTPError, TimeoutException, ConnectError

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    MEMORY_SERVICE = "memory_service"
    THINKING_SERVICE = "thinking_service"
    CREW_SERVICE = "crew_service"
    REDIS = "redis"
    TIMEOUT = "timeout"
    NETWORK = "network"
    INTERNAL = "internal"
    STREAMING = "streaming"


class ServiceError(Exception):
    """Base exception for service errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.category = category
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()
        super().__init__(message)


class ChatErrorHandler:
    """Centralized error handling for chat service."""
    
    @staticmethod
    def handle_memory_service_error(error: Exception) -> ServiceError:
        """
        Handle Memory Service related errors.
        
        Args:
            error: The original exception
            
        Returns:
            ServiceError with appropriate details
        """
        if isinstance(error, TimeoutException):
            return ServiceError(
                message="Memory service request timed out",
                category=ErrorCategory.TIMEOUT,
                details={"service": "memory", "error": str(error)},
                recoverable=True
            )
        elif isinstance(error, ConnectError):
            return ServiceError(
                message="Unable to connect to memory service",
                category=ErrorCategory.NETWORK,
                details={"service": "memory", "error": str(error)},
                recoverable=True
            )
        elif isinstance(error, HTTPError):
            return ServiceError(
                message="Memory service HTTP error",
                category=ErrorCategory.MEMORY_SERVICE,
                details={
                    "service": "memory",
                    "error": str(error),
                    "status_code": getattr(error.response, "status_code", None) if hasattr(error, "response") else None
                },
                recoverable=True
            )
        else:
            return ServiceError(
                message=f"Memory service error: {str(error)}",
                category=ErrorCategory.MEMORY_SERVICE,
                details={"service": "memory", "error": str(error)},
                recoverable=False
            )
            
    @staticmethod
    def handle_thinking_service_error(error: Exception) -> ServiceError:
        """
        Handle Sequential Thinking Service related errors.
        
        Args:
            error: The original exception
            
        Returns:
            ServiceError with appropriate details
        """
        if isinstance(error, TimeoutException):
            return ServiceError(
                message="Thinking service request timed out",
                category=ErrorCategory.TIMEOUT,
                details={"service": "thinking", "error": str(error)},
                recoverable=True
            )
        elif isinstance(error, ConnectError):
            return ServiceError(
                message="Unable to connect to thinking service",
                category=ErrorCategory.NETWORK,
                details={"service": "thinking", "error": str(error)},
                recoverable=True
            )
        else:
            return ServiceError(
                message=f"Thinking service error: {str(error)}",
                category=ErrorCategory.THINKING_SERVICE,
                details={"service": "thinking", "error": str(error)},
                recoverable=True  # Thinking service errors are generally recoverable
            )
            
    @staticmethod
    def handle_redis_error(error: Exception) -> ServiceError:
        """
        Handle Redis related errors.
        
        Args:
            error: The original exception
            
        Returns:
            ServiceError with appropriate details
        """
        error_str = str(error).lower()
        
        if "connection" in error_str:
            return ServiceError(
                message="Redis connection error",
                category=ErrorCategory.REDIS,
                details={"error": str(error)},
                recoverable=True
            )
        elif "timeout" in error_str:
            return ServiceError(
                message="Redis operation timed out",
                category=ErrorCategory.TIMEOUT,
                details={"service": "redis", "error": str(error)},
                recoverable=True
            )
        else:
            return ServiceError(
                message=f"Redis error: {str(error)}",
                category=ErrorCategory.REDIS,
                details={"error": str(error)},
                recoverable=False
            )
            
    @staticmethod
    def handle_streaming_error(error: Exception) -> Dict[str, Any]:
        """
        Handle streaming-specific errors.
        
        Args:
            error: The original exception
            
        Returns:
            Error data formatted for SSE
        """
        return {
            "error": True,
            "message": str(error),
            "category": ErrorCategory.STREAMING.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    @staticmethod
    def to_http_exception(service_error: ServiceError) -> HTTPException:
        """
        Convert ServiceError to HTTPException for API responses.
        
        Args:
            service_error: The service error
            
        Returns:
            HTTPException with appropriate status code
        """
        # Map error categories to HTTP status codes
        status_mapping = {
            ErrorCategory.AUTHENTICATION: status.HTTP_401_UNAUTHORIZED,
            ErrorCategory.AUTHORIZATION: status.HTTP_403_FORBIDDEN,
            ErrorCategory.VALIDATION: status.HTTP_400_BAD_REQUEST,
            ErrorCategory.TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
            ErrorCategory.NETWORK: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.MEMORY_SERVICE: status.HTTP_502_BAD_GATEWAY,
            ErrorCategory.THINKING_SERVICE: status.HTTP_502_BAD_GATEWAY,
            ErrorCategory.CREW_SERVICE: status.HTTP_502_BAD_GATEWAY,
            ErrorCategory.REDIS: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.STREAMING: status.HTTP_500_INTERNAL_SERVER_ERROR
        }
        
        status_code = status_mapping.get(
            service_error.category,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        return HTTPException(
            status_code=status_code,
            detail={
                "message": service_error.message,
                "category": service_error.category.value,
                "details": service_error.details,
                "recoverable": service_error.recoverable,
                "timestamp": service_error.timestamp.isoformat()
            }
        )


class ErrorRecovery:
    """Error recovery strategies."""
    
    @staticmethod
    async def with_memory_fallback(
        primary_func,
        fallback_func,
        *args,
        **kwargs
    ):
        """
        Execute with memory service fallback.
        
        Args:
            primary_func: Primary function to execute
            fallback_func: Fallback function if primary fails
            *args: Arguments for functions
            **kwargs: Keyword arguments for functions
            
        Returns:
            Result from primary or fallback function
        """
        try:
            return await primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary memory function failed: {e}, using fallback")
            return await fallback_func(*args, **kwargs)
            
    @staticmethod
    async def with_thinking_fallback(
        thinking_func,
        standard_func,
        *args,
        **kwargs
    ):
        """
        Execute with thinking service fallback.
        
        Args:
            thinking_func: Function that uses thinking service
            standard_func: Standard function without thinking
            *args: Arguments for functions
            **kwargs: Keyword arguments for functions
            
        Returns:
            Result from thinking or standard function
        """
        try:
            return await thinking_func(*args, **kwargs)
        except Exception as e:
            logger.info(f"Thinking service unavailable: {e}, using standard processing")
            return await standard_func(*args, **kwargs)
            
    @staticmethod
    def with_default(func, default_value, *args, **kwargs):
        """
        Execute with default value on error.
        
        Args:
            func: Function to execute
            default_value: Default value to return on error
            *args: Arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result or default value
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"Function failed, returning default: {e}")
            return default_value