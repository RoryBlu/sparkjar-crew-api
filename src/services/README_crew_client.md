# CrewClient - HTTP Client for SparkJAR Crews Service

The `CrewClient` is a robust HTTP client for communicating with the SparkJAR Crews Service. It provides crew execution capabilities with comprehensive error handling, retry logic, and request tracing.

## Features

- **Async HTTP Client**: Built on httpx with connection pooling
- **Automatic Retry**: Exponential backoff for transient failures
- **JWT Authentication**: Automatic token management and refresh
- **Request Tracing**: Unique request IDs for distributed tracing
- **Structured Logging**: Comprehensive metrics and error logging
- **Error Handling**: Specific exceptions for different error types
- **Connection Pooling**: Efficient connection reuse and management

## Quick Start

```python
from services.crew_client import CrewClient
import asyncio

async def main():
    client = CrewClient()
    
    try:
        # Execute a crew
        result = await client.execute_crew(
            crew_name="memory_maker_crew",
            inputs={
                "text_content": "Analyze this conversation",
                "actor_type": "human",
                "actor_id": "user-123",
                "client_user_id": "client-456"
            }
        )
        
        if result["success"]:
            print(f"Crew executed successfully: {result['result']}")
        else:
            print(f"Crew execution failed: {result['error']}")
            
    finally:
        await client.close()

asyncio.run(main())
```

## Configuration

The client can be configured using `CrewClientConfig`:

```python
from services.crew_client import CrewClient
from services.crew_client_config import CrewClientConfig

config = CrewClientConfig(
    connect_timeout=10.0,      # Connection timeout
    read_timeout=600.0,        # Read timeout (10 minutes)
    max_retries=5,             # Maximum retry attempts
    retry_max_wait=30.0,       # Maximum wait between retries
    default_crew_timeout=600   # Default crew execution timeout
)

client = CrewClient(config=config)
```

## API Methods

### execute_crew(crew_name, inputs, timeout=None, request_id=None)

Execute a crew with the provided inputs.

**Parameters:**
- `crew_name` (str): Name of the crew to execute
- `inputs` (dict): Input parameters for the crew
- `timeout` (int, optional): Execution timeout in seconds
- `request_id` (str, optional): Request ID for tracing

**Returns:**
- `dict`: Execution result with success status, result data, and timing information

**Raises:**
- `CrewNotFoundError`: If the crew doesn't exist
- `CrewExecutionError`: If crew execution fails
- `CrewServiceUnavailableError`: If the service is unavailable

### list_crews(request_id=None)

List all available crews from the service.

**Parameters:**
- `request_id` (str, optional): Request ID for tracing

**Returns:**
- `list`: List of available crew names

### health_check(request_id=None)

Check the health status of the crews service.

**Parameters:**
- `request_id` (str, optional): Request ID for tracing

**Returns:**
- `dict`: Health status information

## Error Handling

The client provides specific exception types for different error scenarios:

```python
from services.crew_client_exceptions import (
    CrewClientError,           # Base exception
    CrewNotFoundError,         # Crew doesn't exist
    CrewExecutionError,        # Crew execution failed
    CrewServiceUnavailableError # Service unavailable
)

try:
    result = await client.execute_crew("my_crew", {"input": "data"})
except CrewNotFoundError:
    print("Crew not found")
except CrewExecutionError as e:
    print(f"Crew execution failed: {e}")
except CrewServiceUnavailableError:
    print("Service is currently unavailable")
except CrewClientError as e:
    print(f"Client error: {e}")
```

## Retry Logic

The client automatically retries requests for transient failures:

- **Connection errors**: Network connectivity issues
- **Timeout errors**: Request timeouts
- **Service errors**: 5xx HTTP status codes
- **Rate limiting**: 429 Too Many Requests

Retry behavior:
- Maximum 3 attempts by default
- Exponential backoff (1s, 2s, 4s, ...)
- Maximum 10 second wait between retries

## Authentication

The client automatically handles JWT authentication:

- Uses `get_internal_token()` from `sparkjar_shared.auth`
- Caches tokens for 23 hours
- Automatically refreshes tokens 5 minutes before expiry
- Includes proper scopes for crew execution

## Request Tracing

All requests include tracing information:

- Unique request IDs for correlation
- Request/response timing metrics
- Structured logging with context
- Error tracking and debugging

## Connection Pooling

Efficient HTTP connection management:

- Maximum 20 concurrent connections
- 10 keepalive connections
- 30 second keepalive expiry
- Automatic connection cleanup

## Logging

Comprehensive structured logging:

```python
# Request logging
INFO:services.crew_client:Making POST request to /execute_crew
INFO:services.crew_client:Request completed: POST /execute_crew - 200

# Execution logging
INFO:services.crew_client:Crew 'memory_maker_crew' executed successfully in 45.23s

# Error logging
ERROR:services.crew_client:Crew 'test_crew' execution failed: Invalid input format
```

## Testing

Run the unit tests:

```bash
cd _reorg/sparkjar-crew-api
source .venv/bin/activate
python -m pytest tests/test_crew_client.py -v
```

Run integration tests (requires running crews service):

```bash
cd _reorg/sparkjar-crew-api
source .venv/bin/activate
python test_crew_client_integration.py
```

## Global Client Instance

Use the global client instance for convenience:

```python
from services.crew_client import get_crew_client, close_crew_client

# Get global instance
client = get_crew_client()

# Use client...
result = await client.execute_crew("my_crew", inputs)

# Cleanup when done
await close_crew_client()
```

## Environment Variables

Configure the client using environment variables:

- `CREWS_SERVICE_URL`: Base URL for the crews service (default: http://localhost:8001)
- `API_SECRET_KEY`: JWT secret key for authentication
- `ENVIRONMENT`: Environment setting (affects logging and behavior)

## Best Practices

1. **Always close the client**: Use `await client.close()` or context managers
2. **Handle specific exceptions**: Catch appropriate exception types
3. **Use request IDs**: Provide request IDs for better tracing
4. **Configure timeouts**: Set appropriate timeouts for your use case
5. **Monitor logs**: Use structured logging for debugging and monitoring