"""Crew API configuration.
Extends the shared configuration settings with service-specific validation."""

from shared.config.shared_settings import *  # noqa: F401,F403
from shared.config.config_validator import validate_config_on_startup
import logging
import os

# Additional settings for chat interface
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8003")
THINKING_SERVICE_URL = os.getenv("THINKING_SERVICE_URL", "http://localhost:8004")
CREW_API_URL = os.getenv("CREW_API_URL", "http://localhost:8000")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", API_SECRET_KEY)  # Use same secret
INTERNAL_AUTH_TOKEN = os.getenv("INTERNAL_AUTH_TOKEN", "")

# Service-specific configuration validation
def validate_crew_api_config() -> bool:
    """Validate crew-api specific configuration requirements."""
    logger = logging.getLogger(__name__)
    
    try:
        # Run base configuration validation
        result = validate_config_on_startup(fail_fast=False)
        
        # Check crew-api specific requirements
        crew_api_errors = []
        
        # Validate required APIs for crew functionality
        if not OPENAI_API_KEY:
            crew_api_errors.append("OPENAI_API_KEY is required for CrewAI functionality")
        
        # Validate database connections for crew operations
        if not DATABASE_URL_DIRECT:
            crew_api_errors.append("DATABASE_URL_DIRECT is required for crew database operations")
        
        # Validate ChromaDB for memory functionality
        if not CHROMA_URL:
            crew_api_errors.append("CHROMA_URL is required for crew memory operations")
        
        # Validate chat interface requirements
        if not REDIS_URL:
            crew_api_errors.append("REDIS_URL is required for chat session management")
            
        if not MEMORY_SERVICE_URL:
            crew_api_errors.append("MEMORY_SERVICE_URL is required for chat memory integration")
        
        # Check optional but recommended configurations
        crew_api_warnings = []
        if not os.getenv("GOOGLE_API_KEY") and not os.getenv("SERPER_API_KEY"):
            crew_api_warnings.append("No search API keys configured (GOOGLE_API_KEY or SERPER_API_KEY)")
        
        if not os.getenv("NVIDIA_NIM_API_KEY"):
            crew_api_warnings.append("NVIDIA_NIM_API_KEY not configured - OCR functionality will be limited")
            
        if not THINKING_SERVICE_URL:
            crew_api_warnings.append("THINKING_SERVICE_URL not configured - sequential thinking will be unavailable")
        
        # Log results
        if crew_api_errors:
            logger.error("❌ Crew API configuration validation failed:")
            for error in crew_api_errors:
                logger.error(f"  • {error}")
        
        if crew_api_warnings:
            logger.warning("⚠️  Crew API configuration warnings:")
            for warning in crew_api_warnings:
                logger.warning(f"  • {warning}")
        
        # Overall validation status
        is_valid = result.is_valid and len(crew_api_errors) == 0
        
        if is_valid:
            logger.info("✅ Crew API configuration validation passed")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ Crew API configuration validation error: {str(e)}")
        return False

# Run crew-api specific validation on import
if not os.getenv("SKIP_CONFIG_VALIDATION", "").lower() == "true":
    validate_crew_api_config()
