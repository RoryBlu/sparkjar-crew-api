"""
Context-related data models for conversation and SYNTH management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .chat_models import ChatMessage


class SynthContext(BaseModel):
    """SYNTH identity and configuration context."""
    
    synth_id: UUID = Field(..., description="Unique SYNTH identifier")
    synth_class_id: int = Field(..., description="SYNTH class identifier")
    synth_class_config: Dict[str, Any] = Field(default_factory=dict, description="Base SYNTH class configuration")
    company_customizations: Dict[str, Any] = Field(default_factory=dict, description="Company-level customizations")
    client_policies: Dict[str, Any] = Field(default_factory=dict, description="Client-specific policies and overrides")
    memory_access_scope: List[str] = Field(default_factory=list, description="Memory hierarchy levels accessible to this SYNTH")
    specializations: Optional[Dict[str, Any]] = Field(default=None, description="SYNTH-specific specializations")
    
    @validator('synth_class_id')
    def validate_synth_class_id(cls, v):
        """Validate synth_class_id is positive."""
        if v <= 0:
            raise ValueError("synth_class_id must be a positive integer")
        return v
    
    @validator('memory_access_scope')
    def validate_memory_access_scope(cls, v):
        """Validate memory access scope contains valid hierarchy levels."""
        valid_scopes = ['synth_class', 'company', 'client', 'personal']
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid memory access scope: {scope}. Must be one of {valid_scopes}")
        return v
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "synth_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "synth_class_id": 1,
                "synth_class_config": {
                    "personality": "professional",
                    "expertise_areas": ["project_management", "technical_writing"],
                    "response_style": "detailed"
                },
                "company_customizations": {
                    "brand_voice": "friendly_professional",
                    "terminology_preferences": {"project": "initiative"}
                },
                "client_policies": {
                    "max_response_length": 2000,
                    "enable_memory_consolidation": True
                },
                "memory_access_scope": ["synth_class", "company", "client"],
                "specializations": {
                    "domain_expertise": ["software_development", "agile_methodologies"]
                }
            }
        }


class MemoryEntity(BaseModel):
    """Simplified memory entity for context storage."""
    
    entity_id: UUID = Field(..., description="Unique entity identifier")
    entity_type: str = Field(..., description="Type of memory entity")
    content: str = Field(..., description="Entity content")
    hierarchy_level: str = Field(..., description="Memory hierarchy level")
    relevance_score: Optional[float] = Field(default=None, description="Relevance score for this context")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional entity metadata")
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


class ConversationContext(BaseModel):
    """Complete conversation context for session management."""
    
    session_id: UUID = Field(..., description="Unique session identifier")
    client_user_id: UUID = Field(..., description="Client user identifier")
    actor_type: str = Field(..., description="Actor type (synth)")
    actor_id: UUID = Field(..., description="Specific actor identifier")
    synth_context: SynthContext = Field(..., description="SYNTH configuration and identity context")
    conversation_history: List[ChatMessage] = Field(default_factory=list, description="Complete conversation history")
    active_memory_context: List[MemoryEntity] = Field(default_factory=list, description="Currently active memory entities")
    thinking_session_id: Optional[UUID] = Field(default=None, description="Active sequential thinking session")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the session was created")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    
    @validator('conversation_history')
    def validate_conversation_history_size(cls, v):
        """Validate conversation history doesn't exceed reasonable limits."""
        max_messages = 1000  # Configurable limit
        if len(v) > max_messages:
            raise ValueError(f"Conversation history cannot exceed {max_messages} messages")
        return v
    
    @validator('last_activity')
    def validate_last_activity_not_future(cls, v):
        """Validate last_activity is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("last_activity cannot be in the future")
        return v
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append(message)
        self.last_activity = datetime.utcnow()
    
    def get_recent_messages(self, count: int = 10) -> List[ChatMessage]:
        """Get the most recent messages from the conversation."""
        return self.conversation_history[-count:] if self.conversation_history else []
    
    def update_memory_context(self, entities: List[MemoryEntity]) -> None:
        """Update the active memory context."""
        self.active_memory_context = entities
        self.last_activity = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "session_id": "456e7890-e12b-34d5-a678-901234567def",
                "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "actor_type": "synth",
                "actor_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "synth_context": {
                    "synth_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                    "synth_class_id": 1,
                    "synth_class_config": {},
                    "company_customizations": {},
                    "client_policies": {},
                    "memory_access_scope": ["client"]
                },
                "conversation_history": [],
                "active_memory_context": [],
                "thinking_session_id": None,
                "created_at": "2024-01-15T10:00:00Z",
                "last_activity": "2024-01-15T10:30:00Z",
                "metadata": {
                    "client_version": "1.0.0",
                    "session_type": "interactive"
                }
            }
        }