"""
Pydantic models for API request/response schemas.
Based on the specifications in API.md.
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
import uuid
import asyncio

# Import moved to where it's used to avoid circular imports

class CrewJobRequest(BaseModel):
    """
    Request model for POST /crew_job endpoint.
    
    This model accepts generic JSON data. Validation happens at the endpoint level
    using async database schema validation.
    
    All schemas require: job_key, client_user_id, actor_type, actor_id
    Additional fields are determined by the specific schema.
    """
    
    # Accept any JSON data - validation happens at endpoint level
    data: Dict[str, Any] = Field(..., description="Request data to be validated against object schemas")
    
    @property
    def job_key(self) -> str:
        """Extract job_key from data."""
        return self.data.get('job_key')
    
    @property
    def client_user_id(self) -> str:
        """Extract client_user_id from data."""
        return self.data.get('client_user_id')
    
    @property
    def actor_type(self) -> str:
        """Extract actor_type from data."""
        return self.data.get('actor_type')
    
    @property
    def actor_id(self) -> str:
        """Extract actor_id from data."""
        return self.data.get('actor_id')
    
    class Config:
        schema_extra = {
            "example": {
                "data": {
                    "job_key": "crew_research_sj_websearch",
                    "client_user_id": "user123",
                    "actor_type": "synth",
                    "actor_id": "synth456",
                    "topic": "AI research trends",
                    "additional_field": "value"
                }
            }
        }

# Keep the old model for backward compatibility but mark as deprecated
class LegacyCrewJobRequest(BaseModel):
    """
    DEPRECATED: Legacy request model for POST /crew_job endpoint.
    Use CrewJobRequest instead which validates against database schemas.
    """
    
    # Required fields for all jobs
    job_key: str = Field(..., description="Identifies the crew to run")
    client_user_id: str = Field(..., description="User requesting the job")
    actor_type: Literal["synth", "human"] = Field(..., description="Type of actor")
    actor_id: str = Field(..., description="ID of the synth or human actor")
    
    # Generic fields for extensibility
    additional_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional job-specific data")
    
    class Config:
        extra = "allow"  # Allow additional fields for different job types

class CrewJobResponse(BaseModel):
    """Response model for POST /crew_job endpoint."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")

class JobStatusResponse(BaseModel):
    """Response model for GET /crew_job/{id} endpoint."""
    
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result data")
    events: Optional[List[Dict[str, Any]]] = Field(None, description="Job execution events")

class HealthResponse(BaseModel):
    """Response model for GET /health endpoint."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    environment: str = Field(..., description="Current environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class ChromaTestResponse(BaseModel):
    """Response model for GET /test_chroma endpoint."""
    
    status: str = Field(..., description="Connection status")
    collections: List[str] = Field(..., description="List of collection names")
    chroma_url: str = Field(..., description="ChromaDB server URL")
    total_collections: int = Field(..., description="Total number of collections")

class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

class SchemaValidationResponse(BaseModel):
    """Response model for schema validation results."""
    
    valid: bool = Field(..., description="Whether the data passed validation")
    schema_used: Optional[str] = Field(None, description="Name of the schema used for validation")
    schema_type: Optional[str] = Field(None, description="Type of schema (crew_request, table_column, etc.)")
    message: str = Field(..., description="Validation result message")
    errors: Optional[List[str]] = Field(None, description="List of validation errors if validation failed")

class ValidationErrorResponse(BaseModel):
    """Error response model for validation failures."""
    
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    validation_errors: Optional[List[str]] = Field(None, description="Specific validation error messages")
    schema_name: Optional[str] = Field(None, description="Schema that was being validated against")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

class CrewMessageRequest(BaseModel):
    """
    Request model for POST /crew_message_api endpoint.
    Uses API key authentication instead of JWT tokens.
    """
    
    api_key: str = Field(..., description="SparkJar API key for authentication", min_length=1)
    inquiry_type: Literal["contact_form", "demo_request", "early_access"] = Field(..., description="Type of inquiry")
    contact: Dict[str, Any] = Field(..., description="Contact information")
    message: str = Field(..., description="The inquiry message", min_length=1)
    metadata: Dict[str, Any] = Field(..., description="Additional metadata about the inquiry")
    
    @validator('contact')
    def validate_contact(cls, v):
        """Validate contact has required fields."""
        if 'name' not in v or not v['name']:
            raise ValueError('Contact must have a name')
        if 'email' not in v or not v['email']:
            raise ValueError('Contact must have an email')
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata has required fields."""
        required = ['source_site', 'source_locale', 'timestamp']
        for field in required:
            if field not in v:
                raise ValueError(f'Metadata must include {field}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "api_key": "sk_live_example123",
                "inquiry_type": "contact_form",
                "contact": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "company": "Acme Corp",
                    "phone": "+1-555-1234"
                },
                "message": "I'm interested in learning more about your AI services.",
                "metadata": {
                    "source_site": "n3xusiq.com",
                    "source_locale": "en_US",
                    "timestamp": "2025-01-07T10:30:00Z",
                    "user_agent": "Mozilla/5.0...",
                    "ip_address": "192.168.1.1",
                    "referrer": "https://google.com"
                }
            }
        }

class CrewMessageResponse(BaseModel):
    """Response model for POST /crew_message_api endpoint."""
    
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Confirmation message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")

# Job status constants
class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "succeeded"  # Database expects 'succeeded' not 'completed'
    FAILED = "failed"
    CANCELLED = "cancelled"
