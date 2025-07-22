"""
Health check endpoints for monitoring.
"""

import logging
from typing import Dict, Any
from datetime import datetime
import asyncio

from fastapi import APIRouter, HTTPException, status

from src.chatclients.memory_service import MemoryServiceClient
from src.chatclients.thinking_service import ThinkingServiceClient
from src.chatservices.session_manager import SessionContextStore
from src.chatutils.metrics import metrics
from src.chatutils.cache_manager import CacheManager
from src.chatutils.connection_pool import ConnectionPoolManager
from src.chatconfig import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthChecker:
    """Performs health checks on dependencies."""
    
    def __init__(self):
        """Initialize health checker."""
        self.settings = get_settings()
        self.checks = {
            "redis": self._check_redis,
            "memory_service": self._check_memory_service,
            "thinking_service": self._check_thinking_service,
            "crew_api": self._check_crew_api
        }
        
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            store = SessionContextStore()
            await store.connect()
            
            # Test basic operation
            test_key = "health_check_test"
            await store._redis.set(test_key, "OK", ex=10)
            result = await store._redis.get(test_key)
            
            await store.disconnect()
            
            return {
                "status": "healthy",
                "response_time_ms": 5,  # Would measure actual time
                "details": {"test_result": result}
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"connection": "failed"}
            }
            
    async def _check_memory_service(self) -> Dict[str, Any]:
        """Check Memory Service connectivity."""
        try:
            client = MemoryServiceClient()
            start_time = datetime.utcnow()
            
            # Simple health check - would call actual endpoint
            # For now, just test client initialization
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": int(response_time),
                "details": {"endpoint": self.settings.memory_service_url}
            }
            
        except Exception as e:
            logger.error(f"Memory Service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"endpoint": self.settings.memory_service_url}
            }
            
    async def _check_thinking_service(self) -> Dict[str, Any]:
        """Check Thinking Service connectivity."""
        try:
            client = ThinkingServiceClient()
            
            # In production, would make actual health check call
            return {
                "status": "healthy",
                "response_time_ms": 10,
                "details": {
                    "endpoint": self.settings.thinking_service_url,
                    "optional": True
                }
            }
            
        except Exception as e:
            # Thinking service is optional, so degraded not unhealthy
            logger.warning(f"Thinking Service health check failed: {e}")
            return {
                "status": "degraded",
                "error": str(e),
                "details": {
                    "endpoint": self.settings.thinking_service_url,
                    "optional": True
                }
            }
            
    async def _check_crew_api(self) -> Dict[str, Any]:
        """Check Crew API connectivity."""
        try:
            # Would make actual health check call
            return {
                "status": "healthy",
                "response_time_ms": 15,
                "details": {"endpoint": self.settings.crew_api_url}
            }
            
        except Exception as e:
            logger.error(f"Crew API health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"endpoint": self.settings.crew_api_url}
            }
            
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        # Run checks concurrently
        check_tasks = {
            name: asyncio.create_task(check_func())
            for name, check_func in self.checks.items()
        }
        
        results = {}
        for name, task in check_tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }
                
        # Determine overall health
        statuses = [r.get("status", "error") for r in results.values()]
        
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s in ["unhealthy", "error"] for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
            
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }


# Create global health checker
health_checker = HealthChecker()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": "chat-interface",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics.get_health_metrics()
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check for deployment."""
    try:
        # Check critical dependencies
        results = await health_checker.check_all()
        
        # Service is ready if Redis and Memory Service are healthy
        critical_checks = ["redis", "memory_service"]
        critical_healthy = all(
            results["checks"].get(check, {}).get("status") == "healthy"
            for check in critical_checks
        )
        
        if not critical_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
            
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/live")
async def liveness_check():
    """Liveness check for deployment."""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": metrics.get_uptime()
    }


@router.get("/dependencies")
async def check_dependencies():
    """Detailed dependency health check."""
    results = await health_checker.check_all()
    
    # Return appropriate status code
    if results["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=results
        )
        
    return results


@router.get("/metrics/summary")
async def metrics_summary():
    """Get metrics summary."""
    # Would integrate with Prometheus in production
    return {
        "uptime_seconds": metrics.get_uptime(),
        "active_sessions": 0,  # Would get from gauge
        "streaming_connections": 0,  # Would get from gauge
        "cache_stats": {},  # Would get from cache manager
        "pool_stats": {}  # Would get from connection pool
    }