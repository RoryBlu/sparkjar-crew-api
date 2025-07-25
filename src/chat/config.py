"""
Configuration settings for Chat Interface Service
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    port: int = Field(default=8002, description="Service port")
    host: str = Field(default="0.0.0.0", description="Service host")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment")
    
    # Database configuration
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/sparkjar_crew",
        description="Database connection URL"
    )
    
    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # External service URLs
    memory_service_url: str = Field(
        default="http://localhost:8003",
        description="Memory service URL"
    )
    memory_internal_api_url: str = Field(
        default=os.getenv("MEMORY_INTERNAL_API_URL", "http://localhost:8001"),
        description="Memory internal API URL"
    )
    thinking_service_url: str = Field(
        default="http://localhost:8004",
        description="Sequential thinking service URL"
    )
    crew_api_url: str = Field(
        default="http://localhost:8000",
        description="Crew API service URL"
    )
    mcp_registry_url: str = Field(
        default=os.getenv("MCP_REGISTRY_URL", "http://localhost:8000"),
        description="MCP Registry URL"
    )
    
    # JWT configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key"
    )
    api_secret_key: str = Field(
        default=os.getenv("API_SECRET_KEY", "development-secret-key"),
        description="API secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")
    
    # Internal auth token for crew API
    internal_auth_token: str = Field(
        default="",
        description="Internal auth token for crew API calls"
    )
    
    # Session configuration
    session_ttl_hours: int = Field(default=24, description="Session TTL in hours")
    max_conversation_history: int = Field(default=100, description="Max conversation history length")
    
    # Performance settings
    max_concurrent_conversations: int = Field(default=10000, description="Max concurrent conversations")
    memory_cache_ttl_minutes: int = Field(default=15, description="Memory cache TTL in minutes")
    synth_context_cache_ttl_minutes: int = Field(default=60, description="SYNTH context cache TTL in minutes")
    
    # Chat with Memory v1 specific settings
    chat_session_ttl_hours: int = Field(
        default=int(os.getenv("CHAT_SESSION_TTL_HOURS", "24")),
        description="Chat session TTL in hours"
    )
    chat_rate_limit_per_minute: int = Field(
        default=int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "20")),
        description="Chat rate limit per minute"
    )
    chat_rate_limit_per_hour: int = Field(
        default=int(os.getenv("CHAT_RATE_LIMIT_PER_HOUR", "200")),
        description="Chat rate limit per hour"
    )
    chat_max_message_length: int = Field(
        default=int(os.getenv("CHAT_MAX_MESSAGE_LENGTH", "10240")),
        description="Maximum message length"
    )
    memory_search_timeout_seconds: int = Field(
        default=int(os.getenv("MEMORY_SEARCH_TIMEOUT_SECONDS", "5")),
        description="Memory search timeout"
    )
    stream_chunk_size: int = Field(
        default=int(os.getenv("STREAM_CHUNK_SIZE", "50")),
        description="Stream chunk size"
    )
    stream_chunk_delay_ms: int = Field(
        default=int(os.getenv("STREAM_CHUNK_DELAY_MS", "30")),
        description="Stream chunk delay in milliseconds"
    )
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(
        default=os.getenv("OPENAI_API_KEY"),
        description="OpenAI API key"
    )
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(
        default=os.getenv("SENTRY_DSN"),
        description="Sentry DSN for error tracking"
    )
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()