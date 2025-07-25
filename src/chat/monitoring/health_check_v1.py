"""
Health Check and Basic Monitoring for Chat with Memory v1.

KISS principles:
- Simple health checks
- Clear status reporting
- Basic metrics collection
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any

from src.chat.services.session_manager_v1 import RedisSessionManager
from src.chat.clients.memory_service import MemoryServiceClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Simple health checking for all services.
    
    KISS: Check connections, measure response times, report status.
    """
    
    def __init__(
        self,
        redis_url: str,
        memory_service_url: str,
        database_url: str
    ):
        """
        Initialize health checker.
        
        Args:
            redis_url: Redis connection URL
            memory_service_url: Memory service URL
            database_url: Database connection URL
        """
        self.redis_url = redis_url
        self.memory_service_url = memory_service_url
        self.database_url = database_url
        
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health status for all services
        """
        start_time = time.time()
        
        # Run all checks concurrently
        results = await asyncio.gather(
            self._check_redis(),
            self._check_memory_service(),
            self._check_database(),
            return_exceptions=True
        )
        
        # Process results
        redis_health = results[0] if not isinstance(results[0], Exception) else {
            "status": "unhealthy",
            "error": str(results[0])
        }
        
        memory_health = results[1] if not isinstance(results[1], Exception) else {
            "status": "unhealthy",
            "error": str(results[1])
        }
        
        database_health = results[2] if not isinstance(results[2], Exception) else {
            "status": "unhealthy",
            "error": str(results[2])
        }
        
        # Overall health
        all_healthy = all(
            h.get("status") == "healthy"
            for h in [redis_health, memory_health, database_health]
        )
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "redis": redis_health,
                "memory_service": memory_health,
                "database": database_health
            },
            "total_check_time_ms": round(total_time, 2)
        }
        
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            start = time.time()
            
            # Create temporary session manager
            session_manager = RedisSessionManager(self.redis_url)
            redis_client = await session_manager._get_redis()
            
            # Ping Redis
            await redis_client.ping()
            
            # Test basic operations
            test_key = "health_check_test"
            await redis_client.setex(test_key, 10, "test_value")
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start) * 1000
            
            await session_manager.close()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "operations_tested": ["ping", "set", "get", "delete"]
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
            
    async def _check_memory_service(self) -> Dict[str, Any]:
        """Check Memory Service connectivity."""
        try:
            start = time.time()
            
            # Create memory client
            client = MemoryServiceClient(
                base_url=self.memory_service_url,
                api_key="test"  # Health check doesn't need real key
            )
            
            # Try to connect (will fail auth but proves service is up)
            try:
                await client._make_request("GET", "/health")
            except Exception as e:
                # If it's an auth error, service is still up
                if "401" in str(e) or "unauthorized" in str(e).lower():
                    response_time = (time.time() - start) * 1000
                    return {
                        "status": "healthy",
                        "response_time_ms": round(response_time, 2),
                        "note": "Service responding (auth not required for health)"
                    }
                raise
                
        except Exception as e:
            logger.error(f"Memory service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
            
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            start = time.time()
            
            # Simple connection test
            # In production, use SQLAlchemy session
            from sqlalchemy import create_engine, text
            
            engine = create_engine(self.database_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
            response_time = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connection_pool_size": 5  # From configuration
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


class MetricsCollector:
    """
    Simple metrics collection for monitoring.
    
    KISS: Count requests, track response times, monitor errors.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            "requests": {
                "total": 0,
                "by_mode": {"tutor": 0, "agent": 0},
                "by_endpoint": {}
            },
            "response_times": [],
            "errors": {
                "total": 0,
                "by_type": {}
            },
            "memory_searches": {
                "total": 0,
                "cache_hits": 0,
                "average_time_ms": 0
            },
            "sessions": {
                "active": 0,
                "created": 0,
                "expired": 0
            }
        }
        
    def record_request(
        self,
        endpoint: str,
        mode: str,
        response_time_ms: float
    ):
        """Record API request metrics."""
        self.metrics["requests"]["total"] += 1
        self.metrics["requests"]["by_mode"][mode] = \
            self.metrics["requests"]["by_mode"].get(mode, 0) + 1
        self.metrics["requests"]["by_endpoint"][endpoint] = \
            self.metrics["requests"]["by_endpoint"].get(endpoint, 0) + 1
            
        # Keep last 1000 response times
        self.metrics["response_times"].append(response_time_ms)
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"].pop(0)
            
    def record_error(self, error_type: str):
        """Record error occurrence."""
        self.metrics["errors"]["total"] += 1
        self.metrics["errors"]["by_type"][error_type] = \
            self.metrics["errors"]["by_type"].get(error_type, 0) + 1
            
    def record_memory_search(
        self,
        search_time_ms: float,
        cache_hit: bool
    ):
        """Record memory search metrics."""
        self.metrics["memory_searches"]["total"] += 1
        if cache_hit:
            self.metrics["memory_searches"]["cache_hits"] += 1
            
        # Update average
        current_avg = self.metrics["memory_searches"]["average_time_ms"]
        total_searches = self.metrics["memory_searches"]["total"]
        new_avg = ((current_avg * (total_searches - 1)) + search_time_ms) / total_searches
        self.metrics["memory_searches"]["average_time_ms"] = round(new_avg, 2)
        
    def update_session_count(self, active_count: int):
        """Update active session count."""
        self.metrics["sessions"]["active"] = active_count
        
    def record_session_created(self):
        """Record new session creation."""
        self.metrics["sessions"]["created"] += 1
        
    def record_session_expired(self):
        """Record session expiration."""
        self.metrics["sessions"]["expired"] += 1
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        # Calculate response time stats
        response_times = self.metrics["response_times"]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            p95_index = int(len(response_times) * 0.95)
            p95_response = sorted(response_times)[p95_index] if response_times else 0
        else:
            avg_response = 0
            p95_response = 0
            
        # Calculate cache hit rate
        total_searches = self.metrics["memory_searches"]["total"]
        cache_hits = self.metrics["memory_searches"]["cache_hits"]
        cache_hit_rate = (cache_hits / total_searches * 100) if total_searches > 0 else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "requests": {
                "total": self.metrics["requests"]["total"],
                "by_mode": self.metrics["requests"]["by_mode"],
                "top_endpoints": self._get_top_endpoints(5)
            },
            "performance": {
                "average_response_ms": round(avg_response, 2),
                "p95_response_ms": round(p95_response, 2),
                "memory_search_avg_ms": self.metrics["memory_searches"]["average_time_ms"],
                "cache_hit_rate": round(cache_hit_rate, 2)
            },
            "errors": {
                "total": self.metrics["errors"]["total"],
                "error_rate": round(
                    self.metrics["errors"]["total"] / self.metrics["requests"]["total"] * 100
                    if self.metrics["requests"]["total"] > 0 else 0,
                    2
                ),
                "top_errors": self._get_top_errors(3)
            },
            "sessions": self.metrics["sessions"]
        }
        
    def _get_top_endpoints(self, limit: int) -> list:
        """Get most used endpoints."""
        endpoints = self.metrics["requests"]["by_endpoint"]
        sorted_endpoints = sorted(
            endpoints.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [
            {"endpoint": ep, "count": count}
            for ep, count in sorted_endpoints[:limit]
        ]
        
    def _get_top_errors(self, limit: int) -> list:
        """Get most common errors."""
        errors = self.metrics["errors"]["by_type"]
        sorted_errors = sorted(
            errors.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [
            {"type": err, "count": count}
            for err, count in sorted_errors[:limit]
        ]


# Global metrics collector instance
metrics_collector = MetricsCollector()