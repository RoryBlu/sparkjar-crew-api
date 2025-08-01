"""
FastAPI server for SparkJAR COS API.
Implements the endpoints specified in API.md with proper authentication and job queuing.
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid
import logging
import asyncio
from datetime import datetime

from config import API_HOST, API_PORT, ENVIRONMENT
from sparkjar_shared.utils.chroma_client import test_chroma_connection
from api.models import (
    CrewJobRequest, CrewJobResponse, HealthResponse, 
    SchemaValidationResponse, ValidationErrorResponse,
    CrewMessageRequest, CrewMessageResponse, JobStatus
)
from api.auth import verify_token
from services.job_service import JobService
from services.json_validator import validate_crew_request, SchemaValidationError
from database.connection import get_direct_session
from database.models import ClientSecrets, Clients
from sqlalchemy import select

# Import chat components
from ..chat.api.chat_controller import ChatController
from ..chat.api.auth_enhanced import verify_chat_access_enhanced
from ..chat.api.health import router as health_router
from ..chat.models.chat_models import ChatRequest, ChatResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SparkJAR COS API",
    description="CrewAI Orchestration System API for asynchronous crew execution",
    version="1.0.0",
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if ENVIRONMENT == "development" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
job_service = JobService()
chat_controller = ChatController()

# Registry has been moved to a separate service

# Include health router for enhanced monitoring
app.include_router(health_router, tags=["health"])

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Returns service status and environment configuration flags.
    """
    return HealthResponse(
        status="healthy",
        service="crew_job_api_with_chat",
        environment=ENVIRONMENT,
        timestamp=datetime.utcnow()
    )

@app.get("/test_chroma")
async def test_chroma():
    """
    Checks ChromaDB connectivity and lists collections.
    Useful for verifying deployment.
    """
    try:
        result = test_chroma_connection()
        if result["status"] == "success":
            return {
                "status": "success",
                "collections": result["collections"],
                "chroma_url": result["chroma_url"],
                "total_collections": result["total_collections"]
            }
        else:
            raise HTTPException(
                status_code=503,
                detail=f"ChromaDB connection failed: {result['error']}"
            )
    except Exception as e:
        logger.error(f"ChromaDB test failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"ChromaDB test failed: {str(e)}"
        )

@app.post("/crew_job", response_model=CrewJobResponse)
async def create_crew_job(
    job_request: CrewJobRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Queue a crew for asynchronous execution.
    
    Requires bearer token with 'sparkjar_internal' scope.
    """
    # Verify authentication
    try:
        token_data = verify_token(credentials.credentials)
        if "sparkjar_internal" not in token_data.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions. Requires 'sparkjar_internal' scope."
            )
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    try:
        # Validate the request data against database schemas
        validation_result = await validate_crew_request(job_request.data)
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Schema validation failed",
                    "detail": "Request data does not match required schema",
                    "validation_errors": validation_result['errors'],
                    "schema_used": validation_result.get("schema_used"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Use the validated data
        validated_data = validation_result['validated_data']
        
        # Create job using the validated data
        job_id = await job_service.create_job_from_validated_data(validated_data)
        
        # Queue job for background execution
        background_tasks.add_task(job_service.execute_job, job_id)
        
        client_user_id = validated_data.get('client_user_id', 'unknown')
        logger.info(f"Created and queued job {job_id} for user {client_user_id}")
        
        return CrewJobResponse(
            job_id=job_id,
            status="queued"
        )
        
    except SchemaValidationError as e:
        logger.error(f"Schema validation failed: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Schema validation failed",
                "detail": str(e),
                "validation_errors": e.errors if hasattr(e, 'errors') else [],
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except ValueError as e:
        logger.error(f"Invalid job request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/crew_job/{job_id}")
async def get_job_status(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get job status and results.
    """
    # Verify authentication
    try:
        token_data = verify_token(credentials.credentials)
        if "sparkjar_internal" not in token_data.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions. Requires 'sparkjar_internal' scope."
            )
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    try:
        job_status = await job_service.get_job_status(job_id)
        if job_status is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/validate_schema", response_model=SchemaValidationResponse)
