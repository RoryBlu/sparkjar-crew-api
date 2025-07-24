"""Proxy MCP registry service for tests.

This module provides access to the MCP registry service using proper package imports.
"""

try:
    # Import from the installed package
    from sparkjar_crew.services.mcp_registry.services.registry_service import MCPRegistryService
except ImportError as e:
    # Create a stub class if the service is not available
    class MCPRegistryService:
        """Stub MCP Registry Service for when the actual service is not available."""
        
        def __init__(self, *args, **kwargs):
            raise ImportError(f"MCP Registry Service not available: {e}")

__all__ = ["MCPRegistryService"]
