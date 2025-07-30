"""
Book Translation Crew Handler
Implements the BaseCrewHandler interface for book translation operations.
"""

import logging
from typing import Dict, Any
from uuid import UUID

from src.crews.base import BaseCrewHandler
from src.services.json_validator import validate_crew_request, SchemaValidationError
from .main import kickoff

logger = logging.getLogger(__name__)

class BookTranslationCrewHandler(BaseCrewHandler):
    """
    Handler for book translation crew operations.
    Translates previously ingested books to target languages.
    """
    
    def __init__(self, job_id: UUID = None):
        """Initialize the book translation crew handler."""
        super().__init__(job_id)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("BookTranslationCrewHandler initialized")
    
    async def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the book translation crew with the provided request data.
        
        Args:
            request_data: Job request data including:
                - client_user_id: Client ID
                - book_key: Book identifier (Google Drive path)
                - target_language: Target language code (default: 'en')
                - batch_size: Pages per batch (default: 10)
                
        Returns:
            Dictionary containing execution results
            
        Raises:
            Exception: If execution fails
        """
        try:
            # Log execution start
            self.log_execution_start(request_data)
            
            # Validate request data against schema
            self.logger.info("Validating request data against book_translation_crew schema")
            validation_result = await validate_crew_request(
                request_data, 
                job_key="book_translation_crew"
            )
            
            if not validation_result['valid']:
                error_msg = f"Schema validation failed: {validation_result['errors']}"
                self.logger.error(error_msg)
                raise SchemaValidationError(error_msg, validation_result['errors'])
            
            self.logger.info(f"Schema validation successful using schema: {validation_result['schema_used']}")
            
            # Add job_id to the request data for the crew
            crew_inputs = request_data.copy()
            crew_inputs['job_id'] = str(self.job_id) if self.job_id else 'unknown'
            
            self.logger.info(f"Executing book translation crew with inputs: {crew_inputs}")
            
            # Execute the crew with full logging capture
            result = await self.execute_crew_with_logging(
                kickoff,  # The crew kickoff function
                crew_inputs,  # Pass inputs as first argument
                logger=self.simple_logger  # Pass simple logger for structured events
            )
            
            self.logger.info(f"Book translation crew execution completed: {result}")
            
            # Log execution complete
            self.log_execution_complete(result)
            
            # Save all collected events to database
            await self.save_crew_events()
            
            return result
            
        except SchemaValidationError:
            # Re-raise schema validation errors as-is
            raise
        except Exception as e:
            self.logger.error(f"Book translation crew execution failed: {str(e)}", exc_info=True)
            self.log_execution_error(e)
            raise
    
    def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Validate the request data before execution.
        
        Args:
            request_data: Request data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["client_user_id", "book_key"]
        
        for field in required_fields:
            if field not in request_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Validate target language if provided
        if "target_language" in request_data:
            valid_languages = ["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]
            if request_data["target_language"] not in valid_languages:
                self.logger.error(f"Invalid target language: {request_data['target_language']}")
                return False
        
        
        return True