async def validate_schema(
    request_data: Dict[str, Any]
):
    """
    Validate JSON data against object schemas stored in the database.
    
    This endpoint validates the incoming JSON against the appropriate schema
    from the object_schemas table based on the job_key field.
    
    Returns validation results including which schema was used.
    """
    try:
        # Validate the request data using the new async validator
        validation_result = await validate_crew_request(request_data)
        
        if validation_result['valid']:
            return SchemaValidationResponse(
                valid=True,
                schema_used=validation_result.get("schema_used"),
                schema_type="crew",  # All our schemas are crew type
                message="Validation successful"
            )
        else:
            # Return validation errors as HTTP 422
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Schema validation failed",
                    "detail": "Request data does not match required schema",
                    "validation_errors": validation_result['errors'],
                    "schema_used": validation_result.get("schema_used"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except SchemaValidationError as e:
        logger.error(f"Schema validation failed: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Schema validation failed",
                "detail": str(e),
                "validation_errors": e.errors if hasattr(e, 'errors') else [],
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected validation error: {str(e)}"
        )

@app.post("/vectorize_job/{job_id}")
async def vectorize_job_events(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Vectorize job events into PostgreSQL using pgvector.
    
    Takes a job ID and processes all events for that job, creating
    vector embeddings and storing them in the document_vectors table.
    """
    try:
        # Verify authentication
        token_data = verify_token(credentials.credentials)
        if "sparkjar_internal" not in token_data.get("scopes", []):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get job data
        job_service = JobService()
        job_status = await job_service.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if not job_status.events:
            raise HTTPException(status_code=400, detail=f"Job {job_id} has no events to vectorize")
        
        # Use vectorization service
        from services.vectorization_service import VectorizationService
        
        vectorization_service = VectorizationService()
        result = await vectorization_service.vectorize_job_events(job_id, job_status.events)
        
        return {
            "status": "success",
            "job_id": job_id,
            "storage": "PostgreSQL (document_vectors table)",
            "embedding_model": vectorization_service.embedding_model,
            "embedding_dimension": vectorization_service.embedding_dimension,
            **result,
            "message": f"Successfully vectorized {result['processed_events']} events into {result['total_chunks']} chunks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vectorization failed for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Vectorization failed: {str(e)}")

class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    source_table: Optional[str] = Field(None, description="Filter by source table")
    limit: int = Field(10, description="Maximum results to return", ge=1, le=100)
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="JSONB metadata filters")

@app.post("/search_vectors")
async def search_vectors(
    request: VectorSearchRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Search for similar documents using vector similarity.
    
    Returns documents ordered by similarity score.
    """
    try:
        # Verify authentication
        token_data = verify_token(credentials.credentials)
        if "sparkjar_internal" not in token_data.get("scopes", []):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Use vectorization service for search
        from services.vectorization_service import VectorizationService
        
        vectorization_service = VectorizationService()
        results = await vectorization_service.search_similar(
            query=request.query,
            source_table=request.source_table,
            limit=request.limit,
            metadata_filter=request.metadata_filters
        )
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/crew_message_api", response_model=CrewMessageResponse)
async def create_crew_message(
    message_request: CrewMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Process client-level messages using API key authentication.
    
    This endpoint:
    1. Validates the API key against client_secrets table
    2. Retrieves the associated client_id
    3. Creates a crew job using the contact_form schema
    4. Queues the job for asynchronous execution
    
    The request is validated against the contact_form schema in object_schemas.
    """
    try:
        # Look up the API key in client_secrets table
        async with get_direct_session() as session:
            # Query for SPARKJAR_API_KEY in client_secrets
            result = await session.execute(
                select(ClientSecrets).where(
                    ClientSecrets.secret_key == "SPARKJAR_API_KEY",
                    ClientSecrets.secret_value == message_request.api_key
                )
            )
            client_secret = result.scalar_one_or_none()
            
            if not client_secret:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key"
                )
            
            client_id = client_secret.client_id
            
            # Get client info for logging
            client_result = await session.execute(
                select(Clients).where(Clients.id == client_id)
            )
            client = client_result.scalar_one_or_none()
            client_name = client.display_name if client else "Unknown"
            
        logger.info(f"Processing message from client: {client_name} ({client_id})")
        
        # Build the crew job request data
        # The contact_form schema expects these fields at the top level
        crew_job_data = {
            "job_key": "contact_form",  # This triggers the contact_form crew
            "client_user_id": str(client_id),  # Use client_id as the user
            "actor_type": "client",  # Mark as client-level request
            "actor_id": str(client_id),  # Use client_id as actor
            "api_key": message_request.api_key,
            "inquiry_type": message_request.inquiry_type,
            "contact": message_request.contact,
            "message": message_request.message,
            "metadata": message_request.metadata
        }
        
        # Validate against the contact_form schema
        validation_result = await validate_crew_request(crew_job_data)
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Schema validation failed",
                    "detail": "Request data does not match contact_form schema",
                    "validation_errors": validation_result['errors'],
                    "schema_used": "contact_form",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Create the job
        job_id = await job_service.create_job_from_validated_data(crew_job_data)
        
        # Queue job for background execution
        background_tasks.add_task(job_service.execute_job, job_id)
        
        logger.info(f"Created contact form job {job_id} for client {client_name}")
        
        return CrewMessageResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message=f"Your message has been received and is being processed. Track progress with job ID: {job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process crew message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )

# Chat endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    token_data=Depends(verify_chat_access_enhanced)
):
    """
    Process a chat request with memory context and optional sequential thinking.
    """
    return await chat_controller.process_chat(request, token_data)

@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    token_data=Depends(verify_chat_access_enhanced)
):
    """
    Process a chat request with streaming response.
    """
    return await chat_controller.process_chat_stream(request, token_data)

@app.get("/chat/session/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    token_data=Depends(verify_chat_access_enhanced)
):
    """
    Get session context information.
    """
    return await chat_controller.get_session_context(session_id, token_data)

@app.delete("/chat/session/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    token_data=Depends(verify_chat_access_enhanced)
):
    """
    Delete a chat session.
    """
    return await chat_controller.delete_session(session_id, token_data)

# Admin endpoints for feature flag management
@app.get("/admin/feature-flags")
async def get_feature_flags(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get all feature flags and their current states
    
    Returns:
        Dictionary of all feature flags with their configurations
    """
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        
        # Check for admin scope
        scopes = payload.get("scopes", [])
        if "admin" not in scopes and "sparkjar_internal" not in scopes:
            raise HTTPException(
                status_code=403,
                detail="Admin access required to view feature flags"
            )
        
        from services.feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        
        return {
            "flags": feature_flags.get_all_flags(),
            "metrics": feature_flags.get_metrics()
        }
        
    except Exception as e:
        logger.error(f"Error getting feature flags: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/admin/feature-flags")
async def update_feature_flag(
    flag_name: str = Field(..., description="Name of the feature flag"),
    enabled: bool = Field(..., description="Whether to enable or disable the flag"),
    description: Optional[str] = Field(None, description="Optional description"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update a feature flag
    
    Args:
        flag_name: Name of the feature flag to update
        enabled: Whether to enable or disable the flag
        description: Optional description for the flag
        
    Returns:
        Updated flag configuration
    """
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        
        # Check for admin scope
        scopes = payload.get("scopes", [])
        if "admin" not in scopes and "sparkjar_internal" not in scopes:
            raise HTTPException(
                status_code=403,
                detail="Admin access required to update feature flags"
            )
        
        from services.feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        
        # Update the flag
        feature_flags.set_flag(flag_name, enabled, description)
        
        # Log the change
        logger.info(
            f"Feature flag '{flag_name}' updated to {enabled} by user {payload.get('sub')}",
            extra={
                "flag_name": flag_name,
                "enabled": enabled,
                "updated_by": payload.get("sub")
            }
        )
        
        # Return updated flag
        flag_config = feature_flags.get_flag(flag_name)
        return {
            "flag_name": flag_name,
            "enabled": flag_config.enabled,
            "description": flag_config.description,
            "updated_at": flag_config.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating feature flag: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/admin/feature-flags/reset-metrics")
async def reset_feature_flag_metrics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Reset feature flag usage metrics
    
    Returns:
        Success message
    """
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        
        # Check for admin scope
        scopes = payload.get("scopes", [])
        if "admin" not in scopes and "sparkjar_internal" not in scopes:
            raise HTTPException(
                status_code=403,
                detail="Admin access required to reset metrics"
            )
        
        from services.feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        
        # Reset metrics
        feature_flags.reset_metrics()
        
        logger.info(f"Feature flag metrics reset by user {payload.get('sub')}")
        
        return {"message": "Feature flag metrics reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        raise HTTPException(status_code=401, detail=str(e))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    await chat_controller.initialize()
    logger.info("Chat controller initialized")
    
    # Log feature flag status
    from services.feature_flags import get_feature_flags
    feature_flags = get_feature_flags()
    all_flags = feature_flags.get_all_flags()
    enabled_count = sum(1 for f in all_flags.values() if f["enabled"])
    logger.info(f"Feature flags initialized: {enabled_count}/{len(all_flags)} enabled")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await chat_controller.shutdown()
    logger.info("Chat controller shutdown complete")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found", "detail": "The requested resource was not found"}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=ENVIRONMENT == "development"
    )
