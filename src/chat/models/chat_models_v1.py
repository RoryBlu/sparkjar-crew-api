"""
Chat V1 models with memory integration and mode support.

KISS principle: Extend existing models, don't reinvent.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .chat_models import ChatRequest, ChatResponse


class ChatRequestV1(ChatRequest):
    """Enhanced chat request with mode support and memory configuration."""
    
    # Mode support - simple enum, no complex state machines
    mode: Literal["tutor", "agent"] = Field(
        default="agent",
        description="Interaction mode: 'tutor' for proactive learning, 'agent' for passive assistance"
    )
    
    # Memory realm configuration - sensible defaults
    include_realms: Dict[str, bool] = Field(
        default_factory=lambda: {
            "include_own": True,
            "include_class": True,
            "include_skills": True,
            "include_client": True
        },
        description="Which memory realms to include in context"
    )
    
    # Simple learning preferences - optional, no complex schemas
    learning_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User's learning preferences for tutor mode (pace, depth, style)"
    )
    
    # Reasonable depth limit to prevent performance issues
    context_depth: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Depth of relationship traversal in knowledge graph"
    )
    
    @validator('learning_preferences')
    def validate_learning_preferences(cls, v):
        """Keep learning preferences simple - no nested objects."""
        if v is not None and len(str(v)) > 1000:
            raise ValueError("Learning preferences too complex - keep it simple")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "actor_type": "synth",
                "actor_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "message": "How do I optimize database queries?",
                "mode": "tutor",
                "session_id": "456e7890-e12b-34d5-a678-901234567def",
                "include_realms": {
                    "include_own": True,
                    "include_class": True,
                    "include_skills": True,
                    "include_client": True
                },
                "learning_preferences": {
                    "pace": "moderate",
                    "depth": "intermediate"
                },
                "context_depth": 2
            }
        }


class ChatResponseV1(ChatResponse):
    """Enhanced chat response with memory context details."""
    
    # Which mode was actually used
    mode_used: Literal["tutor", "agent"] = Field(
        ...,
        description="The mode that was active for this response"
    )
    
    # Simple realm access tracking
    memory_realms_accessed: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of memories accessed from each realm"
    )
    
    # Tutor mode specific - optional fields
    learning_path: Optional[List[str]] = Field(
        default=None,
        description="Learning path topics in tutor mode"
    )
    
    next_suggested_topics: Optional[List[str]] = Field(
        default=None,
        description="Suggested follow-up topics in tutor mode"
    )
    
    # Simple metric for graph traversal
    relationships_traversed: int = Field(
        default=0,
        description="Number of entity relationships traversed"
    )
    
    # Performance metrics - useful for monitoring
    memory_query_time_ms: Optional[int] = Field(
        default=None,
        description="Time spent querying memory service"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "456e7890-e12b-34d5-a678-901234567def",
                "message_id": "789abcde-f012-3456-789a-bcdef0123456",
                "message": "How do I optimize database queries?",
                "response": "Great question! Let's start with understanding indexes...",
                "mode_used": "tutor",
                "memory_context_used": ["database_optimization", "query_patterns", "index_strategies"],
                "memory_realms_accessed": {
                    "synth": 2,
                    "synth_class": 5,
                    "client": 1
                },
                "learning_path": ["SQL Basics", "Query Optimization", "Index Design"],
                "next_suggested_topics": ["Compound Indexes", "Query Execution Plans"],
                "relationships_traversed": 8,
                "memory_query_time_ms": 145,
                "thinking_session_id": None,
                "metadata": {
                    "response_time_ms": 1250,
                    "memory_queries": 3,
                    "tokens_used": 150
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ChatSessionV1(BaseModel):
    """Enhanced session model for Redis storage - keep it flat and simple."""
    
    # Core identifiers
    session_id: UUID
    client_user_id: UUID
    actor_type: str
    actor_id: str
    mode: Literal["tutor", "agent"]
    
    # Timestamps
    created_at: datetime
    last_activity: datetime
    expires_at: datetime  # Explicit TTL for easier management
    
    # Mode-specific state - simple flat structure
    learning_topic: Optional[str] = None
    learning_path: Optional[List[str]] = Field(default_factory=list)
    understanding_level: Optional[int] = Field(default=None, ge=1, le=5)
    
    # Conversation tracking - just the essentials
    message_count: int = 0
    last_memory_query: Optional[str] = None  # For cache key generation
    
    # Simple performance metrics
    total_response_time_ms: int = 0
    total_memory_queries: int = 0
    
    @validator('learning_path')
    def limit_learning_path(cls, v):
        """Prevent unbounded growth - keep last 10 topics."""
        if v and len(v) > 10:
            return v[-10:]
        return v
    
    def to_redis_value(self) -> str:
        """Convert to JSON string for Redis storage."""
        return self.json()
    
    @classmethod
    def from_redis_value(cls, value: str) -> 'ChatSessionV1':
        """Create from Redis JSON string."""
        return cls.parse_raw(value)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }