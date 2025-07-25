"""
Chat with Memory v1 API Endpoints.

KISS: Simple endpoint structure with /v1/ versioning.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from uuid import UUID
from pydantic import BaseModel

from src.chat.models import ChatRequestV1, ChatResponseV1, ChatSessionV1
from src.chat.processors.chat_processor_v1 import ChatProcessorV1
from src.chat.streaming.stream_generator_v1 import StreamGeneratorV1
from src.api.auth import verify_token, get_current_user

logger = logging.getLogger(__name__)

# Dependency injection placeholder
# In production, these would be properly injected
_chat_processor: ChatProcessorV1 = None


def get_chat_processor() -> ChatProcessorV1:
    """Get chat processor instance."""
    if _chat_processor is None:
        raise RuntimeError("Chat processor not initialized")
    return _chat_processor


# Create versioned router
router = APIRouter(
    prefix="/v1/chat",
    tags=["chat-v1"]
)


class ModeSwitchRequest(BaseModel):
    """Request to switch chat mode."""
    mode: str  # "tutor" or "agent"


@router.post("/completions", response_model=ChatResponseV1)
async def create_chat_completion(
    request: ChatRequestV1,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> ChatResponseV1:
    """
    Create a chat completion with memory context.
    
    This endpoint handles both tutor and agent modes based on the
    session's current mode or the mode specified in the request.
    """
    try:
        # Extract client_id from token
        client_id = UUID(current_user["client_id"])
        
        # Process the chat request
        response = await processor.process_chat_request(request, client_id)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/completions/stream")
async def create_chat_completion_stream(
    request: ChatRequestV1,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
):
    """
    Create a streaming chat completion with memory context.
    
    Returns Server-Sent Events (SSE) stream with:
    - metadata: Initial response metadata
    - typing: Typing indicators
    - search_status: Memory search progress
    - chunk: Response text chunks
    - complete: Completion with follow-ups
    - error: Any errors during streaming
    """
    try:
        # Extract client_id from token
        client_id = UUID(current_user["client_id"])
        
        # Create stream generator
        stream_gen = StreamGeneratorV1()
        
        async def generate():
            try:
                # Show search progress
                search_phases = [
                    {"name": "Searching memories", "status": "started"},
                    {"name": "Analyzing context", "status": "in_progress"},
                    {"name": "Generating response", "status": "in_progress"}
                ]
                
                async for event in stream_gen.generate_search_status_stream(search_phases):
                    yield event
                
                # Process the chat request
                response = await processor.process_chat_request(request, client_id)
                
                # Stream the response
                async for event in stream_gen.generate_stream(response):
                    yield event
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> Dict[str, Any]:
    """Get session details."""
    try:
        session_uuid = UUID(session_id)
        client_id = UUID(current_user["client_id"])
        
        # Get session
        session = await processor.session_manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # Verify ownership
        if session.client_user_id != client_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        return session.dict()
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> Dict[str, Any]:
    """Delete a session."""
    try:
        session_uuid = UUID(session_id)
        client_id = UUID(current_user["client_id"])
        
        # Verify ownership before deletion
        session = await processor.session_manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session.client_user_id != client_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        # Delete session
        deleted = await processor.session_manager.delete_session(session_uuid)
        
        return {"deleted": deleted, "session_id": session_id}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/mode")
async def switch_mode(
    session_id: str,
    mode_request: ModeSwitchRequest,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> Dict[str, Any]:
    """Switch between tutor and agent modes."""
    try:
        # Validate mode
        if mode_request.mode not in ["tutor", "agent"]:
            raise HTTPException(
                status_code=400, 
                detail="Mode must be 'tutor' or 'agent'"
            )
            
        session_uuid = UUID(session_id)
        client_id = UUID(current_user["client_id"])
        
        # Switch mode
        updated_session = await processor.switch_mode(
            session_uuid,
            mode_request.mode,
            client_id
        )
        
        return {
            "session_id": str(updated_session.session_id),
            "previous_mode": updated_session.mode,
            "new_mode": mode_request.mode,
            "message": f"Switched to {mode_request.mode} mode"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/progress")
async def get_learning_progress(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> Dict[str, Any]:
    """Get learning progress for tutor mode sessions."""
    try:
        session_uuid = UUID(session_id)
        client_id = UUID(current_user["client_id"])
        
        progress = await processor.get_learning_progress(
            session_uuid,
            client_id
        )
        
        return progress
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/learning-path")
async def get_learning_path(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> Dict[str, Any]:
    """Get detailed learning path for a session."""
    try:
        session_uuid = UUID(session_id)
        client_id = UUID(current_user["client_id"])
        
        # Verify ownership
        session = await processor.session_manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.client_user_id != client_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        # Get learning path
        from src.chat.services.learning_path_v1 import LearningPathManager
        path_manager = LearningPathManager(processor.session_manager)
        path = await path_manager.get_learning_path(session_uuid)
        
        if not path:
            raise HTTPException(
                status_code=400, 
                detail="Session is not in tutor mode"
            )
            
        return path
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/learning-report")
async def export_learning_report(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    processor: ChatProcessorV1 = Depends(get_chat_processor)
) -> Dict[str, Any]:
    """Export comprehensive learning report."""
    try:
        session_uuid = UUID(session_id)
        client_id = UUID(current_user["client_id"])
        
        # Verify ownership
        session = await processor.session_manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.client_user_id != client_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        # Generate report
        from src.chat.services.learning_path_v1 import LearningPathManager
        path_manager = LearningPathManager(processor.session_manager)
        report = await path_manager.export_learning_report(session_uuid)
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))