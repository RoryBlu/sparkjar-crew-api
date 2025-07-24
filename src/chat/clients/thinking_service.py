"""
Sequential Thinking Service client for chat interface integration.

Provides methods to create and manage thinking sessions for
structured problem-solving and complex reasoning.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

import httpx
from httpx import AsyncClient, HTTPStatusError, ConnectError, TimeoutException
from pydantic import BaseModel, Field

from src.chatconfig import get_settings

logger = logging.getLogger(__name__)


class ThinkingSessionStatus(str, Enum):
    """Thinking session status options."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ThinkingServiceError(Exception):
    """Base exception for thinking service errors."""
    pass


class Thought(BaseModel):
    """Individual thought within a session."""
    id: UUID
    session_id: UUID
    thought_number: int
    thought_content: str
    is_revision: bool = False
    revised_thought_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ThinkingSession(BaseModel):
    """Thinking session model."""
    id: UUID
    client_user_id: UUID
    session_name: str
    problem_statement: str
    status: ThinkingSessionStatus
    final_answer: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    thoughts: List[Thought] = Field(default_factory=list)


class ThinkingResponse(BaseModel):
    """Response from thinking service for chat integration."""
    session_id: UUID
    thought_number: int
    thought_content: str
    is_complete: bool
    final_answer: Optional[str] = None


