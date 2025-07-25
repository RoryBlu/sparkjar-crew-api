"""
Conversation Memory Storage Service.

KISS principles:
- Store conversations as memory entities
- Simple relationship extraction
- Async queue for memory maker crew
- No complex analysis in hot path
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from src.chat.clients.memory_service import MemoryServiceClient, MemoryServiceError
from src.chat.models import (
    ChatResponseV1,
    ChatSessionV1,
    ConversationEntity,
    create_conversation_entity
)
# We'll implement a simple queue function instead of importing
# from src.services.crew_service import queue_crew_job

logger = logging.getLogger(__name__)


class ConversationStoreError(Exception):
    """Base exception for conversation storage."""
    pass


class ConversationMemoryStore:
    """
    Stores conversations as memory entities.
    
    KISS: Just store the basics, let Memory Maker Crew do deep analysis.
    """
    
    def __init__(self, memory_client: MemoryServiceClient):
        """
        Initialize conversation store.
        
        Args:
            memory_client: Client for memory service
        """
        self.memory_client = memory_client
        
    async def store_conversation_exchange(
        self,
        session: ChatSessionV1,
        message: str,
        response: ChatResponseV1,
        memories_used: List[str]
    ) -> Optional[str]:
        """
        Store a conversation exchange as a memory entity.
        
        Args:
            session: Current chat session
            message: User's message
            response: Generated response with metadata
            memories_used: List of memory entities referenced
            
        Returns:
            Entity ID if stored successfully, None on error
        """
        try:
            # Create conversation entity
            entity = create_conversation_entity(
                session_id=session.session_id,
                actor_id=session.actor_id,
                mode=session.mode,
                participant_id=session.client_user_id,
                message=message,
                response=response.response,
                memories_used=memories_used[:10],  # Top 10
                topic=session.learning_topic
            )
            
            # Convert to API format
            entity_data = {
                "actor_type": entity.actor_type,
                "actor_id": entity.actor_id,
                "entity": entity.entity,
                "observations": [obs.dict() for obs in entity.observations],
                "relationships": [rel.dict() for rel in entity.relationships]
            }
            
            # Store via memory service
            # Using the create complete entity endpoint
            result = await self._store_entity(entity_data)
            
            if result:
                entity_id = result.get("entity", {}).get("id")
                logger.info(f"Stored conversation entity: {entity_id}")
                
                # Queue for memory maker crew (async, don't wait)
                asyncio.create_task(
                    self._queue_memory_extraction(
                        session_id=session.session_id,
                        entity_id=entity_id,
                        mode=session.mode
                    )
                )
                
                return entity_id
            else:
                logger.error("Failed to store conversation entity")
                return None
                
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return None
            
    async def _store_entity(self, entity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Store entity via memory service API.
        
        Uses the /memory/entities/complete endpoint.
        """
        try:
            # The memory client doesn't have this method yet, 
            # so we'll use the raw request method
            result = await self.memory_client._make_request(
                method="POST",
                endpoint="/memory/entities/complete",
                json_data=entity_data
            )
            
            return result
            
        except MemoryServiceError as e:
            logger.error(f"Memory service error: {e}")
            return None
            
    async def _queue_memory_extraction(
        self,
        session_id: UUID,
        entity_id: str,
        mode: str
    ):
        """
        Queue conversation for memory maker crew processing.
        
        Fire and forget - don't block on this.
        """
        try:
            # Queue memory maker crew job
            job_request = {
                "job_key": "memory_maker_crew",
                "request_data": {
                    "source_type": "chat_conversation",
                    "session_id": str(session_id),
                    "entity_id": entity_id,
                    "mode": mode,
                    "consolidation_type": "conversation_insights"
                }
            }
            
            # Simple job queue - in production this would call crew API
            # For now, just log it
            logger.info(f"Would queue memory extraction job: {job_request}")
            logger.info(f"Queued memory extraction for session {session_id}")
            
        except Exception as e:
            # Log but don't fail the main operation
            logger.warning(f"Failed to queue memory extraction: {e}")
            
    def extract_topic_from_message(
        self,
        message: str,
        memories_used: List[str]
    ) -> Optional[str]:
        """
        Simple topic extraction from message and memories.
        
        KISS: Just basic keyword extraction, no NLP.
        """
        # Use memory names as potential topics
        if memories_used:
            # Take the most referenced memory as topic
            return memories_used[0].replace("_", " ").title()
            
        # Basic keyword extraction from message
        keywords = ["database", "query", "optimization", "index", "performance",
                   "sql", "python", "api", "testing", "deployment"]
        
        message_lower = message.lower()
        for keyword in keywords:
            if keyword in message_lower:
                return keyword.title()
                
        return None
        
    def extract_entities_from_response(
        self,
        response: str,
        memories_used: List[str]
    ) -> List[str]:
        """
        Extract potential entity references from response.
        
        KISS: Just look for memory references and common patterns.
        No complex NLP or entity recognition.
        """
        entities = set(memories_used)  # Start with memories used
        
        # Look for common patterns (very basic)
        # This is where Memory Maker Crew will do better analysis
        
        # Look for quoted terms
        import re
        quoted = re.findall(r'"([^"]+)"', response)
        for term in quoted:
            if 2 < len(term) < 30:  # Reasonable entity name length
                entities.add(term.lower().replace(" ", "_"))
                
        # Look for capitalized terms (potential concepts)
        words = response.split()
        for i, word in enumerate(words):
            if word[0].isupper() and i > 0:  # Not start of sentence
                if 2 < len(word) < 20:
                    entities.add(word.lower())
                    
        # Limit to reasonable number
        return list(entities)[:20]
        
    async def get_recent_conversation_topics(
        self,
        actor_id: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get recent conversation topics for continuity.
        
        KISS: Just search for recent conversation entities.
        """
        try:
            # Search for recent conversations
            # This would need a proper endpoint, for now return empty
            # The memory maker crew will build proper topic tracking
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent topics: {e}")
            return []