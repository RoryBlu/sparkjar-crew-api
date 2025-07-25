"""
Agent Mode Processor for Chat with Memory v1.

KISS principles:
- Passive response only when asked
- Follow procedures from memory exactly
- CLIENT realm always overrides
- Simple task completion logging
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.chat.models import (
    ChatRequestV1,
    ChatResponseV1,
    ChatSessionV1,
    MemorySearchResult
)
from src.chat.services.memory_search_v1 import HierarchicalMemorySearcher

logger = logging.getLogger(__name__)


class AgentModeProcessor:
    """
    Processes chat interactions in agent mode.
    
    Passive helper that follows procedures from memory
    and respects CLIENT policies.
    """
    
    def __init__(
        self,
        memory_searcher: HierarchicalMemorySearcher,
        llm_client: Any  # Will be injected
    ):
        """
        Initialize agent processor.
        
        Args:
            memory_searcher: Hierarchical memory search service
            llm_client: LLM client for response generation
        """
        self.memory_searcher = memory_searcher
        self.llm_client = llm_client
        
    async def process_request(
        self,
        request: ChatRequestV1,
        session: ChatSessionV1,
        client_id: UUID
    ) -> ChatResponseV1:
        """
        Process a chat request in agent mode.
        
        Args:
            request: Incoming chat request
            session: Current session
            client_id: Client UUID for memory access
            
        Returns:
            ChatResponseV1 with task context
        """
        try:
            # 1. Analyze user intent
            intent = self._analyze_intent(request.message)
            
            # 2. Search for relevant procedures and policies
            memory_result = await self._search_task_memories(
                request,
                intent,
                client_id
            )
            
            # 3. Extract procedures and policies
            procedures = self._extract_procedures(memory_result.memories)
            policies = self._extract_client_policies(memory_result.memories)
            
            # 4. Generate task response following procedures
            response_text = await self._generate_task_response(
                request.message,
                procedures,
                policies,
                intent
            )
            
            # 5. Log task completion
            task_summary = self._create_task_summary(
                intent,
                procedures,
                response_text
            )
            
            # Create response
            return ChatResponseV1(
                session_id=session.session_id,
                message_id=UUID(),  # Will be set by API
                message=request.message,
                response=response_text,
                mode_used="agent",
                memory_context_used=[m["entity_name"] for m in memory_result.memories[:10]],
                memory_realms_accessed=memory_result.realms_accessed,
                task_context={
                    "intent": intent,
                    "procedures_followed": [p["name"] for p in procedures[:5]],
                    "policies_applied": [p["name"] for p in policies],
                    "task_summary": task_summary
                },
                relationships_traversed=memory_result.relationships_traversed,
                memory_query_time_ms=memory_result.query_time_ms
            )
            
        except Exception as e:
            logger.error(f"Agent mode processing error: {e}")
            raise
            
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze user intent from message.
        
        KISS: Simple keyword matching, no complex NLP.
        """
        message_lower = message.lower()
        
        # Task type detection
        task_type = "general"
        if any(word in message_lower for word in ["how to", "how do i", "steps to"]):
            task_type = "procedure"
        elif any(word in message_lower for word in ["fix", "error", "problem", "issue"]):
            task_type = "troubleshooting"
        elif any(word in message_lower for word in ["what is", "explain", "definition"]):
            task_type = "information"
        elif any(word in message_lower for word in ["create", "make", "build", "generate"]):
            task_type = "creation"
        elif any(word in message_lower for word in ["find", "search", "locate", "where"]):
            task_type = "search"
            
        # Action detection
        action = None
        action_verbs = ["create", "update", "delete", "find", "fix", "explain", "show", "list"]
        for verb in action_verbs:
            if verb in message_lower:
                action = verb
                break
                
        # Entity extraction (very basic)
        entities = []
        # Look for quoted strings
        import re
        quoted = re.findall(r'"([^"]+)"', message)
        entities.extend(quoted)
        
        return {
            "task_type": task_type,
            "action": action,
            "entities": entities,
            "original_message": message
        }
        
    async def _search_task_memories(
        self,
        request: ChatRequestV1,
        intent: Dict[str, Any],
        client_id: UUID
    ) -> MemorySearchResult:
        """
        Search for task-relevant procedures and policies.
        
        Focuses on procedures and CLIENT policies.
        """
        # Enhance query based on intent
        enhanced_query = request.message
        
        if intent["task_type"] == "procedure":
            enhanced_query = f"procedure SOP steps: {request.message}"
        elif intent["task_type"] == "troubleshooting":
            enhanced_query = f"troubleshooting fix solution: {request.message}"
            
        # Create modified request
        search_request = ChatRequestV1(
            **request.dict(exclude={"message"}),
            message=enhanced_query
        )
        
        return await self.memory_searcher.search_with_precedence(
            search_request,
            client_id
        )
        
    def _extract_procedures(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract procedures from memories.
        
        KISS: Look for procedure-type entities.
        """
        procedures = []
        
        for memory in memories:
            entity_type = memory.get("entity", {}).get("type", "")
            entity_name = memory.get("entity_name", "")
            
            # Check if it's a procedure
            if any(t in entity_type.lower() for t in ["procedure", "sop", "guide", "steps"]):
                # Extract steps from observations
                steps = []
                for obs in memory.get("observations", []):
                    if obs.get("type") in ["step", "instruction", "procedure_step"]:
                        steps.append(obs.get("value", ""))
                        
                procedures.append({
                    "name": entity_name,
                    "type": entity_type,
                    "steps": steps,
                    "metadata": memory.get("metadata", {})
                })
                
        return procedures
        
    def _extract_client_policies(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract CLIENT realm policies.
        
        These override everything else.
        """
        policies = []
        
        for memory in memories:
            # Check if from CLIENT realm
            hierarchy = memory.get("metadata", {}).get("hierarchy_level", "")
            if hierarchy == "client":
                entity_type = memory.get("entity", {}).get("type", "")
                
                # Check if it's a policy
                if any(t in entity_type.lower() for t in ["policy", "rule", "requirement"]):
                    policies.append({
                        "name": memory.get("entity_name", ""),
                        "type": entity_type,
                        "rules": self._extract_rules(memory),
                        "priority": "override"  # CLIENT always overrides
                    })
                    
        return policies
        
    def _extract_rules(self, memory: Dict[str, Any]) -> List[str]:
        """Extract rules from policy memory."""
        rules = []
        
        for obs in memory.get("observations", []):
            if obs.get("type") in ["rule", "requirement", "policy"]:
                value = obs.get("value", "")
                if isinstance(value, dict):
                    rules.append(value.get("content", str(value)))
                else:
                    rules.append(str(value))
                    
        return rules
        
    async def _generate_task_response(
        self,
        message: str,
        procedures: List[Dict[str, Any]],
        policies: List[Dict[str, Any]],
        intent: Dict[str, Any]
    ) -> str:
        """
        Generate response following procedures and policies.
        
        KISS: Direct response, no creativity.
        """
        # Build context
        procedure_context = self._build_procedure_context(procedures)
        policy_context = self._build_policy_context(policies)
        
        # Different prompts based on task type
        if intent["task_type"] == "procedure" and procedures:
            prompt = f"""User asked: {message}

Follow these procedures exactly:
{procedure_context}

Apply these policies:
{policy_context}

Provide step-by-step instructions based on the procedures. Be direct and actionable."""

        elif intent["task_type"] == "troubleshooting":
            prompt = f"""User reported issue: {message}

Available solutions:
{procedure_context}

Policies to follow:
{policy_context}

Provide troubleshooting steps. Be direct and systematic."""

        else:
            prompt = f"""User request: {message}

Relevant information:
{procedure_context}

Policies to follow:
{policy_context}

Provide a direct, helpful response."""

        # In production, this would call the LLM service
        # For now, return a structured response
        if procedures:
            response = f"Based on the procedure '{procedures[0]['name']}', here are the steps:\n\n"
            for i, step in enumerate(procedures[0].get("steps", [])[:5], 1):
                response += f"{i}. {step}\n"
        else:
            response = f"I'll help you with: {intent['action']} {' '.join(intent['entities'])}"
            
        # Apply policies
        if policies:
            response += f"\n\nNote: Following company policy '{policies[0]['name']}'"
            
        return response
        
    def _create_task_summary(
        self,
        intent: Dict[str, Any],
        procedures: List[Dict[str, Any]],
        response: str
    ) -> Dict[str, Any]:
        """
        Create task completion summary for logging.
        
        This helps with learning what works.
        """
        return {
            "task_type": intent["task_type"],
            "action_taken": intent.get("action", "responded"),
            "procedures_used": len(procedures),
            "response_length": len(response),
            "entities_involved": intent.get("entities", [])
        }
        
    def _build_procedure_context(
        self,
        procedures: List[Dict[str, Any]]
    ) -> str:
        """Build context from procedures."""
        if not procedures:
            return "No specific procedures found."
            
        context_parts = []
        for proc in procedures[:3]:  # Limit to top 3
            context_parts.append(f"\nProcedure: {proc['name']}")
            for i, step in enumerate(proc.get("steps", [])[:5], 1):
                context_parts.append(f"  {i}. {step}")
                
        return "\n".join(context_parts)
        
    def _build_policy_context(
        self,
        policies: List[Dict[str, Any]]
    ) -> str:
        """Build context from policies."""
        if not policies:
            return "No specific policies apply."
            
        context_parts = []
        for policy in policies:
            context_parts.append(f"\nPolicy: {policy['name']} (CLIENT override)")
            for rule in policy.get("rules", [])[:3]:
                context_parts.append(f"  - {rule}")
                
        return "\n".join(context_parts)