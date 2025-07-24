"""
Application startup script.
Initializes database, checks connections, and starts the FastAPI server.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root and src directory to Python path
project_root = Path(__file__).parent.parent.parent
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

# Use absolute imports from src
from database.connection import create_tables, check_database_connection
from utils.chroma_client import test_chroma_connection
from config import ENVIRONMENT, API_HOST, API_PORT, OPTIONAL_CONFIG

# Import centralized configuration validation
from shared.config.startup_validator import validate_service_startup, CommonChecks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def startup_checks():
    """Perform startup checks and initialization."""
    logger.info("Starting SparkJAR COS...")
    logger.info(f"Environment: {ENVIRONMENT}")
    
    # Run centralized configuration validation
    logger.info("Validating configuration...")
    crew_api_checks = {
        "database_connection": CommonChecks.database_connection_check,
        "openai_api_key": CommonChecks.openai_api_key_check,
        "secret_key": CommonChecks.secret_key_check,
        "api_port": lambda: CommonChecks.port_availability_check("API_PORT", 8000),
        "chroma_connection": CommonChecks.chroma_connection_check,
    }
    
    config_valid = validate_service_startup(
        service_name="crew-api",
        additional_checks=crew_api_checks,
        exit_on_failure=False,  # We want to handle failure gracefully
        logger=logger
    )
    
    if not config_valid:
        logger.error("Configuration validation failed")
        return False
    
    # Check ChromaDB connection
    logger.info("Testing ChromaDB connection...")
    try:
        chroma_status = test_chroma_connection()
        if chroma_status["status"] == "success":
            logger.info(f"ChromaDB connected: {chroma_status['total_collections']} collections available")
        else:
            # Make ChromaDB non-fatal - just warn
            logger.warning(f"ChromaDB connection issue: {chroma_status.get('error', 'Unknown error')}")
            logger.warning("Continuing without ChromaDB - memory features may be limited")
    except Exception as e:
        # Don't fail startup for ChromaDB issues
        logger.warning(f"ChromaDB check failed: {e}")
        logger.warning("Continuing without ChromaDB - memory features may be limited")
    
    # Check database connection
    logger.info("Testing database connection...")
    db_connected = await check_database_connection()
    if not db_connected:
        logger.error("Database connection failed")
        return False
    
    # Create database tables
    logger.info("Creating database tables...")
    try:
        await create_tables()
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False
    
    logger.info("Startup checks completed successfully")
    return True

def start_server():
    """Start the FastAPI server."""
    try:
        import uvicorn
        
        logger.info(f"Starting server on {API_HOST}:{API_PORT}")
        
        uvicorn.run(
            "api.main:app",
            host=API_HOST,
            port=API_PORT,
            reload=ENVIRONMENT == "development",
            log_level="info" if ENVIRONMENT == "development" else "warning"
        )
        
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

async def main():
    """Main startup function."""
    try:
        # Run startup checks
        success = await startup_checks()
        if not success:
            logger.error("Startup checks failed")
            sys.exit(1)
        
        # Start the server
        start_server()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
