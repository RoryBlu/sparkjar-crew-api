"""
Structured logging configuration for better observability.
"""

import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar
from uuid import UUID

import structlog
from structlog.processors import CallsiteParameter

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
actor_id_var: ContextVar[Optional[str]] = ContextVar('actor_id', default=None)


def add_context_vars(logger, method_name, event_dict):
    """Add context variables to log entries."""
    event_dict['request_id'] = request_id_var.get()
    event_dict['session_id'] = session_id_var.get()
    event_dict['actor_id'] = actor_id_var.get()
    event_dict['timestamp'] = datetime.utcnow().isoformat()
    return event_dict


def setup_structured_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    service_name: str = "chat-interface"
):
    """
    Configure structured logging.
    
    Args:
        log_level: Logging level
        log_format: Output format (json or console)
        service_name: Name of the service
    """
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_context_vars,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ],
        ),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
        
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Add service name to all logs
    structlog.contextvars.bind_contextvars(service=service_name)


class LoggingContext:
    """Context manager for request-scoped logging."""
    
    def __init__(
        self,
        request_id: str,
        session_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None
    ):
        """
        Initialize logging context.
        
        Args:
            request_id: Unique request ID
            session_id: Chat session ID
            actor_id: Actor ID
        """
        self.request_id = request_id
        self.session_id = str(session_id) if session_id else None
        self.actor_id = str(actor_id) if actor_id else None
        self._tokens = []
        
    def __enter__(self):
        """Enter context and set context vars."""
        self._tokens.append(request_id_var.set(self.request_id))
        if self.session_id:
            self._tokens.append(session_id_var.set(self.session_id))
        if self.actor_id:
            self._tokens.append(actor_id_var.set(self.actor_id))
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset vars."""
        for token in self._tokens:
            token.var.reset(token)


def log_performance(
    operation: str,
    duration_ms: int,
    **kwargs
):
    """
    Log performance metrics.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        **kwargs: Additional context
    """
    logger = structlog.get_logger()
    logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        **kwargs
    )


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    **kwargs
):
    """
    Log API request details.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status
        duration_ms: Request duration
        **kwargs: Additional context
    """
    logger = structlog.get_logger()
    
    log_method = logger.info if status_code < 400 else logger.error
    
    log_method(
        "api_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_memory_operation(
    operation: str,
    entity_count: int,
    cache_hit: bool,
    duration_ms: int,
    **kwargs
):
    """
    Log memory service operations.
    
    Args:
        operation: Operation type
        entity_count: Number of entities
        cache_hit: Whether cache was hit
        duration_ms: Operation duration
        **kwargs: Additional context
    """
    logger = structlog.get_logger()
    logger.info(
        "memory_operation",
        operation=operation,
        entity_count=entity_count,
        cache_hit=cache_hit,
        duration_ms=duration_ms,
        **kwargs
    )


def log_error_with_context(
    error: Exception,
    operation: str,
    recoverable: bool = True,
    **kwargs
):
    """
    Log error with full context.
    
    Args:
        error: Exception that occurred
        operation: Operation that failed
        recoverable: Whether error is recoverable
        **kwargs: Additional context
    """
    logger = structlog.get_logger()
    logger.error(
        "operation_failed",
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        recoverable=recoverable,
        **kwargs,
        exc_info=True
    )