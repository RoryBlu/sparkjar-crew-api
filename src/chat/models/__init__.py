"""
Data models for the Chat Interface service.
"""

from .chat_models import ChatRequest, ChatResponse, ChatMessage
from .chat_models_v1 import ChatRequestV1, ChatResponseV1, ChatSessionV1
from .context_models import ConversationContext, SynthContext
from .memory_models import MemoryConsolidationRequest, MemoryExtractionResult
from .conversation_models import ConversationEntity, ConversationObservation, ConversationRelationship, create_conversation_entity

__all__ = [
    # Original models
    "ChatRequest",
    "ChatResponse", 
    "ChatMessage",
    # V1 models with memory integration
    "ChatRequestV1",
    "ChatResponseV1",
    "ChatSessionV1",
    # Context models
    "ConversationContext",
    "SynthContext",
    # Memory models
    "MemoryConsolidationRequest",
    "MemoryExtractionResult",
    # Conversation storage
    "ConversationEntity",
    "ConversationObservation", 
    "ConversationRelationship",
    "create_conversation_entity",
]