"""
Test Pydantic context model for content_ideator crew.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid

class ContentIdeatorContext(BaseModel):
    """
    Pydantic context model for the content_ideator crew.
    Matches the structure defined in the crew config.
    """
    # Core request fields
    user_prompt: Optional[str] = None
    client_user_id: Optional[str] = None
    actor_type: Optional[str] = None
    actor_id: Optional[str] = None
    job_key: Optional[str] = None
    
    # Context data fields
    source_chunks: List[str] = []
    actor_attributes: Dict[str, Any] = {}
    client_attributes: Dict[str, Any] = {}
    
    # Workflow state fields
    selected_finalist: Optional[Dict[str, Any]] = None
    structured_prompt: Optional[str] = None
    discussion_history: List[Dict[str, Any]] = []
    selected_runners_up: Optional[List[Dict[str, Any]]] = None
    blog_idea_candidates: Optional[List[Dict[str, Any]]] = None

    class Config:
        """Pydantic model configuration."""
        extra = "allow"  # Allow extra fields not defined in the model
        validate_assignment = True  # Validate on assignment
