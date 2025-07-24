"""
Model Context Protocol (MCP) Service
Integrates with our Railway-hosted MCP servers for extensible tool ecosystem
"""
import os
import logging
from typing import Dict, Any, List, Optional
import asyncio
import json
import httpx

from crewai_tools import MCPServerAdapter

from config import (
    MCP_REGISTRY_URL,
    MCP_SERVERS_CONFIG_PATH,
    ENVIRONMENT,
    MCP_REGISTRY_ENABLED,
    API_SECRET_KEY
)

"""
Model Context Protocol (MCP) Service
Integrates with our Railway-hosted MCP servers for extensible tool ecosystem
"""
import os
import logging
from typing import Dict, Any, List, Optional
import asyncio
import json
import httpx

from crewai_tools import MCPServerAdapter

from config import (
    MCP_REGISTRY_URL,
    MCP_SERVERS_CONFIG_PATH,
    ENVIRONMENT,
    MCP_REGISTRY_ENABLED,
    API_SECRET_KEY
)

logger = logging.getLogger(__name__)

class MCPService:
    """Service for managing MCP tool integration with CrewAI."""
    
    def __init__(self):
        """Initialize MCP service."""
        self.registry_url = MCP_REGISTRY_URL
        self.registry_enabled = MCP_REGISTRY_ENABLED
        self.servers_config_path = MCP_SERVERS_CONFIG_PATH
        self.available_adapters: List[MCPServerAdapter] = []
        self.available_tools: List[Any] = []
        self.api_token = self._generate_api_token()
        self._load_mcp_configuration()
    
    def _load_mcp_configuration(self) -> None:
        """Load MCP server configuration."""
        try:
            if self.servers_config_path and os.path.exists(self.servers_config_path):
                with open(self.servers_config_path, 'r') as f:
                    self.mcp_config = json.load(f)
                logger.info(f"Loaded MCP configuration from {self.servers_config_path}")
            else:
                # Default MCP configuration for Railway servers
                self.mcp_config = {
                    "servers": [
                        {
                            "name": "filesystem",
                            "url": "https://mcp-filesystem-production.up.railway.app/sse",
                            "description": "File system operations"
                        },
                        {
                            "name": "postgres",
                            "url": "https://mcp-postgres-production.up.railway.app/sse", 
                            "description": "PostgreSQL database operations"
                        },
                        {
                            "name": "brave-search",
                            "url": "https://mcp-brave-search-production.up.railway.app/sse",
                            "description": "Web search capabilities"
                        }
                    ],
                    "default_tools": []
                }
                logger.info("Using default MCP configuration for Railway servers")
                
        except Exception as e:
            logger.error(f"Failed to load MCP configuration: {str(e)}")
            self.mcp_config = {"servers": [], "default_tools": []}
    
    def _generate_api_token(self) -> str:
        """Generate a JWT token for API authentication."""
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            "sub": "mcp-service",
            "scopes": ["sparkjar_internal"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, API_SECRET_KEY, algorithm="HS256")
    
    async def discover_services_from_registry(self, service_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover available MCP services from registry."""
        if not self.registry_enabled or not self.registry_url:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.api_token}"}
                params = {}
                if service_type:
                    params["service_type"] = service_type
                    
                response = await client.get(
                    f"{self.registry_url}/mcp/registry/services",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                services = data.get("services", [])
                logger.info(f"Discovered {len(services)} services from MCP registry")
                return services
                
        except Exception as e:
            logger.error(f"Failed to discover services from registry: {str(e)}")
            return []
    
    async def discover_tools_from_registry(self) -> List[Dict[str, Any]]:
        """Discover available tools from our Railway MCP registry."""
        if not self.registry_enabled or not self.registry_url:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.api_token}"}
                response = await client.get(
                    f"{self.registry_url}/mcp/registry/tools",
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                tools = data.get("tools", [])
                logger.info(f"Discovered {len(tools)} tools from MCP registry")
                return tools
                
        except Exception as e:
            logger.error(f"Failed to discover tools from registry: {str(e)}")
            return []
    
    def connect_to_mcp_server(self, server_config: Dict[str, Any]) -> Optional[MCPServerAdapter]:
        """Connect to a specific MCP server and create adapter."""
        try:
            server_url = server_config.get("url")
            server_name = server_config.get("name", "unknown")
            
            if not server_url:
                logger.warning(f"No URL provided for MCP server: {server_name}")
                return None
            
            # Create MCP server adapter for SSE connection
            adapter = MCPServerAdapter({
                "url": server_url,
                "name": server_name,
                "description": server_config.get("description", f"MCP server: {server_name}")
            })
            
            logger.info(f"Created MCP adapter for server: {server_name}")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_config}: {str(e)}")
            return None
    
    async def load_all_mcp_tools(self) -> List[Any]:
        """Load all available MCP tools from configured servers or registry."""
        tools = []
        adapters = []
        
        try:
            # If registry is enabled, discover services dynamically
            if self.registry_enabled:
                services = await self.discover_services_from_registry()
                
                # Convert registry services to server configs
                for service in services:
                    server_config = {
                        "name": service.get("service_name"),
                        "url": service.get("base_url"),
                        "description": f"{service.get('service_type')} - {service.get('service_name')}"
                    }
                    
                    adapter = self.connect_to_mcp_server(server_config)
                    if adapter:
                        try:
                            # Start the MCP server and get tools
                            with adapter as server_tools:
                                tools.extend(server_tools)
                                adapters.append(adapter)
                                logger.info(f"Loaded {len(server_tools)} tools from {server_config['name']}")
                        except Exception as e:
                            logger.error(f"Failed to start MCP server {server_config['name']}: {str(e)}")
            else:
                # Load tools from static configuration
                for server_config in self.mcp_config.get("servers", []):
                    adapter = self.connect_to_mcp_server(server_config)
                    if adapter:
                        try:
                            # Start the MCP server and get tools
                            with adapter as server_tools:
                                tools.extend(server_tools)
                                adapters.append(adapter)
                                logger.info(f"Loaded {len(server_tools)} tools from {server_config['name']}")
                        except Exception as e:
                            logger.error(f"Failed to start MCP server {server_config['name']}: {str(e)}")
            
            self.available_adapters = adapters
            self.available_tools = tools
            logger.info(f"Loaded {len(tools)} MCP tools total from {len(adapters)} servers")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {str(e)}")
            return []
    
    def get_available_tools(self) -> List[Any]:
        """Get currently available MCP tools (synchronous for compatibility)."""
        return self.available_tools
    
    async def refresh_tools(self) -> None:
        """Refresh the list of available MCP tools."""
        logger.info("Refreshing MCP tools...")
        await self.load_all_mcp_tools()
    
    def get_tool_by_name(self, name: str) -> Optional[Any]:
        """Get a specific MCP tool by name."""
        for tool in self.available_tools:
            if hasattr(tool, 'name') and tool.name == name:
                return tool
        return None
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a specific MCP tool."""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            raise ValueError(f"MCP tool '{tool_name}' not found")
        
        try:
            # Use the tool's run method (may be async or sync)
            if hasattr(tool, 'arun'):
                result = await tool.arun(**kwargs)
            elif hasattr(tool, 'run'):
                result = tool.run(**kwargs)
            else:
                result = tool(**kwargs)
                
            logger.info(f"Executed MCP tool: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute MCP tool {tool_name}: {str(e)}")
            raise

# Global instance
mcp_service = MCPService()
