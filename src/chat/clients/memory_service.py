"""
Memory Service client for chat interface integration.

This client provides methods to interact with the memory service for
entity search, retrieval, and UPSERT operations with hierarchical
SYNTH context resolution.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

import httpx
from httpx import AsyncClient, HTTPStatusError, ConnectError, TimeoutException

from src.chat.models.context_models import SynthContext
from src.chat.models.memory_models import MemoryEntity, Observation
from src.chat.config import get_settings

logger = logging.getLogger(__name__)


class MemoryServiceError(Exception):
    """Base exception for memory service errors."""
    pass


class MemoryServiceClient:
    """Client for interacting with the memory service."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize memory service client.
        
        Args:
            base_url: Override base URL for memory service
        """
        settings = get_settings()
        self.base_url = base_url or settings.memory_service_url
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.max_retries = 3
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        client_id: Optional[UUID] = None,
        actor_type: Optional[str] = None,
        actor_id: Optional[UUID] = None
    ) -> Any:
        """
        Make an HTTP request to the memory service with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: Request body
            params: Query parameters
            client_id: Client user ID for context
            actor_type: Actor type (synth, human, etc.)
            actor_id: Actor ID
            
        Returns:
            Response data
            
        Raises:
            MemoryServiceError: On API errors
        """
        # For internal memory service, we don't need auth but need context params
        if params is None:
            params = {}
            
        # Add context parameters for internal API
        if client_id:
            params["client_user_id"] = str(client_id)
        if actor_type:
            params["actor_type"] = actor_type
        if actor_id:
            params["actor_id"] = str(actor_id)
            
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=json_data,
                        params=params
                    )
                    response.raise_for_status()
                    return response.json()
                    
            except ConnectError as e:
                logger.error(f"Failed to connect to memory service: {e}")
                if attempt == self.max_retries - 1:
                    raise MemoryServiceError(f"Memory service unavailable: {e}")
                    
            except TimeoutException as e:
                logger.error(f"Memory service request timed out: {e}")
                if attempt == self.max_retries - 1:
                    raise MemoryServiceError(f"Memory service timeout: {e}")
                    
            except HTTPStatusError as e:
                logger.error(f"Memory service returned error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    continue  # Retry on server errors
                raise MemoryServiceError(f"Memory service error: {e.response.text}")
                
            except Exception as e:
                logger.error(f"Unexpected error calling memory service: {e}")
                raise MemoryServiceError(f"Unexpected error: {e}")
                
    async def search_relevant_memories(
        self,
        query: str,
        synth_context: SynthContext,
        limit: int = 10,
        min_confidence: float = 0.7,
        include_synth_class: bool = True,
        include_client: bool = True
    ) -> List[MemoryEntity]:
        """
        Search for relevant memories with hierarchical context.
        
        This method searches across the SYNTH hierarchy:
        - Individual SYNTH memories
        - SYNTH class memories (if include_synth_class=True)
        - Client-level memories (if include_client=True)
        
        Args:
            query: Natural language search query
            synth_context: SYNTH context with hierarchy information
            limit: Maximum results to return
            min_confidence: Minimum similarity confidence (0-1)
            include_synth_class: Include SYNTH class memories
            include_client: Include client-level memories
            
        Returns:
            List of memory entities sorted by relevance and hierarchy
        """
        try:
            # Prepare search request
            search_data = {
                "query": query,
                "limit": limit,
                "min_confidence": min_confidence
            }
            
            # Add entity type filtering based on hierarchy scope
            entity_types = []
            if synth_context.memory_access_scope:
                entity_types.extend(synth_context.memory_access_scope)
            
            if entity_types:
                search_data["entity_types"] = entity_types
                
            # Perform search with SYNTH context
            results = await self._make_request(
                method="POST",
                endpoint="/memory/search",
                json_data=search_data,
                client_id=synth_context.client_id,
                actor_type="synth",
                actor_id=synth_context.synth_id
            )
            
            # Convert to MemoryEntity objects
            memories = []
            for result in results:
                memories.append(MemoryEntity(**result))
                
            # Apply hierarchy layering and conflict resolution
            memories = self._apply_hierarchy_precedence(memories, synth_context)
            
            logger.info(f"Found {len(memories)} relevant memories for query: {query}")
            return memories
            
        except MemoryServiceError:
            raise
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            raise MemoryServiceError(f"Failed to search memories: {e}")
            
    async def get_entities_by_names(
        self,
        names: List[str],
        synth_context: SynthContext
    ) -> List[MemoryEntity]:
        """
        Retrieve specific entities by exact name match.
        
        Args:
            names: List of entity names to retrieve
            synth_context: SYNTH context for access control
            
        Returns:
            List of memory entities
        """
        try:
            request_data = {"names": names}
            
            results = await self._make_request(
                method="POST",
                endpoint="/memory/nodes",
                json_data=request_data,
                client_id=synth_context.client_id,
                actor_type="synth",
                actor_id=synth_context.synth_id
            )
            
            entities = []
            for result in results:
                entities.append(MemoryEntity(**result))
                
            return entities
            
        except MemoryServiceError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving entities: {e}")
            raise MemoryServiceError(f"Failed to retrieve entities: {e}")
            
    async def upsert_entities(
        self,
        entities: List[Dict[str, Any]],
        synth_context: SynthContext
    ) -> List[MemoryEntity]:
        """
        Create or update memory entities.
        
        Args:
            entities: List of entity data to upsert
            synth_context: SYNTH context for ownership
            
        Returns:
            List of created/updated entities
        """
        try:
            results = await self._make_request(
                method="POST",
                endpoint="/memory/entities",
                json_data=entities,
                client_id=synth_context.client_id,
                actor_type="synth",
                actor_id=synth_context.synth_id
            )
            
            upserted = []
            for result in results:
                upserted.append(MemoryEntity(**result))
                
            logger.info(f"Upserted {len(upserted)} entities")
            return upserted
            
        except MemoryServiceError:
            raise
        except Exception as e:
            logger.error(f"Error upserting entities: {e}")
            raise MemoryServiceError(f"Failed to upsert entities: {e}")
            
    async def resolve_synth_context(
        self,
        actor_id: UUID,
        client_id: UUID
    ) -> Optional[SynthContext]:
        """
        Resolve full SYNTH context by querying memory service.
        
        This retrieves:
        - SYNTH entity details
        - SYNTH class configuration
        - Company customizations
        - Client policies
        
        Args:
            actor_id: SYNTH ID
            client_id: Client user ID
            
        Returns:
            Resolved SYNTH context or None if not found
        """
        try:
            # Get SYNTH entity details
            synth_entities = await self.get_entities_by_names(
                names=[str(actor_id)],
                synth_context=SynthContext(
                    synth_id=actor_id,
                    synth_class_id=0,  # Will be resolved
                    client_id=client_id,
                    synth_class_config={},
                    company_customizations={},
                    client_policies={},
                    memory_access_scope=[]
                )
            )
            
            if not synth_entities:
                logger.warning(f"SYNTH {actor_id} not found in memory service")
                return None
                
            synth_entity = synth_entities[0]
            
            # Extract SYNTH class ID from metadata
            synth_class_id = synth_entity.metadata.get("synth_class_id", 0)
            
            # TODO: Query for synth_class config, company customizations, and client policies
            # This would require additional endpoints or a dedicated context resolution endpoint
            
            return SynthContext(
                synth_id=actor_id,
                synth_class_id=synth_class_id,
                client_id=client_id,
                synth_class_config=synth_entity.metadata.get("synth_class_config", {}),
                company_customizations=synth_entity.metadata.get("company_customizations", {}),
                client_policies=synth_entity.metadata.get("client_policies", {}),
                memory_access_scope=synth_entity.metadata.get("memory_access_scope", [])
            )
            
        except Exception as e:
            logger.error(f"Error resolving SYNTH context: {e}")
            return None
            
    def _apply_hierarchy_precedence(
        self,
        memories: List[MemoryEntity],
        synth_context: SynthContext
    ) -> List[MemoryEntity]:
        """
        Apply hierarchy precedence rules to memory results.
        
        Hierarchy (highest to lowest precedence):
        1. Client-level memories
        2. Company customizations
        3. SYNTH class memories
        4. Individual SYNTH memories
        
        Args:
            memories: Raw memory search results
            synth_context: SYNTH context with hierarchy info
            
        Returns:
            Memories sorted by precedence with conflicts resolved
        """
        # Group memories by hierarchy level
        client_memories = []
        company_memories = []
        class_memories = []
        synth_memories = []
        
        for memory in memories:
            # Determine hierarchy level from metadata
            if memory.metadata.get("hierarchy_level") == "client":
                client_memories.append(memory)
            elif memory.metadata.get("hierarchy_level") == "company":
                company_memories.append(memory)
            elif memory.metadata.get("hierarchy_level") == "synth_class":
                class_memories.append(memory)
            else:
                synth_memories.append(memory)
                
        # Combine in precedence order
        layered_memories = (
            client_memories +
            company_memories +
            class_memories +
            synth_memories
        )
        
        # Remove duplicates keeping highest precedence
        seen_entities = set()
        deduplicated = []
        
        for memory in layered_memories:
            if memory.entity_name not in seen_entities:
                seen_entities.add(memory.entity_name)
                deduplicated.append(memory)
                
        return deduplicated
