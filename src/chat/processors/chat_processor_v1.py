"""
Main Chat Processor with Mode Switching for Chat with Memory v1.

KISS principles:
- Simple mode switching logic
- Clear separation between modes
- Minimal state management
"""

import logging
from typing import Any, Optional
from uuid import UUID

from src.chat.models import (
    ChatRequestV1,
    ChatResponseV1,
    ChatSessionV1
)
from src.chat.processors.tutor_mode_v1 import TutorModeProcessor
from src.chat.processors.agent_mode_v1 import AgentModeProcessor
from src.chat.services.memory_search_v1 import HierarchicalMemorySearcher
from src.chat.services.session_manager_v1 import RedisSessionManager
from src.chat.services.conversation_store_v1 import ConversationMemoryStore

logger = logging.getLogger(__name__)


class ChatProcessorV1:
    """
    Main chat processor that handles mode switching and orchestration.
    
    KISS: Simple delegation to mode processors.
    """
    
    def __init__(
        self,
        memory_searcher: HierarchicalMemorySearcher,
        session_manager: RedisSessionManager,
        conversation_store: ConversationMemoryStore,
        llm_client: Any  # Will be injected
    ):
        """
        Initialize chat processor with all dependencies.
        
        Args:
            memory_searcher: Memory search service
            session_manager: Redis session management
            conversation_store: Conversation storage
            llm_client: LLM service client
        """
        self.memory_searcher = memory_searcher
        self.session_manager = session_manager
        self.conversation_store = conversation_store
        
        # Initialize mode processors
        self.tutor_processor = TutorModeProcessor(memory_searcher, llm_client)
        self.agent_processor = AgentModeProcessor(memory_searcher, llm_client)
        
    async def process_chat_request(
        self,
        request: ChatRequestV1,
        client_id: UUID
    ) -> ChatResponseV1:
        """
        Process a chat request with mode handling.
        
        Args:
            request: Incoming chat request
            client_id: Client UUID from auth
            
        Returns:
            ChatResponseV1 with appropriate mode processing
        """
        try:
            # 1. Get or create session
            session = await self.session_manager.create_or_get_session(request)
            
            # 2. Process based on mode
            if session.mode == "tutor":
                response = await self.tutor_processor.process_request(
                    request,
                    session,
                    client_id
                )
            else:  # agent mode
                response = await self.agent_processor.process_request(
                    request,
                    session,
                    client_id
                )
                
            # 3. Store conversation
            memories_used = response.memory_context_used
            await self.conversation_store.store_conversation_exchange(
                session=session,
                message=request.message,
                response=response,
                memories_used=memories_used
            )
            
            # 4. Update session state if in tutor mode
            if session.mode == "tutor" and response.learning_context:
                await self._update_tutor_session(
                    session,
                    response
                )
                
            return response
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            raise
            
    async def switch_mode(
        self,
        session_id: UUID,
        new_mode: str,
        client_id: UUID
    ) -> ChatSessionV1:
        """
        Switch between tutor and agent modes.
        
        Args:
            session_id: Session to switch
            new_mode: "tutor" or "agent"
            client_id: For authorization
            
        Returns:
            Updated session
        """
        # Get current session
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        # Verify ownership
        if session.client_user_id != client_id:
            raise ValueError("Unauthorized session access")
            
        # Already in requested mode
        if session.mode == new_mode:
            return session
            
        logger.info(f"Switching session {session_id} from {session.mode} to {new_mode}")
        
        # Clear mode-specific state
        updates = {"mode": new_mode}
        
        if new_mode == "agent":
            # Clear tutor-specific fields
            updates.update({
                "learning_topic": None,
                "learning_path": None,
                "understanding_level": None,
                "learning_preferences": None
            })
        else:  # switching to tutor
            # Initialize tutor fields
            updates.update({
                "understanding_level": 3,  # Start at middle level
                "learning_path": []
            })
            
        # Update session
        updated_session = await self.session_manager.update_session(
            session_id,
            **updates
        )
        
        return updated_session
        
    async def _update_tutor_session(
        self,
        session: ChatSessionV1,
        response: ChatResponseV1
    ):
        """
        Update session with tutor mode learning state.
        """
        learning_context = response.learning_context or {}
        
        # Extract learning updates
        understanding_level = learning_context.get("understanding_level")
        learning_objective = learning_context.get("learning_objective")
        
        # Update session
        if understanding_level != session.understanding_level:
            await self.session_manager.update_learning_state(
                session_id=session.session_id,
                understanding_level=understanding_level
            )
            
        # Update learning path if new objective
        if learning_objective and response.learning_path:
            # The path was already updated in tutor processor
            await self.session_manager.update_session(
                session.session_id,
                learning_path=response.learning_path
            )
            
    async def get_learning_progress(
        self,
        session_id: UUID,
        client_id: UUID
    ) -> dict:
        """
        Get learning progress for a tutor session.
        
        Returns:
            Progress summary with path and understanding level
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        # Verify ownership
        if session.client_user_id != client_id:
            raise ValueError("Unauthorized session access")
            
        if session.mode != "tutor":
            return {
                "error": "Session is not in tutor mode",
                "mode": session.mode
            }
            
        return {
            "session_id": str(session.session_id),
            "learning_topic": session.learning_topic,
            "understanding_level": session.understanding_level,
            "learning_path": session.learning_path or [],
            "message_count": session.message_count,
            "session_duration_minutes": int(
                (session.last_activity - session.created_at).total_seconds() / 60
            )
        }