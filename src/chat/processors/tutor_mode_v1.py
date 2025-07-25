"""
Tutor Mode Processor for Chat with Memory v1.

KISS principles:
- Simple understanding assessment based on message patterns
- Use memory content to guide learning
- Progressive difficulty through topic depth
- No complex NLP or ML models
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from src.chat.models import (
    ChatRequestV1,
    ChatResponseV1,
    ChatSessionV1,
    MemorySearchResult
)
from src.chat.services.memory_search_v1 import HierarchicalMemorySearcher

logger = logging.getLogger(__name__)


class TutorModeProcessor:
    """
    Processes chat interactions in tutor mode.
    
    Proactively guides learning based on user understanding
    and available memory content.
    """
    
    def __init__(
        self,
        memory_searcher: HierarchicalMemorySearcher,
        llm_client: Any  # Will be injected
    ):
        """
        Initialize tutor processor.
        
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
        Process a chat request in tutor mode.
        
        Args:
            request: Incoming chat request
            session: Current session with learning state
            client_id: Client UUID for memory access
            
        Returns:
            ChatResponseV1 with learning metadata
        """
        try:
            # 1. Assess understanding from message
            understanding_level = self._assess_understanding(
                request.message,
                session.understanding_level
            )
            
            # 2. Search for relevant educational content
            memory_result = await self._search_educational_content(
                request, 
                session,
                client_id
            )
            
            # 3. Determine learning objective
            objective = self._determine_learning_objective(
                request.message,
                session.learning_topic,
                memory_result.memories
            )
            
            # 4. Generate progressive response
            response_text = await self._generate_progressive_response(
                request.message,
                memory_result.memories,
                understanding_level,
                objective
            )
            
            # 5. Generate follow-up questions
            follow_up = self._generate_follow_up_questions(
                objective,
                understanding_level,
                memory_result.memories
            )
            
            # 6. Suggest next topics
            next_topics = self._suggest_next_topics(
                session.learning_topic,
                memory_result.memories,
                understanding_level
            )
            
            # 7. Build learning path
            learning_path = self._build_learning_path(
                session.learning_path or [],
                objective
            )
            
            # Create response
            return ChatResponseV1(
                session_id=session.session_id,
                message_id=UUID(),  # Will be set by API
                message=request.message,
                response=response_text,
                mode_used="tutor",
                memory_context_used=[m["entity_name"] for m in memory_result.memories[:10]],
                memory_realms_accessed=memory_result.realms_accessed,
                learning_context={
                    "understanding_level": understanding_level,
                    "learning_objective": objective,
                    "follow_up_questions": follow_up,
                    "suggested_topics": next_topics
                },
                learning_path=learning_path,
                relationships_traversed=memory_result.relationships_traversed,
                memory_query_time_ms=memory_result.query_time_ms
            )
            
        except Exception as e:
            logger.error(f"Tutor mode processing error: {e}")
            raise
            
    def _assess_understanding(
        self,
        message: str,
        current_level: Optional[int]
    ) -> int:
        """
        Assess user's understanding level from their message.
        
        KISS: Simple keyword and pattern matching, no ML.
        
        Returns:
            Understanding level 1-5
        """
        # Default to middle level
        if current_level is None:
            current_level = 3
            
        message_lower = message.lower()
        
        # Indicators of confusion/low understanding
        confusion_indicators = [
            "i don't understand",
            "confused",
            "what does that mean",
            "can you explain",
            "i'm lost",
            "too complex",
            "simpler"
        ]
        
        # Indicators of good understanding
        understanding_indicators = [
            "i see",
            "that makes sense",
            "i understand",
            "got it",
            "what about",
            "how does this relate to",
            "advanced"
        ]
        
        # Check for confusion
        if any(indicator in message_lower for indicator in confusion_indicators):
            return max(1, current_level - 1)
            
        # Check for understanding
        if any(indicator in message_lower for indicator in understanding_indicators):
            return min(5, current_level + 1)
            
        # Check question complexity
        if "?" in message:
            # Simple questions
            if len(message.split()) < 10:
                return current_level
            # Complex questions suggest higher understanding
            else:
                return min(5, current_level + 1)
                
        return current_level
        
    async def _search_educational_content(
        self,
        request: ChatRequestV1,
        session: ChatSessionV1,
        client_id: UUID
    ) -> MemorySearchResult:
        """
        Search for educational content in memory.
        
        Prioritizes tutorial and guide content.
        """
        # Modify query to focus on educational content
        educational_query = request.message
        
        # Add educational context to query
        if session.learning_topic:
            educational_query = f"{session.learning_topic} tutorial guide: {request.message}"
            
        # Create modified request for search
        search_request = ChatRequestV1(
            **request.dict(exclude={"message"}),
            message=educational_query
        )
        
        return await self.memory_searcher.search_with_precedence(
            search_request,
            client_id
        )
        
    def _determine_learning_objective(
        self,
        message: str,
        current_topic: Optional[str],
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        Determine the learning objective from context.
        
        KISS: Simple extraction from message and memories.
        """
        # Extract key concepts from message
        message_lower = message.lower()
        
        # Common learning patterns
        if "how do i" in message_lower:
            return f"Learn to {message[10:].strip('?')}"
        elif "what is" in message_lower:
            return f"Understand {message[8:].strip('?')}"
        elif "why" in message_lower:
            return f"Understand reasoning behind {message[4:].strip('?')}"
        elif "when should" in message_lower:
            return f"Learn when to apply {message[12:].strip('?')}"
            
        # Use current topic if available
        if current_topic:
            return f"Deepen understanding of {current_topic}"
            
        # Extract from memory entities
        if memories:
            topics = [m["entity_name"] for m in memories[:3]]
            return f"Learn about {', '.join(topics)}"
            
        return "Explore the topic"
        
    async def _generate_progressive_response(
        self,
        message: str,
        memories: List[Dict[str, Any]],
        understanding_level: int,
        objective: str
    ) -> str:
        """
        Generate response adapted to understanding level.
        
        KISS: Use LLM with simple prompting based on level.
        """
        # Build context from memories
        memory_context = self._build_memory_context(memories[:5])
        
        # Adjust prompt based on understanding level
        level_guidance = {
            1: "Explain in very simple terms with basic examples",
            2: "Explain clearly with simple examples",
            3: "Provide balanced explanation with examples",
            4: "Include more detail and connections",
            5: "Provide advanced explanation with nuances"
        }
        
        prompt = f"""You are a helpful tutor. The learning objective is: {objective}

User understanding level: {understanding_level}/5
Guidance: {level_guidance.get(understanding_level, level_guidance[3])}

Available knowledge from memory:
{memory_context}

User question: {message}

Provide a response that:
1. Addresses the question at the appropriate level
2. Builds on their current understanding
3. Uses examples from the memory context when relevant
4. Encourages further exploration

Response:"""

        # Call LLM (simplified for now)
        # In production, this would use the actual LLM service
        response = f"""Based on your question about {objective}, let me explain at a level {understanding_level} understanding.

{memory_context}

Would you like me to elaborate on any specific part?"""

        return response
        
    def _generate_follow_up_questions(
        self,
        objective: str,
        understanding_level: int,
        memories: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate appropriate follow-up questions.
        
        KISS: Template-based questions adjusted by level.
        """
        questions = []
        
        # Basic questions for lower levels
        if understanding_level <= 2:
            questions.extend([
                f"Would you like a simpler explanation of {objective}?",
                "What part would you like me to clarify?",
                "Shall we go through an example together?"
            ])
            
        # Intermediate questions
        elif understanding_level == 3:
            questions.extend([
                f"How do you think this {objective} applies to your work?",
                "What aspects interest you most?",
                "Would you like to explore a related concept?"
            ])
            
        # Advanced questions
        else:
            questions.extend([
                f"What are your thoughts on alternative approaches to {objective}?",
                "How does this connect with your existing knowledge?",
                "What advanced aspects would you like to explore?"
            ])
            
        # Add memory-based questions
        if memories:
            topic = memories[0].get("entity_name", "this topic")
            questions.append(f"Would you like to dive deeper into {topic}?")
            
        return questions[:3]  # Limit to 3 questions
        
    def _suggest_next_topics(
        self,
        current_topic: Optional[str],
        memories: List[Dict[str, Any]],
        understanding_level: int
    ) -> List[str]:
        """
        Suggest appropriate next topics.
        
        KISS: Extract from memory relationships.
        """
        suggestions = []
        
        # Extract topics from memories
        for memory in memories[:10]:
            # Look for related concepts in metadata
            metadata = memory.get("metadata", {})
            related = metadata.get("related_topics", [])
            suggestions.extend(related)
            
        # Add progression based on understanding
        if current_topic and understanding_level >= 3:
            suggestions.append(f"Advanced {current_topic}")
            
        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen and s != current_topic:
                seen.add(s)
                unique_suggestions.append(s)
                
        return unique_suggestions[:5]
        
    def _build_learning_path(
        self,
        current_path: List[str],
        new_objective: str
    ) -> List[str]:
        """
        Update learning path with new objective.
        
        Maintains max 10 items.
        """
        # Don't duplicate
        if new_objective not in current_path:
            current_path.append(new_objective)
            
        # Keep last 10
        return current_path[-10:]
        
    def _build_memory_context(
        self,
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        Build context string from memories.
        
        KISS: Simple text extraction.
        """
        if not memories:
            return "No specific knowledge available."
            
        context_parts = []
        for memory in memories:
            name = memory.get("entity_name", "Unknown")
            # Extract key observations
            observations = memory.get("observations", [])
            if observations:
                value = observations[0].get("value", "")
                if isinstance(value, dict):
                    value = value.get("content", str(value))
                context_parts.append(f"- {name}: {str(value)[:200]}")
            else:
                context_parts.append(f"- {name}")
                
        return "\n".join(context_parts)