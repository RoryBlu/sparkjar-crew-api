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
    thinking_service_url: str = Field(
        default="http://localhost:8004",
        description="Sequential thinking service URL"
    )
    crew_api_url: str = Field(
        default="http://localhost:8000",
        description="Crew API service URL"
    )
    
    # JWT configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key"
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