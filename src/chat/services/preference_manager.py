"""
Preference management using Memory Service.

Stores chat preferences and configurations as memory entities,
leveraging hierarchical resolution for defaults.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from src.chatclients.memory_service import MemoryServiceClient
from src.chatmodels.memory_models import MemoryEntity, Observation
from src.chatmodels.context_models import SynthContext

logger = logging.getLogger(__name__)


class PreferenceManager:
    """Manages chat preferences using Memory Service."""
    
    PREFERENCE_ENTITY_TYPE = "preference"
    CHAT_CONFIG_ENTITY_NAME = "chat_configuration"
    
    def __init__(self, memory_client: MemoryServiceClient):
        """
        Initialize preference manager.
        
        Args:
            memory_client: Memory service client
        """
        self.memory_client = memory_client
        
    async def get_chat_preferences(
        self,
        synth_context: SynthContext
    ) -> Dict[str, Any]:
        """
        Get chat preferences with hierarchical resolution.
        
        Args:
            synth_context: SYNTH context for hierarchy
            
        Returns:
            Dictionary of preferences
        """
        try:
            # Search for preference entity
            memories = await self.memory_client.search_relevant_memories(
                query=self.CHAT_CONFIG_ENTITY_NAME,
                synth_context=synth_context,
                limit=1,
                min_confidence=0.5,
                include_synth_class=True,
                include_client=True
            )
            
            if not memories:
                # Return defaults if no preferences found
                return self._get_default_preferences()
                
            # Parse preferences from observations
            preferences = {}
            for memory in memories:
                for obs in memory.observations:
                    if obs.observation_type == "setting":
                        # Parse "key: value" format
                        parts = obs.content.split(":", 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            preferences[key] = self._parse_value(value)
                            
            return preferences
            
        except Exception as e:
            logger.error(f"Error retrieving preferences: {e}")
            return self._get_default_preferences()
            
    async def set_chat_preference(
        self,
        synth_context: SynthContext,
        key: str,
        value: Any,
        level: str = "synth"  # synth, synth_class, or client
    ) -> bool:
        """
        Set a chat preference.
        
        Args:
            synth_context: SYNTH context
            key: Preference key
            value: Preference value
            level: Hierarchy level to set at
            
        Returns:
            Success status
        """
        try:
            # Create observation for the preference
            observation = Observation(
                observation_type="setting",
                content=f"{key}: {value}",
                confidence=1.0,
                timestamp=datetime.utcnow(),
                metadata={
                    "preference_key": key,
                    "updated_by": "chat_interface",
                    "level": level
                }
            )
            
            # Determine actor based on level
            if level == "client":
                actor_type = "system"
                actor_id = synth_context.client_id
            elif level == "synth_class":
                actor_type = "system"
                actor_id = UUID(int=synth_context.synth_class_id)  # Convert class ID to UUID
            else:  # synth level
                actor_type = "synth"
                actor_id = synth_context.synth_id
                
            # Upsert preference entity
            result = await self.memory_client.upsert_memory_entity(
                entity_type=self.PREFERENCE_ENTITY_TYPE,
                entity_name=self.CHAT_CONFIG_ENTITY_NAME,
                observations=[observation],
                client_user_id=synth_context.client_id,
                actor_type=actor_type,
                actor_id=actor_id
            )
            
            return result.success
            
        except Exception as e:
            logger.error(f"Error setting preference {key}: {e}")
            return False
            
    def _get_default_preferences(self) -> Dict[str, Any]:
        """
        Get default chat preferences.
        
        Returns:
            Default preference dictionary
        """
        return {
            "response_style": "balanced",
            "max_response_length": 1000,
            "include_thinking": True,
            "memory_search_depth": 10,
            "temperature": 0.7,
            "enable_streaming": True,
            "language": "en",
            "timezone": "UTC"
        }
        
    def _parse_value(self, value: str) -> Any:
        """
        Parse string value to appropriate type.
        
        Args:
            value: String value
            
        Returns:
            Parsed value
        """
        # Try to parse as number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
            
        # Check for boolean
        if value.lower() in ["true", "yes", "on"]:
            return True
        elif value.lower() in ["false", "no", "off"]:
            return False
            
        # Return as string
        return value


# Example usage in ConversationManager:
"""
async def process_chat_request(self, request, synth_context):
    # Get preferences
    preferences = await self.preference_manager.get_chat_preferences(synth_context)
    
    # Use preferences
    max_tokens = preferences.get("max_response_length", 1000)
    temperature = preferences.get("temperature", 0.7)
    
    # Generate response with preferences
    response = await self.generate_response(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
"""