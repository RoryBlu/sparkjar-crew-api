"""
Redis Session Manager for Chat V1.

KISS principles:
- Simple key-value storage in Redis
- Basic TTL management (24 hours)
- No complex indexing or queries
- Graceful handling of Redis failures
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from redis.exceptions import RedisError

from src.chat.config import get_settings
from src.chat.models import ChatRequestV1, ChatSessionV1

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Base exception for session operations."""
    pass


class RedisSessionManager:
    """
    Simple session management using Railway Redis.
    
    No clustering, no sharding, just basic Redis ops.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            redis_url: Override Redis URL for testing
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.ttl_seconds = 86400  # 24 hours
        self._redis: Optional[redis.Redis] = None
        
    async def _get_redis(self) -> redis.Redis:
        """
        Get Redis connection with lazy initialization.
        
        KISS: Single connection, reconnect on failure.
        """
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise SessionError(f"Redis connection failed: {e}")
                
        return self._redis
        
    async def create_or_get_session(
        self,
        request: ChatRequestV1
    ) -> ChatSessionV1:
        """
        Create a new session or retrieve existing one.
        
        Args:
            request: Chat request with optional session_id
            
        Returns:
            ChatSessionV1 instance
            
        Raises:
            SessionError: On Redis failures
        """
        try:
            # Use provided session_id or create new one
            session_id = request.session_id or uuid4()
            
            # Try to get existing session
            if request.session_id:
                existing = await self.get_session(session_id)
                if existing:
                    # Update last activity
                    existing.last_activity = datetime.utcnow()
                    existing.message_count += 1
                    
                    # Check mode consistency
                    if existing.mode != request.mode:
                        logger.warning(
                            f"Mode mismatch for session {session_id}: "
                            f"stored={existing.mode}, requested={request.mode}"
                        )
                        existing.mode = request.mode  # Update mode
                        
                    await self._save_session(existing)
                    return existing
                    
            # Create new session
            now = datetime.utcnow()
            session = ChatSessionV1(
                session_id=session_id,
                client_user_id=request.client_user_id,
                actor_type=request.actor_type,
                actor_id=str(request.actor_id),
                mode=request.mode,
                created_at=now,
                last_activity=now,
                expires_at=now + timedelta(seconds=self.ttl_seconds),
                message_count=1,
                learning_preferences=request.learning_preferences
            )
            
            await self._save_session(session)
            logger.info(f"Created new session: {session_id}")
            
            return session
            
        except RedisError as e:
            logger.error(f"Redis error in create_or_get_session: {e}")
            # Could return a temporary in-memory session here
            raise SessionError(f"Failed to manage session: {e}")
            
    async def get_session(self, session_id: UUID) -> Optional[ChatSessionV1]:
        """
        Retrieve session from Redis.
        
        Args:
            session_id: Session UUID
            
        Returns:
            ChatSessionV1 or None if not found/expired
        """
        try:
            conn = await self._get_redis()
            key = f"chat:session:{session_id}"
            
            data = await conn.get(key)
            if not data:
                return None
                
            session = ChatSessionV1.from_redis_value(data)
            
            # Check if expired
            if datetime.utcnow() > session.expires_at:
                logger.info(f"Session {session_id} has expired")
                await conn.delete(key)
                return None
                
            return session
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid session data for {session_id}: {e}")
            return None
        except RedisError as e:
            logger.error(f"Redis error getting session: {e}")
            return None
            
    async def update_session(
        self,
        session_id: UUID,
        **updates
    ) -> Optional[ChatSessionV1]:
        """
        Update specific session fields.
        
        Args:
            session_id: Session to update
            **updates: Fields to update
            
        Returns:
            Updated session or None if not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None
            
        # Apply updates
        for field, value in updates.items():
            if hasattr(session, field):
                setattr(session, field, value)
                
        # Always update last activity
        session.last_activity = datetime.utcnow()
        
        await self._save_session(session)
        return session
        
    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            conn = await self._get_redis()
            key = f"chat:session:{session_id}"
            
            result = await conn.delete(key)
            if result > 0:
                logger.info(f"Deleted session: {session_id}")
                return True
                
            return False
            
        except RedisError as e:
            logger.error(f"Redis error deleting session: {e}")
            return False
            
    async def update_learning_state(
        self,
        session_id: UUID,
        topic: Optional[str] = None,
        path_item: Optional[str] = None,
        understanding_level: Optional[int] = None
    ) -> Optional[ChatSessionV1]:
        """
        Update tutor mode learning state.
        
        Args:
            session_id: Session to update
            topic: New learning topic
            path_item: Item to add to learning path
            understanding_level: New understanding level (1-5)
            
        Returns:
            Updated session or None
        """
        session = await self.get_session(session_id)
        if not session or session.mode != "tutor":
            return None
            
        if topic is not None:
            session.learning_topic = topic
            
        if path_item is not None:
            if session.learning_path is None:
                session.learning_path = []
            session.learning_path.append(path_item)
            # Validator will limit to 10 items
            
        if understanding_level is not None:
            session.understanding_level = understanding_level
            
        await self._save_session(session)
        return session
        
    async def _save_session(self, session: ChatSessionV1):
        """
        Save session to Redis with TTL.
        
        Uses expires_at field to calculate TTL.
        """
        try:
            conn = await self._get_redis()
            key = f"chat:session:{session.session_id}"
            
            # Calculate TTL from expires_at
            ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
            if ttl <= 0:
                ttl = 60  # Minimum 1 minute
                
            await conn.setex(
                name=key,
                time=ttl,
                value=session.to_redis_value()
            )
            
        except RedisError as e:
            logger.error(f"Failed to save session: {e}")
            raise SessionError(f"Failed to save session: {e}")
            
    async def get_user_sessions_count(self, client_user_id: UUID) -> int:
        """
        Get count of active sessions for a user.
        
        KISS: Just scan keys, don't maintain indexes.
        Good enough for 100 concurrent users.
        """
        try:
            conn = await self._get_redis()
            count = 0
            
            # Scan for user's sessions
            cursor = 0
            pattern = "chat:session:*"
            
            while True:
                cursor, keys = await conn.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                
                # Check each key
                for key in keys:
                    try:
                        data = await conn.get(key)
                        if data:
                            session_data = json.loads(data)
                            if session_data.get("client_user_id") == str(client_user_id):
                                count += 1
                    except:
                        continue
                        
                if cursor == 0:
                    break
                    
            return count
            
        except RedisError as e:
            logger.error(f"Failed to count user sessions: {e}")
            return 0
            
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Redis TTL should handle this, but this is a backup.
        Could be run periodically.
        """
        try:
            conn = await self._get_redis()
            deleted = 0
            cursor = 0
            pattern = "chat:session:*"
            now = datetime.utcnow()
            
            while True:
                cursor, keys = await conn.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                
                for key in keys:
                    try:
                        data = await conn.get(key)
                        if data:
                            session = ChatSessionV1.from_redis_value(data)
                            if now > session.expires_at:
                                await conn.delete(key)
                                deleted += 1
                    except:
                        # Delete corrupted entries
                        await conn.delete(key)
                        deleted += 1
                        
                if cursor == 0:
                    break
                    
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired sessions")
                
            return deleted
            
        except RedisError as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0
            
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")