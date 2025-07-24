"""
Chat-related data models for request/response handling.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ChatMessage(BaseModel):
    """Individual chat message in a conversation."""
    
    message_id: UUID = Field(..., description="Unique identifier for the message")
    session_id: UUID = Field(..., description="Session this message belongs to")
    role: Literal["user", "assistant", "system"] = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the message was created")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional message metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ChatRequest(BaseModel):
    """Request model for chat interactions."""
    
    client_user_id: UUID = Field(..., description="Client user identifier for billing and context")
    actor_type: Literal["synth"] = Field(..., description="Type of actor being impersonated")
    actor_id: UUID = Field(..., description="Specific SYNTH identifier")
    message: str = Field(..., min_length=1, max_length=10000, description="User message content")
    session_id: Optional[UUID] = Field(default=None, description="Existing session ID, if continuing conversation")
    enable_sequential_thinking: bool = Field(default=False, description="Whether to use sequential thinking mode")
    stream_response: bool = Field(default=True, description="Whether to stream the response")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional request metadata")
    
    @validator('message')
    def validate_message_content(cls, v):
        """Validate message content is not just whitespace."""
        if not v.strip():
            raise ValueError("Message content cannot be empty or only whitespace")
        return v.strip()
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "actor_type": "synth",
                "actor_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "message": "Hello, can you help me understand the latest project updates?",
                "session_id": "456e7890-e12b-34d5-a678-901234567def",
                "enable_sequential_thinking": False,
                "stream_response": True,
                "metadata": {
                    "client_version": "1.0.0",
                    "user_agent": "ChatClient/1.0"
                }
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat interactions."""
    
    session_id: UUID = Field(..., description="Session identifier for this conversation")
    message_id: UUID = Field(..., description="Unique identifier for this response message")
    message: str = Field(..., description="Original user message")
    response: str = Field(..., description="Generated response content")
    memory_context_used: List[str] = Field(default_factory=list, description="Memory contexts that influenced the response")
    thinking_session_id: Optional[UUID] = Field(default=None, description="Sequential thinking session ID if used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the response was generated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "session_id": "456e7890-e12b-34d5-a678-901234567def",
                "message_id": "789abcde-f012-3456-789a-bcdef0123456",
                "message": "Hello, can you help me understand the latest project updates?",
                "response": "I'd be happy to help you understand the latest project updates. Based on the context I have access to...",
                "memory_context_used": ["project_status", "team_updates", "recent_milestones"],
                "thinking_session_id": None,
                "metadata": {
                    "response_time_ms": 1250,
                    "memory_queries": 3,
                    "tokens_used": 150
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class StreamingChatChunk(BaseModel):
    """Individual chunk in a streaming chat response."""
    
    session_id: UUID = Field(..., description="Session identifier")
    message_id: UUID = Field(..., description="Message identifier")
    chunk_id: int = Field(..., description="Sequential chunk number")
    content: str = Field(..., description="Chunk content")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Chunk metadata")
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }