"""
Monitoring and observability metrics collection.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from contextlib import asynccontextmanager
from functools import wraps
import asyncio

from prometheus_client import Counter, Histogram, Gauge, Info
import structlog

logger = structlog.get_logger()


# Prometheus metrics
request_counter = Counter(
    'chat_requests_total',
    'Total number of chat requests',
    ['endpoint', 'status', 'actor_type']
)

response_time_histogram = Histogram(
    'chat_response_duration_seconds',
    'Response time for chat requests',
    ['endpoint', 'status'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

active_sessions_gauge = Gauge(
    'chat_active_sessions',
    'Number of active chat sessions'
)

memory_search_histogram = Histogram(
    'memory_search_duration_seconds',
    'Time taken for memory searches',
    ['cache_hit'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
)

thinking_service_counter = Counter(
    'thinking_service_requests_total',
    'Total thinking service requests',
    ['status']
)

streaming_connections_gauge = Gauge(
    'chat_streaming_connections',
    'Number of active streaming connections'
)

error_counter = Counter(
    'chat_errors_total',
    'Total number of errors',
    ['error_category', 'recoverable']
)

token_usage_counter = Counter(
    'chat_tokens_used_total',
    'Total tokens used',
    ['model', 'type']
)

service_info = Info(
    'chat_service',
    'Chat service information'
)


class MetricsCollector:
    """Collects and manages metrics for monitoring."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = time.time()
        
        # Set service info
        service_info.info({
            'version': '1.0.0',
            'environment': 'production',
            'started_at': datetime.utcnow().isoformat()
        })
        
    @asynccontextmanager
    async def track_request(
        self,
        endpoint: str,
        actor_type: str = "unknown"
    ):
        """
        Track request metrics.
        
        Args:
            endpoint: API endpoint
            actor_type: Type of actor making request
        """
        start_time = time.time()
        status = "success"
        
        try:
            yield
        except Exception as e:
            status = "error"
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            request_counter.labels(
                endpoint=endpoint,
                status=status,
                actor_type=actor_type
            ).inc()
            
            response_time_histogram.labels(
                endpoint=endpoint,
                status=status
            ).observe(duration)
            
            # Structured logging
            logger.info(
                "request_completed",
                endpoint=endpoint,
                status=status,
                duration_ms=int(duration * 1000),
                actor_type=actor_type
            )
            
    def track_memory_search(self, duration: float, cache_hit: bool):
        """
        Track memory search metrics.
        
        Args:
            duration: Search duration in seconds
            cache_hit: Whether result was from cache
        """
        memory_search_histogram.labels(
            cache_hit=str(cache_hit)
        ).observe(duration)
        
        logger.debug(
            "memory_search_completed",
            duration_ms=int(duration * 1000),
            cache_hit=cache_hit
        )
        
    def track_thinking_service(self, success: bool):
        """
        Track thinking service usage.
        
        Args:
            success: Whether request succeeded
        """
        status = "success" if success else "error"
        thinking_service_counter.labels(status=status).inc()
        
    def track_error(
        self,
        error_category: str,
        recoverable: bool,
        error_message: str
    ):
        """
        Track error occurrence.
        
        Args:
            error_category: Category of error
            recoverable: Whether error is recoverable
            error_message: Error message
        """
        error_counter.labels(
            error_category=error_category,
            recoverable=str(recoverable)
        ).inc()
        
        logger.error(
            "error_occurred",
            error_category=error_category,
            recoverable=recoverable,
            error_message=error_message
        )
        
    def track_token_usage(
        self,
        tokens: int,
        model: str = "gpt-4o-mini",
        usage_type: str = "completion"
    ):
        """
        Track token usage.
        
        Args:
            tokens: Number of tokens used
            model: Model name
            usage_type: Type of usage (prompt/completion)
        """
        token_usage_counter.labels(
            model=model,
            type=usage_type
        ).inc(tokens)
        
    def update_active_sessions(self, count: int):
        """Update active session count."""
        active_sessions_gauge.set(count)
        
    def update_streaming_connections(self, delta: int):
        """Update streaming connection count."""
        if delta > 0:
            streaming_connections_gauge.inc(delta)
        else:
            streaming_connections_gauge.dec(abs(delta))
            
    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self.start_time
        
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get health check metrics.
        
        Returns:
            Health metrics dictionary
        """
        return {
            "uptime_seconds": self.get_uptime(),
            "active_sessions": active_sessions_gauge._value.get(),
            "streaming_connections": streaming_connections_gauge._value.get(),
            "start_time": datetime.fromtimestamp(self.start_time).isoformat()
        }


# Global metrics instance
metrics = MetricsCollector()


# Decorator for tracking async functions
def track_async_operation(
    operation_name: str,
    track_errors: bool = True
):
    """
    Decorator to track async operation metrics.
    
    Args:
        operation_name: Name of the operation
        track_errors: Whether to track errors
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Log success
                duration = time.time() - start_time
                logger.info(
                    f"{operation_name}_completed",
                    duration_ms=int(duration * 1000),
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                if track_errors:
                    logger.error(
                        f"{operation_name}_failed",
                        duration_ms=int(duration * 1000),
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                raise
                
        return wrapper
    return decorator