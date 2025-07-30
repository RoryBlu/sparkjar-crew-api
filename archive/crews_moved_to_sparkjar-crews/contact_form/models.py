"""
Pydantic models for contact form crew structured outputs.
These models ensure data consistency and validation throughout the crew execution.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

import logging
logger = logging.getLogger(__name__)

class InquiryIntent(str, Enum):
    """Types of inquiry intents."""
    DEMO_REQUEST = "demo_request"
    PRICING_INQUIRY = "pricing_inquiry"
    TECHNICAL_QUESTION = "technical_question"
    PARTNERSHIP_INQUIRY = "partnership_inquiry"
    GENERAL_INQUIRY = "general_inquiry"
    SUPPORT_REQUEST = "support_request"

class UrgencyLevel(str, Enum):
    """Urgency levels for inquiries."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Sentiment(str, Enum):
    """Sentiment analysis results."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class ContactAnalysis(BaseModel):
    """Structured output for contact inquiry analysis."""
    
    # Analysis results
    primary_intent: InquiryIntent = Field(
        description="The primary intent of the inquiry"
    )
    urgency_level: UrgencyLevel = Field(
        description="Assessed urgency level of the inquiry"
    )
    key_topics: List[str] = Field(
        description="Key topics mentioned in the inquiry",
        min_items=1,
        max_items=10
    )
    sentiment: Sentiment = Field(
        description="Overall sentiment of the inquiry"
    )
    
    # Extracted entities
    mentioned_products: List[str] = Field(
        default_factory=list,
        description="Any SparkJAR products or services mentioned"
    )
    mentioned_technologies: List[str] = Field(
        default_factory=list,
        description="Technologies or platforms mentioned (e.g., ERP, AI, etc.)"
    )
    
    # Business intelligence
    company_size_indicator: Optional[str] = Field(
        None,
        description="Any indicators of company size from the message"
    )
    budget_indicator: Optional[str] = Field(
        None,
        description="Any budget-related mentions"
    )
    timeline_indicator: Optional[str] = Field(
        None,
        description="Any timeline or urgency mentions"
    )
    
    # Recommended actions
    recommended_response_type: str = Field(
        description="Type of response recommended (e.g., 'schedule_demo', 'send_info', 'urgent_callback')"
    )
    follow_up_priority: int = Field(
        description="Priority score for follow-up (1-10)",
        ge=1,
        le=10
    )

class ContactEntity(BaseModel):
    """Information about a contact entity in the system."""
    
    entity_id: str = Field(
        description="Memory system entity UUID"
    )
    is_new_contact: bool = Field(
        description="Whether this is a new contact or existing"
    )
    previous_interactions: int = Field(
        default=0,
        description="Number of previous interactions found"
    )
    existing_relationships: List[str] = Field(
        default_factory=list,
        description="List of existing relationship IDs"
    )

class OdooRecord(BaseModel):
    """Information about created Odoo records."""
    
    lead_id: Optional[str] = Field(
        None,
        description="Odoo lead ID if created"
    )
    contact_id: Optional[str] = Field(
        None,
        description="Odoo contact ID if created/found"
    )
    opportunity_id: Optional[str] = Field(
        None,
        description="Odoo opportunity ID if created"
    )
    record_url: Optional[str] = Field(
        None,
        description="Direct URL to the Odoo record"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if Odoo integration failed"
    )

class InquiryStorage(BaseModel):
    """Results of storing the inquiry in memory."""
    
    observation_ids: List[str] = Field(
        description="List of observation IDs created"
    )
    document_id: Optional[str] = Field(
        None,
        description="Document ID if inquiry was archived"
    )
    tags_applied: List[str] = Field(
        default_factory=list,
        description="Tags applied to the observations"
    )

class ContactFormResult(BaseModel):
    """Final structured output of the contact form crew."""
    
    # Processing metadata
    job_id: str = Field(
        description="The crew job ID"
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of processing"
    )
    processing_time_seconds: Optional[float] = Field(
        None,
        description="Total processing time"
    )
    
    # Analysis results
    analysis: ContactAnalysis = Field(
        description="Structured analysis of the inquiry"
    )
    
    # Storage results
    contact_entity: ContactEntity = Field(
        description="Contact entity information"
    )
    odoo_record: OdooRecord = Field(
        description="Odoo integration results"
    )
    inquiry_storage: InquiryStorage = Field(
        description="Memory storage results"
    )
    
    # Response information
    suggested_response: str = Field(
        description="AI-generated suggested response"
    )
    next_actions: List[str] = Field(
        description="Concrete next steps to take"
    )
    
    # Status
    status: str = Field(
        default="completed",
        description="Overall status of the crew execution"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Any non-fatal errors encountered"
    )

class MemorySearchResult(BaseModel):
    """Result from memory system searches."""
    
    entity_id: str
    entity_name: str
    entity_type: str
    similarity_score: float
    metadata: Dict[str, Any]