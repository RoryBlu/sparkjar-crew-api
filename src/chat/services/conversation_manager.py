"""
Conversation management core logic.

Handles conversation flow, context window management, and
coordination between memory retrieval and response generation.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID, uuid4

from openai import AsyncOpenAI

from src.chat.models.chat_models import ChatMessage, ChatRequest, ChatResponse
from src.chat.models.context_models import ConversationContext, SynthContext, MemoryEntity
from src.chat.clients.memory_service import MemoryServiceClient
from src.chat.clients.thinking_service import ThinkingServiceClient
from src.chat.config import get_settings
from .session_manager import SessionManager
from src.chat.utils.error_handler import ChatErrorHandler, ErrorRecovery, ServiceError, ErrorCategory

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation flow and context integration."""
    
    def __init__(
        self,
        session_manager: SessionManager,
        memory_client: MemoryServiceClient,
        thinking_client: Optional[ThinkingServiceClient] = None,
        openai_client: Optional[AsyncOpenAI] = None
    ):
        """
        Initialize conversation manager.
        
        Args:
            session_manager: Session management instance
            memory_client: Memory service client
            thinking_client: Thinking service client for sequential thinking
            openai_client: OpenAI client for response generation
        """
        self.session_manager = session_manager
        self.memory_client = memory_client
        self.thinking_client = thinking_client or ThinkingServiceClient()
        self.settings = get_settings()
        
        # Initialize OpenAI client
        self.openai_client = openai_client or AsyncOpenAI()
        
        # Context window configuration
        self.max_context_tokens = 8000  # Reserve some for response
        self.response_max_tokens = 2000
        
    async def process_chat_request(
        self,
        request: ChatRequest,
        synth_context: SynthContext
    ) -> ChatResponse:
        """
        Process a chat request and generate response.
        
        Args:
            request: Incoming chat request
            synth_context: Resolved SYNTH context
            
        Returns:
            Chat response with memory context
        """
        # Get or create session
        context = await self.session_manager.get_or_create_session(
            session_id=request.session_id,
            client_user_id=request.client_user_id,
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            synth_context=synth_context,
            metadata=request.metadata
        )
        
        # Create user message
        user_message = ChatMessage(
            message_id=uuid4(),
            session_id=context.session_id,
            role="user",
            content=request.message,
            timestamp=datetime.utcnow(),
            metadata=request.metadata
        )
        
        # Add to conversation history
        await self.session_manager.add_message(context.session_id, user_message)
        
        # Search relevant memories
        memory_entities = await self._search_relevant_memories(
            query=request.message,
            synth_context=synth_context,
            conversation_context=context
        )
        
        # Update active memory context
        await self.session_manager.update_memory_context(
            context.session_id,
            memory_entities
        )
        
        # Build conversation context with memory
        messages = self._build_conversation_messages(
            context=context,
            memory_entities=memory_entities,
            synth_context=synth_context
        )
        
        # Generate response
        if request.enable_sequential_thinking:
            response_content, thinking_session_id = await self._generate_thinking_response(
                request=request,
                context=context,
                messages=messages,
                memory_entities=memory_entities
            )
            
            # Update session with thinking session ID
            if thinking_session_id:
                await self.session_manager.set_thinking_session(
                    context.session_id,
                    thinking_session_id
                )
        else:
            response_content = await self._generate_standard_response(messages)
            thinking_session_id = None
            
        # Create response message
        response_message = ChatMessage(
            message_id=uuid4(),
            session_id=context.session_id,
            role="assistant",
            content=response_content,
            timestamp=datetime.utcnow(),
            metadata={"memory_contexts_used": len(memory_entities)}
        )
        
        # Add response to history
        await self.session_manager.add_message(context.session_id, response_message)
        
        # Create response
        return ChatResponse(
            session_id=context.session_id,
            message_id=response_message.message_id,
            message=request.message,
            response=response_content,
            memory_context_used=self._extract_memory_context_names(memory_entities),
            thinking_session_id=thinking_session_id or context.thinking_session_id,
            metadata={
                "response_time_ms": int((datetime.utcnow() - user_message.timestamp).total_seconds() * 1000),
                "memory_queries": 1,
                "tokens_used": self._estimate_tokens(messages + [{"role": "assistant", "content": response_content}])
            },
            timestamp=response_message.timestamp
        )
        
    async def process_chat_stream(
        self,
        request: ChatRequest,
        synth_context: SynthContext
    ) -> AsyncGenerator[str, None]:
        """
        Process chat request with streaming response.
        
        Args:
            request: Incoming chat request
            synth_context: Resolved SYNTH context
            
        Yields:
            Response chunks for streaming
        """
        # Get or create session
        context = await self.session_manager.get_or_create_session(
            session_id=request.session_id,
            client_user_id=request.client_user_id,
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            synth_context=synth_context,
            metadata=request.metadata
        )
        
        # Create user message
        user_message = ChatMessage(
            message_id=uuid4(),
            session_id=context.session_id,
            role="user",
            content=request.message,
            timestamp=datetime.utcnow(),
            metadata=request.metadata
        )
        
        # Add to conversation history
        await self.session_manager.add_message(context.session_id, user_message)
        
        # Search relevant memories
        memory_entities = await self._search_relevant_memories(
            query=request.message,
            synth_context=synth_context,
            conversation_context=context
        )
        
        # Update active memory context
        await self.session_manager.update_memory_context(
            context.session_id,
            memory_entities
        )
        
        # Build conversation context
        messages = self._build_conversation_messages(
            context=context,
            memory_entities=memory_entities,
            synth_context=synth_context
        )
        
        # Stream response
        full_response = ""
        async for chunk in self._stream_response(messages):
            full_response += chunk
            yield chunk
            
        # Create response message for history
        response_message = ChatMessage(
            message_id=uuid4(),
            session_id=context.session_id,
            role="assistant",
            content=full_response,
            timestamp=datetime.utcnow(),
            metadata={"memory_contexts_used": len(memory_entities)}
        )
        
        # Add complete response to history
        await self.session_manager.add_message(context.session_id, response_message)
        
    async def _search_relevant_memories(
        self,
        query: str,
        synth_context: SynthContext,
        conversation_context: ConversationContext
    ) -> List[MemoryEntity]:
        """
        Search for relevant memories based on query and context.
        
        Args:
            query: User's message
            synth_context: SYNTH hierarchy context
            conversation_context: Current conversation context
            
        Returns:
            List of relevant memory entities
        """
        # Define fallback function
        async def fallback_memory_search(*args, **kwargs):
            logger.warning("Using fallback: returning empty memory list")
            return []
            
        # Search with error recovery
        async def search_memories():
            try:
                # Enhance query with conversation context
                enhanced_query = self._enhance_query_with_context(
                    query,
                    conversation_context
                )
                
                # Search memories with hierarchy
                memories = await self.memory_client.search_relevant_memories(
                    query=enhanced_query,
                    synth_context=synth_context,
                    limit=10,
                    min_confidence=0.7,
                    include_synth_class=True,
                    include_client=True
                )
                
                logger.info(f"Found {len(memories)} relevant memories for session {conversation_context.session_id}")
                return memories
                
            except Exception as e:
                # Convert to service error for consistent handling
                service_error = ChatErrorHandler.handle_memory_service_error(e)
                logger.error(f"Memory search failed: {service_error.message}", extra={"details": service_error.details})
                raise service_error
                
        # Execute with fallback
        return await ErrorRecovery.with_memory_fallback(
            search_memories,
            fallback_memory_search
        )
            
    def _enhance_query_with_context(
        self,
        query: str,
        context: ConversationContext
    ) -> str:
        """
        Enhance search query with recent conversation context.
        
        Args:
            query: Original user query
            context: Conversation context
            
        Returns:
            Enhanced query string
        """
        # Get last few exchanges for context
        recent_messages = context.conversation_history[-4:] if len(context.conversation_history) > 1 else []
        
        if not recent_messages:
            return query
            
        # Build context summary
        context_parts = []
        for msg in recent_messages:
            if msg.role == "user":
                context_parts.append(f"User asked: {msg.content[:100]}")
            else:
                context_parts.append(f"Assistant discussed: {msg.content[:100]}")
                
        context_summary = " ".join(context_parts[-2:])  # Last 2 exchanges
        
        # Enhance query
        enhanced = f"{query} (Context: {context_summary})"
        return enhanced
        
    def _build_conversation_messages(
        self,
        context: ConversationContext,
        memory_entities: List[MemoryEntity],
        synth_context: SynthContext
    ) -> List[Dict[str, str]]:
        """
        Build conversation messages for LLM including system prompt and memory context.
        
        Args:
            context: Conversation context
            memory_entities: Relevant memories
            synth_context: SYNTH configuration
            
        Returns:
            List of message dictionaries for OpenAI API
        """
        messages = []
        
        # System message with SYNTH personality and memory context
        system_content = self._build_system_message(synth_context, memory_entities)
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        for msg in context.conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        # Manage context window
        messages = self._manage_context_window(messages)
        
        return messages
        
    def _build_system_message(
        self,
        synth_context: SynthContext,
        memory_entities: List[MemoryEntity]
    ) -> str:
        """
        Build system message with SYNTH personality and memory context.
        
        Args:
            synth_context: SYNTH configuration and policies
            memory_entities: Relevant memory entities
            
        Returns:
            System message content
        """
        parts = []
        
        # Base SYNTH role from class configuration
        if synth_context.synth_class_config.get("role"):
            parts.append(f"You are a {synth_context.synth_class_config['role']}.")
            
        # Company customizations
        if synth_context.company_customizations:
            parts.append("Company guidelines: " + 
                        "; ".join(f"{k}: {v}" for k, v in synth_context.company_customizations.items()))
                        
        # Client policies (highest priority)
        if synth_context.client_policies:
            parts.append("Client requirements: " +
                        "; ".join(f"{k}: {v}" for k, v in synth_context.client_policies.items()))
                        
        # Memory context
        if memory_entities:
            parts.append("\nRelevant context from memory:")
            for entity in memory_entities[:5]:  # Limit to top 5
                entity_summary = self._summarize_memory_entity(entity)
                parts.append(f"- {entity_summary}")
                
        return "\n".join(parts)
        
    def _summarize_memory_entity(self, entity: MemoryEntity) -> str:
        """
        Create concise summary of memory entity for context.
        
        Args:
            entity: Memory entity to summarize
            
        Returns:
            Summary string
        """
        summary_parts = [f"{entity.entity_name} ({entity.entity_type})"]
        
        # Add key observations
        for obs in entity.observations[:3]:  # Limit observations
            if obs.type == "fact":
                summary_parts.append(f"fact: {obs.value}")
            elif obs.type == "skill" and hasattr(obs, "skill_name"):
                summary_parts.append(f"skill: {obs.skill_name}")
                
        return "; ".join(summary_parts)
        
    def _manage_context_window(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Manage context window size by pruning old messages if needed.
        
        Args:
            messages: All conversation messages
            
        Returns:
            Messages that fit within context window
        """
        # Estimate tokens (rough approximation)
        total_tokens = self._estimate_tokens(messages)
        
        if total_tokens <= self.max_context_tokens:
            return messages
            
        # Keep system message and recent messages
        system_message = messages[0]
        conversation_messages = messages[1:]
        
        # Keep removing oldest messages until within limit
        while len(conversation_messages) > 2 and self._estimate_tokens([system_message] + conversation_messages) > self.max_context_tokens:
            conversation_messages = conversation_messages[2:]  # Remove oldest exchange
            
        return [system_message] + conversation_messages
        
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Rough token estimation for messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        total_chars = sum(len(msg["content"]) for msg in messages)
        return total_chars // 4
        
    async def _generate_standard_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate response using OpenAI API.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Generated response content
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Using efficient model for MVP
                messages=messages,
                max_tokens=self.response_max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."
            
    async def _stream_response(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """
        Stream response using OpenAI API.
        
        Args:
            messages: Conversation messages
            
        Yields:
            Response chunks
        """
        try:
            stream = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=self.response_max_tokens,
                temperature=0.7,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            # Handle streaming errors
            error_data = ChatErrorHandler.handle_streaming_error(e)
            logger.error(f"Streaming error: {error_data['message']}")
            
            # Yield error message in a user-friendly way
            yield "I apologize, but I'm having trouble generating a response right now. "
            
            # Log the actual error for debugging
            if isinstance(e, TimeoutException):
                yield "The response timed out. Please try again."
            elif isinstance(e, ConnectError):
                yield "Connection issue detected. Please check your internet connection."
            else:
                yield "Please try again in a moment."
            
    def _extract_memory_context_names(self, memory_entities: List[MemoryEntity]) -> List[str]:
        """
        Extract memory entity names for response metadata.
        
        Args:
            memory_entities: Memory entities used
            
        Returns:
            List of entity names
        """
        return [entity.entity_name for entity in memory_entities]
        
    async def _generate_thinking_response(
        self,
        request: ChatRequest,
        context: ConversationContext,
        messages: List[Dict[str, str]],
        memory_entities: List[MemoryEntity]
    ) -> tuple[str, Optional[UUID]]:
        """
        Generate response using sequential thinking service.
        
        Args:
            request: Chat request
            context: Conversation context
            messages: Prepared messages for LLM
            memory_entities: Relevant memory entities
            
        Returns:
            Tuple of (response content, thinking session ID)
        """
        # Define thinking function
        async def thinking_response():
            try:
                # Create or continue thinking session
                if context.thinking_session_id:
                    thinking_session_id = context.thinking_session_id
                else:
                    # Create new thinking session
                    problem_statement = f"Chat conversation with context: {request.message}"
                    if memory_entities:
                        problem_statement += f"\nRelevant context: {', '.join(self._extract_memory_context_names(memory_entities))}"
                        
                    thinking_session_id = await self.thinking_client.create_thinking_session(
                        problem_statement=problem_statement,
                        client_user_id=request.client_user_id,
                        session_name=f"Chat session {context.session_id}",
                        metadata={
                            "chat_session_id": str(context.session_id),
                            "actor_id": str(request.actor_id)
                        }
                    )
                    
                # Get thinking response
                thinking_response = await self.thinking_client.get_thinking_response(
                    session_id=thinking_session_id,
                    user_input=request.message,
                    max_thoughts=5
                )
                
                # For MVP, combine thinking with standard response
                # In production, this would be more sophisticated
                thinking_prefix = f"Let me think about this step by step...\n\n"
                thinking_prefix += f"Thought #{thinking_response.thought_number}: {thinking_response.thought_content}\n\n"
                
                # Generate final response with thinking context
                messages_with_thinking = messages.copy()
                messages_with_thinking.append({
                    "role": "assistant",
                    "content": thinking_prefix
                })
                
                final_response = await self._generate_standard_response(messages_with_thinking)
                
                # Combine thinking and response
                full_response = thinking_prefix + final_response
                
                return full_response, thinking_session_id
                
            except Exception as e:
                # Convert to service error
                service_error = ChatErrorHandler.handle_thinking_service_error(e)
                logger.warning(f"Thinking service error: {service_error.message}", extra={"details": service_error.details})
                raise service_error
                
        # Define standard response fallback
        async def standard_response():
            response = await self._generate_standard_response(messages)
            return response, None
            
        # Execute with fallback to standard response
        return await ErrorRecovery.with_thinking_fallback(
            thinking_response,
            standard_response
        )
