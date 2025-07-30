"""
Connection pooling for service integrations.
"""

import logging
from typing import Dict, Optional
from contextlib import asynccontextmanager

import httpx
from httpx import Limits, Timeout

from src.chat.config import get_settings

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Manages connection pools for external services."""
    
    def __init__(self):
        """Initialize connection pool manager."""
        self.settings = get_settings()
        self._clients: Dict[str, httpx.AsyncClient] = {}
        
        # Connection pool settings
        self.pool_limits = Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
        
        # Timeout settings
        self.timeout = Timeout(
            connect=5.0,
            read=30.0,
            write=10.0,
            pool=5.0
        )
        
    async def get_client(self, service_name: str, base_url: str) -> httpx.AsyncClient:
        """
        Get or create HTTP client for a service.
        
        Args:
            service_name: Name of the service
            base_url: Base URL for the service
            
        Returns:
            HTTP client with connection pooling
        """
        if service_name not in self._clients:
            logger.info(f"Creating connection pool for {service_name}")
            
            self._clients[service_name] = httpx.AsyncClient(
                base_url=base_url,
                limits=self.pool_limits,
                timeout=self.timeout,
                http2=True,  # Enable HTTP/2 for better performance
                headers={
                    "User-Agent": "ChatInterface/1.0",
                    "Keep-Alive": "timeout=30, max=100"
                }
            )
            
        return self._clients[service_name]
        
    @asynccontextmanager
    async def get_memory_client(self):
        """Get Memory Service client with connection pooling."""
        client = await self.get_client(
            "memory_service",
            self.settings.memory_service_url
        )
        try:
            yield client
        finally:
            # Client remains open for reuse
            pass
            
    @asynccontextmanager
    async def get_thinking_client(self):
        """Get Thinking Service client with connection pooling."""
        client = await self.get_client(
            "thinking_service",
            self.settings.thinking_service_url
        )
        try:
            yield client
        finally:
            pass
            
    @asynccontextmanager
    async def get_crew_client(self):
        """Get Crew API client with connection pooling."""
        client = await self.get_client(
            "crew_api",
            self.settings.crew_api_url
        )
        try:
            yield client
        finally:
            pass
            
    async def close_all(self):
        """Close all connection pools."""
        for service_name, client in self._clients.items():
            logger.info(f"Closing connection pool for {service_name}")
            await client.aclose()
            
        self._clients.clear()
        
    def get_pool_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get connection pool statistics.
        
        Returns:
            Statistics for each service pool
        """
        stats = {}
        
        for service_name, client in self._clients.items():
            # Note: httpx doesn't expose detailed pool stats
            # In production, we'd use a custom transport for monitoring
            stats[service_name] = {
                "active": 1 if not client.is_closed else 0,
                "max_connections": self.pool_limits.max_connections,
                "max_keepalive": self.pool_limits.max_keepalive_connections
            }
            
        return stats
