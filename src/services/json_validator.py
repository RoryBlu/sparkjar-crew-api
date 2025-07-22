"""
JSON Schema Validation Service

Validates incoming JSON data against schemas stored in the object_schemas database table.
All schemas contain required fields: job_key, client_user_id, actor_type, actor_id.
"""
import json
import logging
from typing import Dict, Any, Optional, List

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from .database.models import ObjectSchemas
    from .database.connection import get_direct_session
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

logger = logging.getLogger(__name__)

class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []

class JSONSchemaValidator:
    """
    Validates JSON data against schemas stored in the database.
    
    Uses direct database queries for efficiency - no caching overhead.
    All crew request schemas must include core required fields.
    """
    
    def __init__(self):
        """Initialize validator."""
        pass
    
    async def get_schema_by_name(self, schema_name: str, db=None) -> Optional[Dict[str, Any]]:
        """Get a specific schema by name directly from database - no caching."""
        if not SQLALCHEMY_AVAILABLE:
            raise SchemaValidationError("SQLAlchemy not available for database operations")
        
        if db is None:
            async with get_direct_session() as db:
                return await self._get_single_schema(schema_name, db)
        else:
            return await self._get_single_schema(schema_name, db)
    
    async def _get_single_schema(self, schema_name: str, db) -> Optional[Dict[str, Any]]:
        """Load a single schema from database by name."""
        try:
            stmt = select(ObjectSchemas).where(ObjectSchemas.name == schema_name)
            result = await db.execute(stmt)
            schema_record = result.scalar_one_or_none()
            
            if schema_record:
                return {
                    'id': schema_record.id,
                    'name': schema_record.name,
                    'object_type': schema_record.object_type,
                    'schema': schema_record.schema_data,
                    'description': schema_record.description,
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to load schema '{schema_name}' from database: {e}")
            raise SchemaValidationError(f"Unable to load schema '{schema_name}': {e}")

    async def get_crew_request_schemas(self, db=None) -> Dict[str, Dict[str, Any]]:
        """Get all crew and gen_crew request schemas for job validation - only used when actually needed."""
        if not SQLALCHEMY_AVAILABLE:
            raise SchemaValidationError("SQLAlchemy not available for database operations")
        
        if db is None:
            async with get_direct_session() as db:
                return await self._get_crew_schemas(db)
        else:
            return await self._get_crew_schemas(db)
    
    async def _get_crew_schemas(self, db) -> Dict[str, Dict[str, Any]]:
        """Load both crew and gen_crew type schemas from database."""
        try:
            # Query for both classic 'crew' and database-driven 'gen_crew' schemas
            stmt = select(ObjectSchemas).where(
                ObjectSchemas.object_type.in_(['crew', 'gen_crew'])
            )
            result = await db.execute(stmt)
            schemas = result.scalars().all()
            
            crew_schemas = {}
            for schema_record in schemas:
                crew_schemas[schema_record.name] = {
                    'id': schema_record.id,
                    'name': schema_record.name,
                    'object_type': schema_record.object_type,
                    'schema': schema_record.schema_data,
                    'description': schema_record.description,
                }
            
            logger.info(f"Loaded {len(crew_schemas)} crew/gen_crew schemas from database")
            return crew_schemas
            
        except Exception as e:
            logger.error(f"Failed to load crew schemas from database: {e}")
            raise SchemaValidationError(f"Unable to load crew schemas: {e}")

    async def _determine_schema_from_job_key(self, job_key: str, db) -> Optional[str]:
        """
        Determine schema name from job_key by checking if a schema with that name exists.
        Direct database lookup - no caching overhead.
        """
        # First try exact match - most common case for both crew and gen_crew
        schema_data = await self._get_single_schema(job_key, db)
        if schema_data and schema_data['object_type'] in ['crew', 'gen_crew']:
            logger.info(f"Found {schema_data['object_type']} schema for job_key '{job_key}' (exact match)")
            return job_key
        
        logger.warning(f"No schema found for job_key: {job_key}")
        return None
        for schema_name, schema_data in self._schema_cache.items():
            schema_content = schema_data.get('schema', {})
            if isinstance(schema_content, dict):
                # Check if this schema is designed for this job_key
                if 'properties' in schema_content and 'job_key' in schema_content['properties']:
                    job_key_property = schema_content['properties']['job_key']
                    if isinstance(job_key_property, dict):
                        # Check if job_key is in enum values
                        if 'enum' in job_key_property and job_key in job_key_property['enum']:
                            return schema_name
                        # Check if job_key matches a const value
                        if 'const' in job_key_property and job_key_property['const'] == job_key:
                            return schema_name
        
        # No schema found for this job_key
        return None
    
    def _validate_core_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate that all core required fields are present.
        These fields are required for ALL crew requests regardless of schema.
        """
        required_core_fields = ['job_key', 'client_user_id', 'actor_type', 'actor_id']
        errors = []
        
        for field in required_core_fields:
            if field not in data:
                errors.append(f"Missing required core field: {field}")
            elif data[field] is None:
                errors.append(f"Core field '{field}' cannot be null")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"Core field '{field}' cannot be empty")
        
        return errors
    
    async def validate_request_data(self, data: Dict[str, Any], schema_name: Optional[str] = None, 
                                  job_key: Optional[str] = None, db=None) -> Dict[str, Any]:
        """
        Validate JSON data against a schema with core field validation.
        
        Args:
            data: The JSON data to validate
            schema_name: Specific schema name to use (optional)
            job_key: Job key to determine schema automatically (optional)
            db: Database session (optional, will create if needed)
            
        Returns:
            Dict containing validation results
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if db is None and SQLALCHEMY_AVAILABLE:
            async with get_direct_session() as db:
                return await self._validate_with_db(data, schema_name, job_key, db)
        else:
            return await self._validate_with_db(data, schema_name, job_key, db)
    
    async def _validate_with_db(self, data: Dict[str, Any], schema_name: Optional[str], 
                               job_key: Optional[str], db) -> Dict[str, Any]:
        """Internal validation method with database session."""
        # Determine schema to use
        if schema_name:
            target_schema_name = schema_name
        elif job_key:
            target_schema_name = await self._determine_schema_from_job_key(job_key, db)
            if not target_schema_name:
                raise SchemaValidationError(f"No schema mapping found for job_key: {job_key}")
        else:
            # Try to extract job_key from data
            job_key_from_data = data.get('job_key')
            if job_key_from_data:
                target_schema_name = await self._determine_schema_from_job_key(job_key_from_data, db)
                if not target_schema_name:
                    raise SchemaValidationError(f"No schema mapping found for job_key: {job_key_from_data}")
            else:
                raise SchemaValidationError("No schema_name provided and no job_key found in data")
        
        # Load schema from database - NO FALLBACKS!
        schema_data = await self.get_schema_by_name(target_schema_name, db)
        if not schema_data:
            raise SchemaValidationError(f"Schema '{target_schema_name}' not found in database")
        
        # Always validate core fields first
        core_errors = self._validate_core_fields(data)
        
        # Validate against JSON schema
        schema_errors = []
        if JSONSCHEMA_AVAILABLE:
            try:
                validate(instance=data, schema=schema_data['schema'])
            except ValidationError as e:
                schema_errors.append(f"Schema validation error: {e.message}")
            except Exception as e:
                schema_errors.append(f"Validation error: {str(e)}")
        else:
            schema_errors.append("JSONSchema library not available - skipping schema validation")
        
        # Combine all errors
        all_errors = core_errors + schema_errors
        
        result = {
            'valid': len(all_errors) == 0,
            'schema_used': target_schema_name,
            'schema_id': schema_data['id'] if schema_data else None,
            'errors': all_errors,
            'validated_data': data if len(all_errors) == 0 else None
        }
        
        if all_errors:
            logger.warning(f"Validation failed for schema '{target_schema_name}': {all_errors}")
        else:
            logger.info(f"Validation successful for schema '{target_schema_name}'")
        
        return result

# Global validator instance
validator = JSONSchemaValidator()

# Convenience functions
async def validate_crew_request(data: Dict[str, Any], job_key: Optional[str] = None, 
                               schema_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to validate crew request data.
    
    Args:
        data: Request data to validate
        job_key: Job key for schema selection
        schema_name: Specific schema name (overrides job_key)
        
    Returns:
        Validation result dictionary
    """
    return await validator.validate_request_data(data, schema_name, job_key)

async def get_available_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all available crew request schemas."""
    return await validator.get_crew_request_schemas()
