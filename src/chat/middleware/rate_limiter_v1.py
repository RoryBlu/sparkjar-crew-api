"""
Basic Rate Limiting for Chat with Memory v1.

KISS principles:
- Simple Redis-based rate limiting
- Per-user limits with clear messages
- No complex algorithms
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

import redis.asyncio as redis
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple rate limiter using Redis.
    
    KISS: Just track requests per user per time window.
    """
    
    def __init__(
        self,
        redis_url: str,
        requests_per_minute: int = 20,
        requests_per_hour: int = 200
    ):
        """
        Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
        """
        self.redis_url = redis_url
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self._redis: Optional[redis.Redis] = None
        
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
        
    async def check_rate_limit(
        self,
        user_id: UUID,
        endpoint: str = "chat"
    ) -> Tuple[bool, dict]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User UUID
            endpoint: Endpoint being accessed
            
        Returns:
            Tuple of (allowed, headers_dict)
        """
        try:
            conn = await self._get_redis()
            now = datetime.utcnow()
            
            # Keys for tracking
            minute_key = f"rate:{endpoint}:{user_id}:min:{now.strftime('%Y%m%d%H%M')}"
            hour_key = f"rate:{endpoint}:{user_id}:hour:{now.strftime('%Y%m%d%H')}"
            
            # Use pipeline for atomic operations
            pipe = conn.pipeline()
            
            # Increment counters
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)  # Expire after 1 minute
            
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)  # Expire after 1 hour
            
            # Execute pipeline
            results = await pipe.execute()
            
            minute_count = results[0]
            hour_count = results[2]
            
            # Check limits
            if minute_count > self.requests_per_minute:
                return False, {
                    "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
                    "X-RateLimit-Remaining-Minute": "0",
                    "X-RateLimit-Reset": str(int((now + timedelta(minutes=1)).timestamp())),
                    "Retry-After": "60"
                }
                
            if hour_count > self.requests_per_hour:
                return False, {
                    "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
                    "X-RateLimit-Remaining-Hour": "0",
                    "X-RateLimit-Reset": str(int((now + timedelta(hours=1)).timestamp())),
                    "Retry-After": "3600"
                }
                
            # Calculate remaining
            remaining_minute = max(0, self.requests_per_minute - minute_count)
            remaining_hour = max(0, self.requests_per_hour - hour_count)
            
            headers = {
                "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
                "X-RateLimit-Remaining-Minute": str(remaining_minute),
                "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
                "X-RateLimit-Remaining-Hour": str(remaining_hour)
            }
            
            return True, headers
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow request but log it
            return True, {}
            
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    KISS: Only limit specific endpoints, not everything.
    """
    
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests."""
        # Only rate limit chat endpoints
        if not request.url.path.startswith("/v1/chat"):
            return await call_next(request)
            
        # Extract user ID from request
        # In production, this would come from JWT token
        try:
            # Get user from request state (set by auth middleware)
            user = getattr(request.state, "user", None)
            if not user:
                return await call_next(request)
                
            user_id = UUID(user.get("client_user_id", user.get("user_id")))
            
            # Check rate limit
            allowed, headers = await self.rate_limiter.check_rate_limit(
                user_id,
                "chat"
            )
            
            if not allowed:
                # Rate limit exceeded
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later.",
                    headers=headers
                )
                
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            for key, value in headers.items():
                response.headers[key] = value
                
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # On error, allow request
            return await call_next(request)


def create_rate_limiter_dependency(redis_url: str):
    """
    Create a FastAPI dependency for rate limiting.
    
    Usage:
        rate_limiter = create_rate_limiter_dependency(redis_url)
        
        @router.post("/endpoint")
        async def endpoint(
            rate_limit: bool = Depends(rate_limiter)
        ):
            ...
    """
    limiter = RateLimiter(redis_url)
    
    async def check_limit(request: Request, response: Response):
        """Dependency function for rate limiting."""
        # Extract user from request
        user = getattr(request.state, "user", None)
        if not user:
            return True
            
        user_id = UUID(user.get("client_user_id", user.get("user_id")))
        
        # Check rate limit
        allowed, headers = await limiter.check_rate_limit(user_id, "chat")
        
        # Add headers to response
        for key, value in headers.items():
            response.headers[key] = value
            
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers=headers
            )
            
        return True
        
    return check_limit