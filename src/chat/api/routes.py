"""
API routes for Chat Interface Service
"""

from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Dict, Any
import logging
from uuid import UUID

from src.chat.config import get_settings
from src.chat.models.chat_models import ChatRequest, ChatResponse
from .auth import TokenData, verify_chat_access
from .chat_controller import ChatController

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize chat controller
chat_controller = ChatController()


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get service status"""
    settings = get_settings()
    
    return {
        "service": "chat-interface",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.environment,
        "configuration": {
            "max_concurrent_conversations": settings.max_concurrent_conversations,
            "session_ttl_hours": settings.session_ttl_hours,
            "memory_service_url": settings.memory_service_url,
            "thinking_service_url": settings.thinking_service_url,
            "crew_api_url": settings.crew_api_url
        }
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with dependency status"""
    settings = get_settings()
    
    # TODO: Add actual dependency health checks in future tasks
    health_status = {
        "service": "healthy",
        "dependencies": {
            "memory_service": "unknown",  # Will be implemented in task 3
            "thinking_service": "unknown",  # Will be implemented in task 6
            "crew_api": "unknown",  # Will be implemented in task 13
            "redis": "unknown",  # Will be implemented in task 4
            "database": "unknown"  # Will be implemented in task 4
        },
        "configuration": {
            "port": settings.port,
            "environment": settings.environment,
            "debug": settings.debug
        }
    }
    
    return health_status


# Chat endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    token_data: TokenData = Depends(verify_chat_access)
) -> ChatResponse:
    """
    Process a chat message and return a response.
    
    This endpoint:
    - Validates the request against the authenticated token
    - Resolves SYNTH context and memory hierarchy
    - Generates a response using memory context
    - Optionally uses sequential thinking if enabled
    
    Args:
        request: Chat request with message and configuration
        token_data: Authenticated user/actor information
        
    Returns:
        Chat response with generated content and metadata
    """
    return await chat_controller.process_chat(request, token_data)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    token_data: TokenData = Depends(verify_chat_access)
):
    """
    Process a chat message with streaming response.
    
    Returns Server-Sent Events (SSE) stream with response chunks.
    
    Args:
        request: Chat request (stream_response will be ignored)
        token_data: Authenticated user/actor information
        
    Returns:
        StreamingResponse with SSE formatted chunks
    """
    return await chat_controller.process_chat_stream(request, token_data)


# Session management endpoints
@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    token_data: TokenData = Depends(verify_chat_access)
) -> Dict[str, Any]:
    """
    Get information about a chat session.
    
    Args:
        session_id: Session identifier
        token_data: Authenticated user information
        
    Returns:
        Session context information
    """
    return await chat_controller.get_session_context(session_id, token_data)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    token_data: TokenData = Depends(verify_chat_access)
) -> Dict[str, Any]:
    """
    Delete a chat session.
    
    Args:
        session_id: Session to delete
        token_data: Authenticated user information
        
    Returns:
        Deletion status
    """
    return await chat_controller.delete_session(session_id, token_data)
