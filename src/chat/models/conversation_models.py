"""
Conversation memory entity models.

KISS: Simple models for storing conversations in memory service.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ConversationObservation(BaseModel):
    """Single observation about a conversation exchange."""
    
    type: str = "message_exchange"
    value: Dict[str, Any] = Field(
        ...,
        description="Exchange details: user_message, synth_response, mode, context"
    )
    source: str = "chat_service"
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('value')
    def validate_exchange_structure(cls, v):
        """Ensure basic exchange structure is present."""
        required_keys = {"user_message", "synth_response", "mode"}
        if not all(key in v for key in required_keys):
            raise ValueError(f"Exchange must have keys: {required_keys}")
        return v


class ConversationRelationship(BaseModel):
    """Relationship from conversation to other entities."""
    
    type: Literal["references", "discusses", "implements", "questions"]
    direction: Literal["outgoing"] = "outgoing"  # Conversations only have outgoing
    to_entity: str = Field(..., description="Entity name being referenced")
    to_realm: Dict[str, str] = Field(
        ...,
        description="Target realm (actor_type and actor_id)"
    )
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('to_entity')
    def validate_entity_name(cls, v):
        """Entity names should be short keys."""
        if len(v) > 50:
            raise ValueError("Entity name too long - use short keys")
        return v


class ConversationEntity(BaseModel):
    """Entity structure for storing conversations in memory service."""
    
    # Actor context - who owns this conversation
    actor_type: str = "synth"
    actor_id: str
    
    # Entity details
    entity: Dict[str, Any] = Field(
        ...,
        description="Entity name, type, and metadata"
    )
    
    # Observations about the conversation
    observations: List[ConversationObservation]
    
    # Relationships to other entities discussed
    relationships: List[ConversationRelationship] = Field(
        default_factory=list,
        description="Links to topics, procedures, entities discussed"
    )
    
    @validator('entity')
    def validate_entity_structure(cls, v):
        """Ensure entity has required fields and proper naming."""
        if "name" not in v:
            raise ValueError("Entity must have a name")
        
        # Enforce naming convention: conv_<session_id_prefix>_<timestamp>
        name = v["name"]
        if not name.startswith("conv_"):
            raise ValueError("Conversation entities must start with 'conv_'")
        
        if "type" not in v:
            v["type"] = "conversation"
        
        return v
    
    @validator('observations')
    def limit_observations(cls, v):
        """Keep observations reasonable - summarize if needed."""
        if len(v) > 50:
            # In practice, you'd summarize here
            raise ValueError("Too many observations - summarize the conversation")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "actor_type": "synth",
                "actor_id": "987fcdeb-51a2-43d7-8f9e-123456789abc",
                "entity": {
                    "name": "conv_456e7890_1705320600",
                    "type": "conversation",
                    "metadata": {
                        "session_id": "456e7890-e12b-34d5-a678-901234567def",
                        "mode": "tutor",
                        "participant": "123e4567-e89b-12d3-a456-426614174000",
                        "topic": "database optimization",
                        "duration_ms": 45000
                    }
                },
                "observations": [
                    {
                        "type": "message_exchange",
                        "value": {
                            "user_message": "How do I optimize database queries?",
                            "synth_response": "Let's start with understanding indexes...",
                            "mode": "tutor",
                            "memories_used": ["database_optimization", "index_strategies"]
                        },
                        "source": "chat_service",
                        "confidence": 1.0
                    }
                ],
                "relationships": [
                    {
                        "type": "discusses",
                        "to_entity": "database_optimization",
                        "to_realm": {"actor_type": "synth_class", "actor_id": "24"},
                        "metadata": {"relevance": "high"}
                    }
                ]
            }
        }


def create_conversation_entity(
    session_id: UUID,
    actor_id: str,
    mode: str,
    participant_id: UUID,
    message: str,
    response: str,
    memories_used: List[str],
    topic: Optional[str] = None
) -> ConversationEntity:
    """
    Helper to create a conversation entity with proper structure.
    
    KISS: Simple factory function instead of complex builders.
    """
    timestamp = int(datetime.utcnow().timestamp())
    entity_name = f"conv_{str(session_id)[:8]}_{timestamp}"
    
    return ConversationEntity(
        actor_type="synth",
        actor_id=actor_id,
        entity={
            "name": entity_name,
            "type": "conversation",
            "metadata": {
                "session_id": str(session_id),
                "mode": mode,
                "participant": str(participant_id),
                "topic": topic or "general",
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        observations=[
            ConversationObservation(
                value={
                    "user_message": message[:500],  # Truncate for storage
                    "synth_response": response[:500],
                    "mode": mode,
                    "memories_used": memories_used[:10]  # Top 10
                }
            )
        ],
        relationships=[
            ConversationRelationship(
                type="references",
                to_entity=memory,
                to_realm={"actor_type": "synth", "actor_id": actor_id}
            )
            for memory in memories_used[:5]  # Top 5 relationships
        ]
    )