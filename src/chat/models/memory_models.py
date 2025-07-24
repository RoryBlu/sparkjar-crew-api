"""
Memory-related data models for conversation consolidation and extraction.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .chat_models import ChatMessage


class MemoryConsolidationRequest(BaseModel):
    """Request model for memory consolidation via Memory Maker Crew."""
    
    client_user_id: UUID = Field(..., description="Client user identifier")
    actor_type: str = Field(..., description="Actor type (synth)")
    actor_id: UUID = Field(..., description="Specific actor identifier")
    conversation_data: List[ChatMessage] = Field(..., description="Conversation messages to consolidate")
    context_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context for consolidation")
    consolidation_type: str = Field(default="conversation", description="Type of consolidation being performed")
    priority: int = Field(default=5, ge=1, le=10, description="Consolidation priority (1=highest, 10=lowest)")
    
    @validator('conversation_data')
    def validate_conversation_data_not_empty(cls, v):
        """Validate that conversation data is not empty."""
        if not v:
            raise ValueError("conversation_data cannot be empty")
        return v
    
    @validator('actor_type')
    def validate_actor_type(cls, v):
        """Validate actor_type is supported."""
        if v != "synth":
            raise ValueError("Only 'synth' actor_type is currently supported")
        return v
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "actor_type": "synth",
                "actor_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "conversation_data": [
                    {
                        "message_id": "msg-001",
                        "session_id": "session-001",
                        "role": "user",
                        "content": "What's the status of Project Alpha?",
                        "timestamp": "2024-01-15T10:00:00Z"
                    },
                    {
                        "message_id": "msg-002", 
                        "session_id": "session-001",
                        "role": "assistant",
                        "content": "Project Alpha is currently in the testing phase...",
                        "timestamp": "2024-01-15T10:00:30Z"
                    }
                ],
                "context_metadata": {
                    "session_duration_minutes": 15,
                    "total_messages": 8,
                    "topics_discussed": ["project_status", "timeline", "resources"]
                },
                "consolidation_type": "conversation",
                "priority": 5
            }
        }


class ExtractedEntity(BaseModel):
    """Individual entity extracted from conversation."""
    
    entity_type: str = Field(..., description="Type of entity (person, project, skill, etc.)")
    entity_name: str = Field(..., description="Name or identifier of the entity")
    entity_content: str = Field(..., description="Detailed content about the entity")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in extraction accuracy")
    source_messages: List[UUID] = Field(default_factory=list, description="Message IDs that contributed to this entity")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional entity metadata")
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


class ExtractedObservation(BaseModel):
    """Individual observation extracted from conversation."""
    
    observation_type: str = Field(..., description="Type of observation (skill_assessment, preference, fact, etc.)")
    observation_content: str = Field(..., description="Content of the observation")
    related_entity_id: Optional[UUID] = Field(default=None, description="Related entity if applicable")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in observation accuracy")
    source_messages: List[UUID] = Field(default_factory=list, description="Message IDs that contributed to this observation")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional observation metadata")
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


class ExtractedRelationship(BaseModel):
    """Individual relationship extracted from conversation."""
    
    relationship_type: str = Field(..., description="Type of relationship (works_with, manages, collaborates_on, etc.)")
    source_entity_id: UUID = Field(..., description="Source entity in the relationship")
    target_entity_id: UUID = Field(..., description="Target entity in the relationship")
    relationship_strength: float = Field(..., ge=0.0, le=1.0, description="Strength of the relationship")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in relationship accuracy")
    source_messages: List[UUID] = Field(default_factory=list, description="Message IDs that contributed to this relationship")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional relationship metadata")
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


class MemoryExtractionResult(BaseModel):
    """Result model for memory extraction and consolidation."""
    
    consolidation_id: UUID = Field(..., description="Unique identifier for this consolidation operation")
    client_user_id: UUID = Field(..., description="Client user identifier")
    actor_type: str = Field(..., description="Actor type")
    actor_id: UUID = Field(..., description="Actor identifier")
    entities_created: List[ExtractedEntity] = Field(default_factory=list, description="New entities created")
    entities_updated: List[ExtractedEntity] = Field(default_factory=list, description="Existing entities updated")
    observations_added: List[ExtractedObservation] = Field(default_factory=list, description="New observations added")
    relationships_created: List[ExtractedRelationship] = Field(default_factory=list, description="New relationships created")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the extraction process")
    processing_time_seconds: Optional[float] = Field(default=None, description="Time taken to process the consolidation")
    success: bool = Field(default=True, description="Whether the consolidation was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if consolidation failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the consolidation was completed")
    
    @validator('entities_created', 'entities_updated')
    def validate_entities_have_content(cls, v):
        """Validate that entities have meaningful content."""
        for entity in v:
            if not entity.entity_content.strip():
                raise ValueError("Entity content cannot be empty")
        return v
    
    @validator('observations_added')
    def validate_observations_have_content(cls, v):
        """Validate that observations have meaningful content."""
        for observation in v:
            if not observation.observation_content.strip():
                raise ValueError("Observation content cannot be empty")
        return v
    
    def get_total_extractions(self) -> int:
        """Get total number of items extracted."""
        return (
            len(self.entities_created) + 
            len(self.entities_updated) + 
            len(self.observations_added) + 
            len(self.relationships_created)
        )
    
    def is_successful(self) -> bool:
        """Check if the consolidation was successful."""
        return self.success and self.error_message is None
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "consolidation_id": "consolidation-123",
                "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "actor_type": "synth",
                "actor_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "entities_created": [
                    {
                        "entity_type": "project",
                        "entity_name": "Project Alpha",
                        "entity_content": "Software development project in testing phase",
                        "confidence_score": 0.95,
                        "source_messages": ["msg-001", "msg-002"]
                    }
                ],
                "entities_updated": [],
                "observations_added": [
                    {
                        "observation_type": "project_status",
                        "observation_content": "Project Alpha is currently in testing phase",
                        "confidence_score": 0.90,
                        "source_messages": ["msg-002"]
                    }
                ],
                "relationships_created": [],
                "extraction_metadata": {
                    "messages_processed": 8,
                    "extraction_method": "llm_analysis",
                    "model_version": "1.0"
                },
                "processing_time_seconds": 2.5,
                "success": True,
                "error_message": None,
                "created_at": "2024-01-15T10:35:00Z"
            }
        }