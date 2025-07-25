"""
Enhanced Streaming Infrastructure for Chat with Memory v1.

KISS principles:
- Simple SSE streaming with metadata
- Basic chunk buffering
- Error recovery without complexity
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import UUID

from src.chat.models import ChatResponseV1

logger = logging.getLogger(__name__)


class StreamGeneratorV1:
    """
    Enhanced SSE stream generator with metadata support.
    
    KISS: Just stream chunks with metadata, no fancy protocols.
    """
    
    def __init__(self, chunk_size: int = 50, chunk_delay_ms: int = 30):
        """
        Initialize stream generator.
        
        Args:
            chunk_size: Characters per chunk
            chunk_delay_ms: Delay between chunks in milliseconds
        """
        self.chunk_size = chunk_size
        self.chunk_delay_ms = chunk_delay_ms
        
    async def generate_stream(
        self,
        response: ChatResponseV1,
        include_metadata: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Generate SSE stream from chat response.
        
        Args:
            response: Chat response to stream
            include_metadata: Include mode metadata in stream
            
        Yields:
            SSE formatted events
        """
        try:
            # 1. Send initial metadata event
            if include_metadata:
                metadata_event = self._create_metadata_event(response)
                yield f"event: metadata\ndata: {json.dumps(metadata_event)}\n\n"
                
            # 2. Send typing indicator
            yield 'event: typing\ndata: {"status": "started"}\n\n'
            
            # 3. Stream response chunks
            text = response.response
            chunks = self._chunk_text(text)
            
            for i, chunk in enumerate(chunks):
                # Create chunk event
                chunk_event = {
                    "chunk": chunk,
                    "index": i,
                    "total": len(chunks)
                }
                
                yield f"event: chunk\ndata: {json.dumps(chunk_event)}\n\n"
                
                # Delay between chunks
                await asyncio.sleep(self.chunk_delay_ms / 1000)
                
            # 4. Send completion event
            completion_event = self._create_completion_event(response)
            yield f"event: complete\ndata: {json.dumps(completion_event)}\n\n"
            
            # 5. Stop typing indicator
            yield 'event: typing\ndata: {"status": "stopped"}\n\n'
            
        except Exception as e:
            logger.error(f"Stream generation error: {e}")
            # Send error event
            error_event = {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
            
    async def generate_search_status_stream(
        self,
        search_phases: list
    ) -> AsyncGenerator[str, None]:
        """
        Stream memory search progress indicators.
        
        Args:
            search_phases: List of search phases to indicate
            
        Yields:
            SSE search status events
        """
        for phase in search_phases:
            status_event = {
                "phase": phase["name"],
                "status": phase["status"],
                "details": phase.get("details", "")
            }
            
            yield f"event: search_status\ndata: {json.dumps(status_event)}\n\n"
            
            # Small delay to show progress
            await asyncio.sleep(0.1)
            
    def _create_metadata_event(self, response: ChatResponseV1) -> Dict[str, Any]:
        """Create metadata event from response."""
        metadata = {
            "session_id": str(response.session_id),
            "message_id": str(response.message_id),
            "mode": response.mode_used,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add mode-specific metadata
        if response.mode_used == "tutor" and response.learning_context:
            metadata["learning_context"] = {
                "understanding_level": response.learning_context.get("understanding_level"),
                "objective": response.learning_context.get("learning_objective")
            }
        elif response.mode_used == "agent" and response.task_context:
            metadata["task_context"] = {
                "intent": response.task_context.get("intent"),
                "procedures_count": len(response.task_context.get("procedures_followed", []))
            }
            
        # Add memory context summary
        metadata["memory_context"] = {
            "memories_used": len(response.memory_context_used),
            "realms_accessed": response.memory_realms_accessed,
            "query_time_ms": response.memory_query_time_ms
        }
        
        return metadata
        
    def _create_completion_event(self, response: ChatResponseV1) -> Dict[str, Any]:
        """Create completion event with summary."""
        completion = {
            "session_id": str(response.session_id),
            "message_id": str(response.message_id),
            "total_length": len(response.response),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add follow-up suggestions for tutor mode
        if response.mode_used == "tutor" and response.learning_context:
            completion["follow_up_questions"] = response.learning_context.get(
                "follow_up_questions", []
            )
            completion["suggested_topics"] = response.learning_context.get(
                "suggested_topics", []
            )
            
        return completion
        
    def _chunk_text(self, text: str) -> list:
        """
        Split text into chunks for streaming.
        
        KISS: Simple character-based chunking.
        """
        chunks = []
        
        # Split by sentences first for natural breaks
        sentences = text.split(". ")
        
        current_chunk = ""
        for sentence in sentences:
            # Add period back
            if sentence and not sentence.endswith("."):
                sentence += "."
                
            # If adding sentence exceeds chunk size, yield current
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "
                
        # Add remaining
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        # If no sentences or very short text, fall back to character chunking
        if not chunks:
            for i in range(0, len(text), self.chunk_size):
                chunks.append(text[i:i + self.chunk_size])
                
        return chunks


class StreamBuffer:
    """
    Simple buffer for stream chunks with error recovery.
    
    KISS: Just a list with size limit.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize buffer.
        
        Args:
            max_size: Maximum chunks to buffer
        """
        self.buffer = []
        self.max_size = max_size
        self.error_count = 0
        
    def add_chunk(self, chunk: str):
        """Add chunk to buffer."""
        if len(self.buffer) >= self.max_size:
            # Remove oldest
            self.buffer.pop(0)
        self.buffer.append(chunk)
        
    def get_replay_chunks(self, from_index: int = 0) -> list:
        """Get chunks for replay after error."""
        return self.buffer[from_index:]
        
    def record_error(self):
        """Record streaming error."""
        self.error_count += 1
        
    def should_retry(self) -> bool:
        """Check if should retry after error."""
        return self.error_count < 3  # Max 3 retries
        
    def clear(self):
        """Clear buffer."""
        self.buffer.clear()
        self.error_count = 0