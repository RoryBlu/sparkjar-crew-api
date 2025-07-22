"""Proxy module exposing MCP registry Pydantic models.

This provides access to MCP registry models using proper package imports.
"""

try:
    # Import from the installed package
    from sparkjar_crew.services.mcp_registry.models.registry_models import (
        AuthenticationType,
        HealthStatus,
        ServiceFilters,
        ServiceProtocol,
        ServiceRegistration,
        ServiceStatus,
        ServiceType,
        ToolFilters,
    )
except ImportError:
    # Create stub classes if the models are not available
    from enum import Enum
    from pydantic import BaseModel
    
    class AuthenticationType(str, Enum):
        NONE = "none"
        BASIC = "basic"
        BEARER = "bearer"
    
    class HealthStatus(str, Enum):
        HEALTHY = "healthy"
        UNHEALTHY = "unhealthy"
        UNKNOWN = "unknown"
    
    class ServiceProtocol(str, Enum):
        HTTP = "http"
        HTTPS = "https"
    
    class ServiceStatus(str, Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"
        MAINTENANCE = "maintenance"
    
    class ServiceType(str, Enum):
        MCP = "mcp"
        API = "api"
    
    class ServiceFilters(BaseModel):
        pass
    
    class ServiceRegistration(BaseModel):
        pass
    
    class ToolFilters(BaseModel):
        pass

__all__ = [
    "AuthenticationType",
    "HealthStatus",
    "ServiceFilters",
    "ServiceProtocol",
    "ServiceRegistration",
    "ServiceStatus",
    "ServiceType",
    "ToolFilters",
]
