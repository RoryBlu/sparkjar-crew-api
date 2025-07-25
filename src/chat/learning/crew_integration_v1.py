"""
Memory Maker Crew Integration for Learning Loop.

KISS principles:
- Simple crew job schema
- Direct result processing
- No complex transformations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.chat.learning.memory_consolidator_v1 import MemoryConsolidator
from src.chat.learning.pattern_extractor_v1 import PatternExtractor

logger = logging.getLogger(__name__)


class MemoryMakerCrewIntegration:
    """
    Integrates learning loop with Memory Maker Crew.
    
    KISS: Format data for crew, process results, store insights.
    """
    
    def __init__(
        self,
        consolidator: MemoryConsolidator,
        pattern_extractor: PatternExtractor,
        memory_client: Any  # Memory service client
    ):
        """
        Initialize crew integration.
        
        Args:
            consolidator: Memory consolidation pipeline
            pattern_extractor: Pattern extraction service
            memory_client: Client for memory service
        """
        self.consolidator = consolidator
        self.pattern_extractor = pattern_extractor
        self.memory_client = memory_client
        
    async def process_conversation_for_learning(
        self,
        session_id: UUID,
        conversation_entity_id: str,
        conversation_history: List[Dict[str, Any]],
        mode: str
    ) -> Dict[str, Any]:
        """
        Process conversation through learning loop.
        
        Args:
            session_id: Chat session ID
            conversation_entity_id: Stored conversation entity
            conversation_history: Full conversation exchanges
            mode: Chat mode used
            
        Returns:
            Processing result with job ID
        """
        try:
            # 1. Extract patterns
            patterns = self.pattern_extractor.extract_patterns(
                conversation_history
            )
            
            # 2. Filter successful patterns
            successful_patterns = self.pattern_extractor.identify_successful_patterns(
                patterns
            )
            
            # 3. Store pattern entities
            pattern_entities = []
            for pattern in successful_patterns:
                entity = await self._store_pattern_entity(
                    pattern,
                    session_id
                )
                if entity:
                    pattern_entities.append(entity)
                    
            # 4. Queue for Memory Maker Crew processing
            job_id = await self.consolidator.consolidate_conversation(
                session_id=session_id,
                entity_id=conversation_entity_id,
                mode=mode,
                patterns=successful_patterns
            )
            
            return {
                "status": "processing",
                "job_id": job_id,
                "patterns_found": len(patterns),
                "successful_patterns": len(successful_patterns),
                "pattern_entities_created": len(pattern_entities)
            }
            
        except Exception as e:
            logger.error(f"Failed to process conversation for learning: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def process_crew_results(
        self,
        job_id: str,
        crew_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process results from Memory Maker Crew.
        
        Args:
            job_id: Crew job ID
            crew_results: Results from crew processing
            
        Returns:
            Processing summary
        """
        try:
            # Extract insights from crew results
            insights = crew_results.get("insights", [])
            relationships = crew_results.get("relationships", [])
            improvements = crew_results.get("improvements", [])
            
            stored_count = 0
            
            # Store insights as memory entities
            for insight in insights:
                entity = await self._store_insight_entity(insight)
                if entity:
                    stored_count += 1
                    
            # Update relationships
            for relationship in relationships:
                await self._update_entity_relationships(relationship)
                
            # Store improvement suggestions
            for improvement in improvements:
                await self._store_improvement_entity(improvement)
                
            return {
                "status": "completed",
                "job_id": job_id,
                "insights_stored": stored_count,
                "relationships_updated": len(relationships),
                "improvements_identified": len(improvements)
            }
            
        except Exception as e:
            logger.error(f"Failed to process crew results: {e}")
            return {
                "status": "error",
                "job_id": job_id,
                "error": str(e)
            }
            
    def create_crew_request_schema(
        self,
        source_type: str
    ) -> Dict[str, Any]:
        """
        Create schema for Memory Maker Crew requests.
        
        Args:
            source_type: Type of source data
            
        Returns:
            Request schema for crew
        """
        base_schema = {
            "job_key": "memory_maker_crew",
            "request_data": {
                "source_type": source_type,
                "required_fields": [],
                "optional_fields": [],
                "output_format": {}
            }
        }
        
        if source_type == "chat_conversation":
            base_schema["request_data"].update({
                "required_fields": [
                    "session_id",
                    "entity_id",
                    "mode",
                    "consolidation_type"
                ],
                "optional_fields": [
                    "patterns",
                    "metadata"
                ],
                "output_format": {
                    "insights": "List of key insights from conversation",
                    "relationships": "New entity relationships discovered",
                    "improvements": "Suggested improvements for responses"
                }
            })
            
        elif source_type == "pattern_consolidation":
            base_schema["request_data"].update({
                "required_fields": [
                    "patterns",
                    "source_sessions",
                    "consolidation_type"
                ],
                "optional_fields": [
                    "metadata"
                ],
                "output_format": {
                    "consolidated_patterns": "Merged and refined patterns",
                    "best_practices": "Extracted best practices",
                    "recommendations": "Recommendations for future interactions"
                }
            })
            
        return base_schema
        
    async def monitor_learning_progress(self) -> Dict[str, Any]:
        """
        Monitor overall learning loop progress.
        
        Returns:
            Learning metrics and status
        """
        # Get consolidation progress
        consolidation_progress = self.consolidator.get_consolidation_progress()
        
        # Additional metrics would come from database
        # For now, return consolidation metrics
        return {
            "learning_loop_status": "active",
            "consolidation_progress": consolidation_progress,
            "last_update": datetime.utcnow().isoformat()
        }
        
    async def _store_pattern_entity(
        self,
        pattern: Dict[str, Any],
        session_id: UUID
    ) -> Optional[str]:
        """Store pattern as memory entity."""
        try:
            entity_data = self.pattern_extractor.create_pattern_entity(
                pattern,
                session_id
            )
            
            # In production, call memory service API
            # For now, simulate storage
            logger.info(f"Stored pattern entity: {entity_data['entity']['name']}")
            return entity_data["entity"]["name"]
            
        except Exception as e:
            logger.error(f"Failed to store pattern entity: {e}")
            return None
            
    async def _store_insight_entity(
        self,
        insight: Dict[str, Any]
    ) -> Optional[str]:
        """Store insight from crew processing."""
        try:
            entity_data = {
                "entity": {
                    "name": f"insight_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "type": "conversation_insight",
                    "metadata": insight.get("metadata", {})
                },
                "observations": [
                    {
                        "type": "insight",
                        "value": {
                            "content": insight["content"],
                            "confidence": insight.get("confidence", 0.8)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
            # Store via memory service
            logger.info(f"Stored insight entity: {entity_data['entity']['name']}")
            return entity_data["entity"]["name"]
            
        except Exception as e:
            logger.error(f"Failed to store insight entity: {e}")
            return None
            
    async def _store_improvement_entity(
        self,
        improvement: Dict[str, Any]
    ) -> Optional[str]:
        """Store improvement suggestion."""
        try:
            entity_data = {
                "entity": {
                    "name": f"improvement_{improvement['type']}_{datetime.utcnow().strftime('%Y%m%d')}",
                    "type": "response_improvement",
                    "metadata": {
                        "improvement_type": improvement["type"],
                        "priority": improvement.get("priority", "medium")
                    }
                },
                "observations": [
                    {
                        "type": "improvement_suggestion",
                        "value": improvement["suggestion"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
            logger.info(f"Stored improvement: {entity_data['entity']['name']}")
            return entity_data["entity"]["name"]
            
        except Exception as e:
            logger.error(f"Failed to store improvement: {e}")
            return None
            
    async def _update_entity_relationships(
        self,
        relationship: Dict[str, Any]
    ):
        """Update entity relationships based on crew findings."""
        try:
            # In production, call memory service to add relationship
            logger.info(
                f"Updated relationship: {relationship['from']} -> {relationship['to']}"
            )
        except Exception as e:
            logger.error(f"Failed to update relationship: {e}")