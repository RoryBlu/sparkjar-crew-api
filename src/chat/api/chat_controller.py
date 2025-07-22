"""
Chat Controller - Main API endpoints for chat functionality.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
import asyncio

from fastapi import Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
import httpx

from src.chatmodels.chat_models import ChatRequest, ChatResponse
from src.chatmodels.context_models import SynthContext
from src.chatservices.conversation_manager import ConversationManager
from src.chatservices.session_manager import SessionManager, SessionContextStore
from src.chatclients.memory_service import MemoryServiceClient
from src.chatclients.thinking_service import ThinkingServiceClient
from src.chatconfig import get_settings
from .auth_enhanced import TokenData, verify_chat_access_enhanced

logger = logging.getLogger(__name__)


class ChatController:
    """Handles chat-related API endpoints."""
    
    def __init__(self):
        """Initialize chat controller with dependencies."""
        self.settings = get_settings()
        
        # Initialize components
        self.session_store = SessionContextStore()
        self.session_manager = SessionManager(self.session_store)
        self.memory_client = MemoryServiceClient()
        self.thinking_client = ThinkingServiceClient()
        
        # Create conversation manager
        self.conversation_manager = ConversationManager(
            session_manager=self.session_manager,
            memory_client=self.memory_client,
            thinking_client=self.thinking_client
        )
        
        # HTTP client for crew API
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        self._initialized = False
        
    async def initialize(self):
        """Initialize controller dependencies."""
        if not self._initialized:
            try:
                # Connect to Redis
                await self.session_store.connect()
                logger.info("ChatController initialized successfully")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize ChatController: {e}")
                raise
                
    async def shutdown(self):
        """Cleanup controller resources."""
        try:
            await self.session_store.disconnect()
            await self.http_client.aclose()
            logger.info("ChatController shutdown complete")
        except Exception as e:
            logger.error(f"Error during ChatController shutdown: {e}")
            
    async def process_chat(
        self,
        request: ChatRequest,
        token_data: TokenData = Depends(verify_chat_access_enhanced)
    ) -> ChatResponse:
        """
        Process a chat request and return response.
        
        Args:
            request: Chat request from client
            token_data: Authenticated token data
            
        Returns:
            Chat response
            
        Raises:
            HTTPException: On processing errors
        """
        try:
            # Validate request matches token
            if request.client_user_id != token_data.client_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Client user ID mismatch"
                )
                
            if request.actor_id != token_data.actor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Actor ID mismatch"
                )
                
            # Resolve SYNTH context
            synth_context = await self._resolve_synth_context(
                actor_id=request.actor_id,
                client_id=request.client_user_id
            )
            
            if not synth_context:
                # Create minimal context for MVP
                synth_context = SynthContext(
                    synth_id=request.actor_id,
                    synth_class_id=0,  # Default class
                    client_id=request.client_user_id,
                    synth_class_config={},
                    company_customizations={},
                    client_policies={},
                    memory_access_scope=["fact", "skill", "procedure"]
                )
                
            # Process the chat request
            response = await self.conversation_manager.process_chat_request(
                request=request,
                synth_context=synth_context
            )
            
            # Trigger memory consolidation asynchronously
            asyncio.create_task(
                self._consolidate_conversation_memory(
                    session_id=request.session_id,
                    client_user_id=request.client_user_id,
                    actor_id=request.actor_id,
                    actor_type=request.actor_type
                )
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing chat request: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process chat request"
            )
            
    async def process_chat_stream(
        self,
        request: ChatRequest,
        token_data: TokenData = Depends(verify_chat_access_enhanced)
    ) -> StreamingResponse:
        """
        Process a chat request with streaming response.
        
        Args:
            request: Chat request from client
            token_data: Authenticated token data
            
        Returns:
            Streaming response
        """
        try:
            # Validate request
            if request.client_user_id != token_data.client_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Client user ID mismatch"
                )
                
            if request.actor_id != token_data.actor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Actor ID mismatch"
                )
                
            # Resolve SYNTH context
            synth_context = await self._resolve_synth_context(
                actor_id=request.actor_id,
                client_id=request.client_user_id
            )
            
            if not synth_context:
                synth_context = SynthContext(
                    synth_id=request.actor_id,
                    synth_class_id=0,
                    client_id=request.client_user_id,
                    synth_class_config={},
                    company_customizations={},
                    client_policies={},
                    memory_access_scope=["fact", "skill", "procedure"]
                )
                
            # Create streaming response
            async def generate():
                """Generate SSE formatted chunks."""
                try:
                    async for chunk in self.conversation_manager.process_chat_stream(
                        request=request,
                        synth_context=synth_context
                    ):
                        # Format as Server-Sent Event
                        yield f"data: {chunk}\n\n"
                        
                    # Send completion event
                    yield f"data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in stream generation: {e}")
                    yield f"data: Error: {str(e)}\n\n"
                    
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting up chat stream: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to setup chat stream"
            )
            
    async def get_session_context(
        self,
        session_id: UUID,
        token_data: TokenData = Depends(verify_chat_access_enhanced)
    ) -> dict:
        """
        Get session context information.
        
        Args:
            session_id: Session identifier
            token_data: Authenticated token data
            
        Returns:
            Session context information
        """
        try:
            context = await self.session_manager.store.get(session_id)
            
            if not context:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
                
            # Verify session belongs to authenticated user
            if context.client_user_id != token_data.client_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this session"
                )
                
            # Return session info
            return {
                "session_id": str(context.session_id),
                "client_user_id": str(context.client_user_id),
                "actor_id": str(context.actor_id),
                "created_at": context.created_at.isoformat(),
                "last_activity": context.last_activity.isoformat(),
                "message_count": len(context.conversation_history),
                "has_thinking_session": context.thinking_session_id is not None,
                "memory_context_count": len(context.active_memory_context)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve session context"
            )
            
    async def delete_session(
        self,
        session_id: UUID,
        token_data: TokenData = Depends(verify_chat_access_enhanced)
    ) -> dict:
        """
        Delete a chat session.
        
        Args:
            session_id: Session to delete
            token_data: Authenticated token data
            
        Returns:
            Deletion status
        """
        try:
            # Verify ownership
            context = await self.session_manager.store.get(session_id)
            
            if not context:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
                
            if context.client_user_id != token_data.client_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this session"
                )
                
            # Delete session
            deleted = await self.session_manager.delete_session(session_id)
            
            return {
                "session_id": str(session_id),
                "deleted": deleted,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete session"
            )
            
    async def _resolve_synth_context(
        self,
        actor_id: UUID,
        client_id: UUID
    ) -> Optional[SynthContext]:
        """
        Resolve SYNTH context from memory service.
        
        Args:
            actor_id: SYNTH ID
            client_id: Client ID
            
        Returns:
            SYNTH context or None
        """
        try:
            return await self.memory_client.resolve_synth_context(
                actor_id=actor_id,
                client_id=client_id
            )
        except Exception as e:
            logger.error(f"Error resolving SYNTH context: {e}")
            return None
            
    async def _consolidate_conversation_memory(
        self,
        session_id: UUID,
        client_user_id: UUID,
        actor_id: UUID,
        actor_type: str
    ) -> None:
        """
        Trigger memory consolidation for a conversation session.
        
        Args:
            session_id: Session to consolidate
            client_user_id: Client user ID
            actor_id: Actor ID
            actor_type: Type of actor
        """
        try:
            # Get session context
            context = await self.session_manager.get_context(session_id)
            if not context or len(context.conversation_history) < 2:
                # Skip consolidation for very short conversations
                return
                
            # Format conversation text
            conversation_text = self._format_conversation_for_memory(
                context.conversation_history
            )
            
            # Create crew job request
            crew_job_request = {
                "job_key": "memory_maker_crew",
                "client_user_id": str(client_user_id),
                "actor_type": actor_type,
                "actor_id": str(actor_id),
                "text_content": conversation_text,
                "metadata": {
                    "source": "chat_session",
                    "session_id": str(session_id),
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_count": len(context.conversation_history)
                }
            }
            
            # Submit to crew API
            crew_api_url = self.settings.crew_api_url or "http://localhost:8000"
            response = await self.http_client.post(
                f"{crew_api_url}/crew_job",
                json=crew_job_request,
                headers={
                    "Authorization": f"Bearer {self.settings.internal_auth_token}"
                }
            )
            
            if response.status_code == 200:
                job_data = response.json()
                logger.info(
                    f"Memory consolidation job created: {job_data.get('job_id')} "
                    f"for session {session_id}"
                )
            else:
                logger.error(
                    f"Failed to create memory consolidation job: "
                    f"{response.status_code} - {response.text}"
                )
                
        except Exception as e:
            logger.error(
                f"Error consolidating conversation memory for session {session_id}: {e}",
                exc_info=True
            )
            # Don't raise - this is a background task
            
    def _format_conversation_for_memory(self, history: list) -> str:
        """
        Format conversation history as text for memory extraction.
        
        Args:
            history: Conversation history
            
        Returns:
            Formatted text
        """
        lines = []
        for msg in history:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            if timestamp:
                lines.append(f"[{timestamp}] {role}: {content}")
            else:
                lines.append(f"{role}: {content}")
                
        return "\n".join(lines)