class ThinkingServiceClient:
    """Client for interacting with the sequential thinking service."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize thinking service client.
        
        Args:
            base_url: Override base URL for thinking service
        """
        settings = get_settings()
        self.base_url = base_url or settings.thinking_service_url
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.max_retries = 3
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make an HTTP request to the thinking service with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: Request body
            params: Query parameters
            
        Returns:
            Response data
            
        Raises:
            ThinkingServiceError: On API errors
        """
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
                logger.error(f"Failed to connect to thinking service: {e}")
                if attempt == self.max_retries - 1:
                    raise ThinkingServiceError(f"Thinking service unavailable: {e}")
                    
            except TimeoutException as e:
                logger.error(f"Thinking service request timed out: {e}")
                if attempt == self.max_retries - 1:
                    raise ThinkingServiceError(f"Thinking service timeout: {e}")
                    
            except HTTPStatusError as e:
                logger.error(f"Thinking service returned error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    continue  # Retry on server errors
                raise ThinkingServiceError(f"Thinking service error: {e.response.text}")
                
            except Exception as e:
                logger.error(f"Unexpected error calling thinking service: {e}")
                raise ThinkingServiceError(f"Unexpected error: {e}")
                
    async def create_thinking_session(
        self,
        problem_statement: str,
        client_user_id: UUID,
        session_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Create a new thinking session.
        
        Args:
            problem_statement: The problem or question to solve
            client_user_id: Client user identifier
            session_name: Optional session name
            metadata: Optional session metadata
            
        Returns:
            Session ID for the created session
        """
        try:
            request_data = {
                "client_user_id": str(client_user_id),
                "problem_statement": problem_statement,
                "session_name": session_name or f"Chat thinking session - {datetime.utcnow().isoformat()}",
                "metadata": metadata or {}
            }
            
            response = await self._make_request(
                method="POST",
                endpoint="/api/v1/thinking/sessions",
                json_data=request_data
            )
            
            session = ThinkingSession(**response)
            logger.info(f"Created thinking session {session.id}")
            return session.id
            
        except ThinkingServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating thinking session: {e}")
            raise ThinkingServiceError(f"Failed to create thinking session: {e}")
            
    async def add_thought(
        self,
        session_id: UUID,
        thought_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Thought:
        """
        Add a thought to a thinking session.
        
        Args:
            session_id: Session to add thought to
            thought_content: Content of the thought
            metadata: Optional thought metadata
            
        Returns:
            Created thought
        """
        try:
            request_data = {
                "thought_content": thought_content,
                "metadata": metadata or {}
            }
            
            response = await self._make_request(
                method="POST",
                endpoint=f"/api/v1/thinking/sessions/{session_id}/thoughts",
                json_data=request_data
            )
            
            thought = Thought(**response)
            logger.debug(f"Added thought #{thought.thought_number} to session {session_id}")
            return thought
            
        except ThinkingServiceError:
            raise
        except Exception as e:
            logger.error(f"Error adding thought: {e}")
            raise ThinkingServiceError(f"Failed to add thought: {e}")
            
    async def revise_thought(
        self,
        session_id: UUID,
        original_thought_number: int,
        revised_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Thought:
        """
        Revise a previous thought in the session.
        
        Args:
            session_id: Session containing the thought
            original_thought_number: Number of thought to revise
            revised_content: New content for the revision
            metadata: Optional revision metadata
            
        Returns:
            New thought representing the revision
        """
        try:
            request_data = {
                "thought_content": revised_content,
                "revised_thought_number": original_thought_number,
                "metadata": metadata or {}
            }
            
            response = await self._make_request(
                method="POST",
                endpoint=f"/api/v1/thinking/sessions/{session_id}/thoughts/revise",
                json_data=request_data
            )
            
            thought = Thought(**response)
            logger.debug(f"Revised thought #{original_thought_number} with thought #{thought.thought_number}")
            return thought
            
        except ThinkingServiceError:
            raise
        except Exception as e:
            logger.error(f"Error revising thought: {e}")
            raise ThinkingServiceError(f"Failed to revise thought: {e}")
            
    async def complete_session(
        self,
        session_id: UUID,
        final_answer: str
    ) -> ThinkingSession:
        """
        Complete a thinking session with a final answer.
        
        Args:
            session_id: Session to complete
            final_answer: Final conclusion or answer
            
        Returns:
            Updated session
        """
        try:
            request_data = {
                "status": ThinkingSessionStatus.COMPLETED.value,
                "final_answer": final_answer
            }
            
            response = await self._make_request(
                method="PATCH",
                endpoint=f"/api/v1/thinking/sessions/{session_id}",
                json_data=request_data
            )
            
            session = ThinkingSession(**response)
            logger.info(f"Completed thinking session {session_id}")
            return session
            
        except ThinkingServiceError:
            raise
        except Exception as e:
            logger.error(f"Error completing session: {e}")
            raise ThinkingServiceError(f"Failed to complete session: {e}")
            
    async def get_session(
        self,
        session_id: UUID,
        include_thoughts: bool = True
    ) -> ThinkingSession:
        """
        Get a thinking session by ID.
        
        Args:
            session_id: Session identifier
            include_thoughts: Whether to include all thoughts
            
        Returns:
            Thinking session
        """
        try:
            params = {"include_thoughts": include_thoughts}
            
            response = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/thinking/sessions/{session_id}",
                params=params
            )
            
            return ThinkingSession(**response)
            
        except ThinkingServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            raise ThinkingServiceError(f"Failed to get session: {e}")
            
    async def get_thinking_response(
        self,
        session_id: UUID,
        user_input: str,
        max_thoughts: int = 5
    ) -> ThinkingResponse:
        """
        Process user input through sequential thinking and get response.
        
        This is a convenience method that:
        1. Adds the user input as context
        2. Generates thoughts to solve the problem
        3. Returns a structured response
        
        Args:
            session_id: Active thinking session
            user_input: User's input or clarification
            max_thoughts: Maximum thoughts to generate
            
        Returns:
            Thinking response with thoughts and potential answer
        """
        try:
            # Add user input as a thought
            input_thought = await self.add_thought(
                session_id=session_id,
                thought_content=f"User input: {user_input}",
                metadata={"type": "user_input"}
            )
            
            # Generate thinking steps (simplified for MVP)
            # In production, this would use more sophisticated reasoning
            thinking_thought = await self.add_thought(
                session_id=session_id,
                thought_content=f"Analyzing the request: {user_input[:100]}...",
                metadata={"type": "analysis"}
            )
            
            # For MVP, we'll return a simple structured response
            # Real implementation would involve more complex reasoning
            return ThinkingResponse(
                session_id=session_id,
                thought_number=thinking_thought.thought_number,
                thought_content=thinking_thought.thought_content,
                is_complete=False,
                final_answer=None
            )
            
        except Exception as e:
            logger.error(f"Error generating thinking response: {e}")
            # Return a basic response on error
            return ThinkingResponse(
                session_id=session_id,
                thought_number=1,
                thought_content="I'm processing your request...",
                is_complete=False,
                final_answer=None
            )