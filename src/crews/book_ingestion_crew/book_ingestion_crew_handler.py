"""
Book Ingestion Crew Handler
Implements the BaseCrewHandler interface for book ingestion operations.
"""

import logging
from typing import Dict, Any
from uuid import UUID

from crews.base import BaseCrewHandler
from src.services.json_validator import validate_crew_request, SchemaValidationError
from .crew_production import kickoff

logger = logging.getLogger(__name__)

class BookIngestionCrewHandler(BaseCrewHandler):
    """
    Handler for book ingestion crew operations.
    This is a minimal implementation for testing the crew handler pattern.
    """
    
    def __init__(self, job_id: UUID = None):
        """Initialize the book ingestion crew handler."""
        super().__init__(job_id)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("BookIngestionCrewHandler initialized")
    
    async def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the book ingestion crew with the provided request data.
        
        Args:
            request_data: Job request data including all parameters
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            Exception: If execution fails
        """
        try:
            # Log execution start
            self.log_execution_start(request_data)
            
            # Validate request data against schema
            self.logger.info("Validating request data against book_ingestion_crew schema")
            validation_result = await validate_crew_request(
                request_data, 
                job_key="book_ingestion_crew"
            )
            
            if not validation_result['valid']:
                error_msg = f"Schema validation failed: {validation_result['errors']}"
                self.logger.error(error_msg)
                raise SchemaValidationError(error_msg, validation_result['errors'])
            
            self.logger.info(f"Schema validation successful using schema: {validation_result['schema_used']}")
            
            # Add job_id to the request data for the crew
            crew_inputs = request_data.copy()
            crew_inputs['job_id'] = str(self.job_id) if self.job_id else 'unknown'
            
            self.logger.info(f"Executing book ingestion crew with inputs: {crew_inputs}")
            
            # Execute the crew with full logging capture
            # This will capture all CrewAI logs and agent interactions
            result = await self.execute_crew_with_logging(
                kickoff,  # The crew kickoff function
                crew_inputs,  # Pass inputs as first argument
                logger=self.simple_logger  # Pass simple logger for structured events
            )
            
            self.logger.info(f"Book ingestion crew execution completed: {result}")
            
            # Log execution complete
            self.log_execution_complete(result)
            
            # Save all collected events to database
            await self.save_crew_events()
            
            return result
            
        except SchemaValidationError:
            # Re-raise schema validation errors as-is
            raise
        except Exception as e:
            self.logger.error(f"Book ingestion crew execution failed: {str(e)}", exc_info=True)
            self.log_execution_error(e)
            raise
    
    def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Validate the request data before execution.
        
        Note: Schema validation is now handled in execute() method using database schemas.
        This method provides basic structural validation.
        
        Args:
            request_data: Request data to validate
            
        Returns:
            True if valid, raises Exception if invalid
        """
        # First, call parent validation for required fields
        super().validate_request(request_data)
        
        # Check for required book ingestion fields (basic validation)
        required_fields = ['google_drive_folder_path', 'language']
        missing_fields = [field for field in required_fields if field not in request_data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields for book ingestion: {missing_fields}")
        
        # Validate language field
        valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'pl', 'ru', 'ja', 'zh']
        if request_data.get('language') not in valid_languages:
            raise ValueError(f"Invalid language '{request_data.get('language')}'. Must be one of: {valid_languages}")
        
        self.logger.info("Basic request validation successful")
        return True
    
    def get_job_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this job type.
        
        Returns:
            Dictionary with job type metadata
        """
        return {
            "handler_class": self.__class__.__name__,
            "description": "Handles book ingestion operations including OCR, parsing, and storage",
            "crew_type": "book_ingestion_crew",
            "version": "2.0.0",
            "capabilities": [
                "multi_pass_ocr",
                "gpt4o_vision",
                "sequential_thinking",
                "database_storage",
                "embedding_generation",
                "page_by_page_processing",
                "todo_tracking",
                "context_aware_ocr"
            ]
        }