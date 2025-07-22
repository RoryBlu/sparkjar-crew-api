"""
Session context management with Redis backend.

Handles conversation session storage, TTL management, and
concurrent access control for multi-instance deployments.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

import redis.asyncio as redis
from redis.asyncio.lock import Lock
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.chatmodels.context_models import ConversationContext, SynthContext
from src.chatmodels.chat_models import ChatMessage
from src.chatconfig import get_settings
from src.chatutils.error_handler import ChatErrorHandler, ServiceError, ErrorCategory

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Base exception for session management errors."""
    pass


class SessionNotFoundError(SessionError):
    """Raised when a session is not found."""
    pass


class ContextSerializer:
    """Handles serialization/deserialization of conversation context."""
    
    @staticmethod
    def serialize(context: ConversationContext) -> str:
        """
        Serialize conversation context to JSON string.
        
        Args:
            context: Conversation context to serialize
            
        Returns:
            JSON string representation
        """
        data = {
            "session_id": str(context.session_id),
            "client_user_id": str(context.client_user_id),
            "actor_type": context.actor_type,
            "actor_id": str(context.actor_id),
            "synth_context": {
                "synth_id": str(context.synth_context.synth_id),
                "synth_class_id": context.synth_context.synth_class_id,
                "client_id": str(context.synth_context.client_id),
                "synth_class_config": context.synth_context.synth_class_config,
                "company_customizations": context.synth_context.company_customizations,
                "client_policies": context.synth_context.client_policies,
                "memory_access_scope": context.synth_context.memory_access_scope
            },
            "conversation_history": [
                {
                    "message_id": str(msg.message_id),
                    "session_id": str(msg.session_id),
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in context.conversation_history
            ],
            "active_memory_context": [
                entity.model_dump() for entity in context.active_memory_context
            ],
            "thinking_session_id": str(context.thinking_session_id) if context.thinking_session_id else None,
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "metadata": context.metadata
        }
        
        return json.dumps(data)
        
    @staticmethod
    def deserialize(data: str) -> ConversationContext:
        """
        Deserialize JSON string to conversation context.
        
        Args:
            data: JSON string to deserialize
            
        Returns:
            ConversationContext instance
        """
        parsed = json.loads(data)
        
        # Reconstruct SynthContext
        synth_data = parsed["synth_context"]
        synth_context = SynthContext(
            synth_id=UUID(synth_data["synth_id"]),
            synth_class_id=synth_data["synth_class_id"],
            client_id=UUID(synth_data["client_id"]),
            synth_class_config=synth_data["synth_class_config"],
            company_customizations=synth_data["company_customizations"],
            client_policies=synth_data["client_policies"],
            memory_access_scope=synth_data["memory_access_scope"]
        )
        
        # Reconstruct conversation history
        conversation_history = []
        for msg_data in parsed["conversation_history"]:
            conversation_history.append(ChatMessage(
                message_id=UUID(msg_data["message_id"]),
                session_id=UUID(msg_data["session_id"]),
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                metadata=msg_data.get("metadata")
            ))
            
        # Reconstruct context
        return ConversationContext(
            session_id=UUID(parsed["session_id"]),
            client_user_id=UUID(parsed["client_user_id"]),
            actor_type=parsed["actor_type"],
            actor_id=UUID(parsed["actor_id"]),
            synth_context=synth_context,
            conversation_history=conversation_history,
            active_memory_context=parsed.get("active_memory_context", []),
            thinking_session_id=UUID(parsed["thinking_session_id"]) if parsed.get("thinking_session_id") else None,
            created_at=datetime.fromisoformat(parsed["created_at"]),
            last_activity=datetime.fromisoformat(parsed["last_activity"]),
            metadata=parsed.get("metadata", {})
        )


class SessionContextStore:
    """Redis-based storage for conversation session contexts."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize session store.
        
        Args:
            redis_url: Override Redis URL
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.ttl_hours = settings.session_ttl_hours
        self.key_prefix = "chat_session:"
        self._redis: Optional[redis.Redis] = None
        
    async def connect(self):
        """Establish Redis connection."""
        try:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            logger.info("Connected to Redis for session storage")
        except Exception as e:
            service_error = ChatErrorHandler.handle_redis_error(e)
            logger.error(f"Redis connection failed: {service_error.message}", extra={"details": service_error.details})
            raise ChatErrorHandler.to_http_exception(service_error)
            
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            
    def _get_key(self, session_id: UUID) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"
        
    async def get(self, session_id: UUID) -> Optional[ConversationContext]:
        """
        Retrieve session context from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationContext or None if not found
        """
        if not self._redis:
            raise SessionError("Redis not connected")
            
        try:
            key = self._get_key(session_id)
            data = await self._redis.get(key)
            
            if not data:
                return None
                
            return ContextSerializer.deserialize(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize session {session_id}: {e}")
            return None
        except RedisError as e:
            logger.error(f"Redis error retrieving session {session_id}: {e}")
            raise SessionError(f"Failed to retrieve session: {e}")
            
    async def set(
        self,
        context: ConversationContext,
        ttl_override: Optional[int] = None
    ) -> None:
        """
        Store session context in Redis.
        
        Args:
            context: Conversation context to store
            ttl_override: Override TTL in seconds
        """
        if not self._redis:
            raise SessionError("Redis not connected")
            
        try:
            key = self._get_key(context.session_id)
            data = ContextSerializer.serialize(context)
            
            ttl = ttl_override or (self.ttl_hours * 3600)
            await self._redis.setex(key, ttl, data)
            
            logger.debug(f"Stored session {context.session_id} with TTL {ttl}s")
            
        except RedisError as e:
            logger.error(f"Redis error storing session {context.session_id}: {e}")
            raise SessionError(f"Failed to store session: {e}")
            
    async def delete(self, session_id: UUID) -> bool:
        """
        Delete session from Redis.
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if deleted, False if not found
        """
        if not self._redis:
            raise SessionError("Redis not connected")
            
        try:
            key = self._get_key(session_id)
            result = await self._redis.delete(key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis error deleting session {session_id}: {e}")
            raise SessionError(f"Failed to delete session: {e}")
            
    async def exists(self, session_id: UUID) -> bool:
        """Check if session exists."""
        if not self._redis:
            raise SessionError("Redis not connected")
            
        try:
            key = self._get_key(session_id)
            return await self._redis.exists(key) > 0
            
        except RedisError as e:
            logger.error(f"Redis error checking session {session_id}: {e}")
            raise SessionError(f"Failed to check session: {e}")
            
    async def touch(self, session_id: UUID) -> bool:
        """
        Update session last activity time and reset TTL.
        
        Args:
            session_id: Session to touch
            
        Returns:
            True if updated, False if not found
        """
        context = await self.get(session_id)
        if not context:
            return False
            
        context.last_activity = datetime.utcnow()
        await self.set(context)
        return True
        
    async def acquire_lock(
        self,
        session_id: UUID,
        timeout: float = 5.0
    ) -> Lock:
        """
        Acquire distributed lock for session.
        
        Args:
            session_id: Session to lock
            timeout: Lock timeout in seconds
            
        Returns:
            Redis lock instance
        """
        if not self._redis:
            raise SessionError("Redis not connected")
            
        lock_key = f"{self.key_prefix}lock:{session_id}"
        return self._redis.lock(lock_key, timeout=timeout)


class SessionManager:
    """High-level session management operations."""
    
    def __init__(self, store: Optional[SessionContextStore] = None):
        """
        Initialize session manager.
        
        Args:
            store: Session store instance (creates default if None)
        """
        self.store = store or SessionContextStore()
        self.settings = get_settings()
        
    async def create_session(
        self,
        client_user_id: UUID,
        actor_type: str,
        actor_id: UUID,
        synth_context: SynthContext,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Create a new conversation session.
        
        Args:
            client_user_id: Client user identifier
            actor_type: Type of actor (synth)
            actor_id: Actor identifier
            synth_context: Resolved SYNTH context
            metadata: Optional session metadata
            
        Returns:
            New conversation context
        """
        session_id = uuid4()
        now = datetime.utcnow()
        
        context = ConversationContext(
            session_id=session_id,
            client_user_id=client_user_id,
            actor_type=actor_type,
            actor_id=actor_id,
            synth_context=synth_context,
            conversation_history=[],
            active_memory_context=[],
            thinking_session_id=None,
            created_at=now,
            last_activity=now,
            metadata=metadata or {}
        )
        
        await self.store.set(context)
        logger.info(f"Created new session {session_id} for actor {actor_id}")
        
        return context
        
    async def get_or_create_session(
        self,
        session_id: Optional[UUID],
        client_user_id: UUID,
        actor_type: str,
        actor_id: UUID,
        synth_context: SynthContext,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Existing session ID (optional)
            client_user_id: Client user identifier
            actor_type: Type of actor
            actor_id: Actor identifier
            synth_context: Resolved SYNTH context
            metadata: Session metadata
            
        Returns:
            Conversation context
        """
        if session_id:
            context = await self.store.get(session_id)
            if context:
                # Validate session belongs to correct actor
                if context.actor_id != actor_id or context.client_user_id != client_user_id:
                    logger.warning(f"Session {session_id} actor mismatch")
                    raise SessionError("Session does not belong to this actor")
                    
                # Touch to update activity
                await self.store.touch(session_id)
                return context
                
        # Create new session
        return await self.create_session(
            client_user_id=client_user_id,
            actor_type=actor_type,
            actor_id=actor_id,
            synth_context=synth_context,
            metadata=metadata
        )
        
    async def add_message(
        self,
        session_id: UUID,
        message: ChatMessage
    ) -> None:
        """
        Add message to conversation history.
        
        Args:
            session_id: Session identifier
            message: Message to add
        """
        async with await self.store.acquire_lock(session_id):
            context = await self.store.get(session_id)
            if not context:
                raise SessionNotFoundError(f"Session {session_id} not found")
                
            # Add message to history
            context.conversation_history.append(message)
            
            # Prune if exceeds max history
            max_history = self.settings.max_conversation_history
            if len(context.conversation_history) > max_history:
                # Keep most recent messages
                context.conversation_history = context.conversation_history[-max_history:]
                
            # Update activity time
            context.last_activity = datetime.utcnow()
            
            await self.store.set(context)
            
    async def update_memory_context(
        self,
        session_id: UUID,
        memory_entities: List[Any]
    ) -> None:
        """
        Update active memory context for session.
        
        Args:
            session_id: Session identifier
            memory_entities: Memory entities to set as context
        """
        async with await self.store.acquire_lock(session_id):
            context = await self.store.get(session_id)
            if not context:
                raise SessionNotFoundError(f"Session {session_id} not found")
                
            context.active_memory_context = memory_entities
            context.last_activity = datetime.utcnow()
            
            await self.store.set(context)
            
    async def set_thinking_session(
        self,
        session_id: UUID,
        thinking_session_id: UUID
    ) -> None:
        """
        Associate thinking session with conversation.
        
        Args:
            session_id: Conversation session ID
            thinking_session_id: Sequential thinking session ID
        """
        async with await self.store.acquire_lock(session_id):
            context = await self.store.get(session_id)
            if not context:
                raise SessionNotFoundError(f"Session {session_id} not found")
                
            context.thinking_session_id = thinking_session_id
            context.last_activity = datetime.utcnow()
            
            await self.store.set(context)
            
    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if deleted, False if not found
        """
        return await self.store.delete(session_id)