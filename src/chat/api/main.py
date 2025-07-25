"""
Main FastAPI application for Chat with Memory v1.

KISS: Simple app setup with clear middleware and routes.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.chat.api.chat_endpoints_v1 import router as chat_router
from src.chat.config import get_settings
from src.chat.middleware.rate_limiter_v1 import RateLimitMiddleware, RateLimiter
from src.chat.monitoring.health_check_v1 import HealthChecker, metrics_collector
from src.chat.processors.chat_processor_v1 import ChatProcessorV1
from src.chat.services.memory_search_v1 import HierarchicalMemorySearcher
from src.chat.services.session_manager_v1 import RedisSessionManager
from src.chat.services.conversation_store_v1 import ConversationMemoryStore
from src.chat.clients.memory_service import MemoryServiceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
chat_processor = None
health_checker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    
    KISS: Setup on startup, cleanup on shutdown.
    """
    global chat_processor, health_checker
    
    logger.info("Starting Chat with Memory v1...")
    
    # Load settings
    settings = get_settings()
    
    # Initialize services
    try:
        # Memory service client
        memory_client = MemoryServiceClient(
            base_url=settings.memory_internal_api_url,
            api_key=settings.api_secret_key
        )
        
        # Core services
        memory_searcher = HierarchicalMemorySearcher(memory_client)
        session_manager = RedisSessionManager(settings.redis_url)
        conversation_store = ConversationMemoryStore(memory_client)
        
        # TODO: Initialize real LLM client
        llm_client = None  # Placeholder
        
        # Chat processor
        chat_processor = ChatProcessorV1(
            memory_searcher,
            session_manager,
            conversation_store,
            llm_client
        )
        
        # Health checker
        health_checker = HealthChecker(
            redis_url=settings.redis_url,
            memory_service_url=settings.memory_internal_api_url,
            database_url=settings.database_url
        )
        
        # Set processor in endpoints
        from src.chat.api import chat_endpoints_v1
        chat_endpoints_v1._chat_processor = chat_processor
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
        
    yield
    
    # Cleanup
    logger.info("Shutting down Chat with Memory v1...")
    
    try:
        if chat_processor and chat_processor.session_manager:
            await chat_processor.session_manager.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Chat with Memory v1",
    description="Intelligent chat with hierarchical memory access",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
settings = get_settings()
rate_limiter = RateLimiter(
    redis_url=settings.redis_url,
    requests_per_minute=settings.chat_rate_limit_per_minute,
    requests_per_hour=settings.chat_rate_limit_per_hour
)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to headers."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    # Record metrics
    if request.url.path.startswith("/v1/chat"):
        endpoint = request.url.path
        mode = "unknown"  # Would extract from request
        metrics_collector.record_request(endpoint, mode, process_time)
    
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns service health status.
    """
    if not health_checker:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Service not initialized"}
        )
        
    health_status = await health_checker.check_health()
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_status)


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """
    Get application metrics.
    
    Returns current metrics summary.
    """
    return metrics_collector.get_metrics_summary()


# Include chat routes
app.include_router(chat_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Chat with Memory v1",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "chat_stream": "/v1/chat/completions/stream",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Resource not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal error: {exc}")
    metrics_collector.record_error("internal_server_error")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_id": str(time.time())  # For log correlation
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # Required for Railway
        port=8000,
        log_level="info"
    )