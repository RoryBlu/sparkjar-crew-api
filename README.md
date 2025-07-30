# sparkjar-crew-api

SparkJAR Crew API - REST API Gateway for orchestrating distributed CrewAI crews.

## Overview

This service acts as the main API gateway for the SparkJAR platform, providing:
- Asynchronous crew job execution via remote crews service
- Job status tracking and results storage
- Feature flag-based routing between local and remote execution
- Authentication and authorization
- Integration with memory service, thinking service, and MCP registry
- Chat API for interactive AI conversations

## Architecture

The API service no longer contains crew implementations. Instead, it:
1. Receives crew execution requests
2. Checks feature flags to determine routing
3. Forwards requests to the remote crews service via HTTP
4. Tracks job status in the database
5. Returns results to clients

## Quick Start

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install sparkjar-shared as editable
pip install -e ../sparkjar-shared

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Crew Management
- `POST /crew_job` - Queue a crew for execution
- `GET /crew_job/{job_id}` - Get job status and results
- `POST /vectorize_job/{job_id}` - Create embeddings for job events
- `POST /search_vectors` - Vector similarity search

### Feature Flag Management (Admin)
- `GET /admin/feature-flags` - View all feature flags
- `POST /admin/feature-flags` - Update a feature flag
- `POST /admin/feature-flags/reset-metrics` - Reset usage metrics

### Chat API
- `POST /chat` - Send a chat message
- `POST /chat/stream` - Stream chat responses
- `GET /chat/session/{session_id}` - Get session history
- `DELETE /chat/session/{session_id}` - Delete a session

### Health & Testing
- `GET /health` - Service health check
- `GET /test_chroma` - Test ChromaDB connectivity
- `POST /validate_schema` - Validate JSON against stored schemas

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://...
DATABASE_URL_POOLED=postgresql://...
DATABASE_URL_DIRECT=postgresql://...

# Authentication
API_SECRET_KEY=your-secret-key

# Service URLs
CREWS_SERVICE_URL=http://localhost:8001  # Remote crews service
MEMORY_SERVICE_URL=http://localhost:8002
THINKING_SERVICE_URL=http://localhost:8004
MCP_REGISTRY_URL=http://localhost:8003

# Feature Flags (JSON format)
FEATURE_FLAGS='{"use_remote_crews": false}'

# Or individual flags
FEATURE_FLAG_USE_REMOTE_CREWS_MEMORY_MAKER_CREW=true
FEATURE_FLAG_ENABLE_REMOTE_CREW_FALLBACK=false

# External Services
CHROMA_URL=http://chroma:8000
OPENAI_API_KEY=your-openai-key
```

## Feature Flags

The system uses feature flags to control crew execution routing:

- `use_remote_crews` - Route ALL crews to remote service
- `use_remote_crews_<crew_name>` - Route specific crew to remote service
- `enable_remote_crew_fallback` - Fall back to local if remote fails (deprecated)

Example: Enable remote execution for memory_maker_crew:
```bash
export FEATURE_FLAG_USE_REMOTE_CREWS_MEMORY_MAKER_CREW=true
```

## Crew Execution Flow

1. Client sends POST to `/crew_job`
2. Job is created in database with status "queued"
3. Background task checks feature flags:
   - If remote enabled: Calls crews service via HTTP
   - If remote disabled: Returns error (local execution removed)
4. Job status updated to "running"
5. Results stored in database
6. Client polls GET `/crew_job/{job_id}` for results

## Available Crews

Crews are now hosted in the separate sparkjar-crews service:
- `memory_maker_crew` - Analyzes text and creates memories
- `entity_research_crew` - Researches entities via web search
- `book_ingestion_crew` - Ingests books from Google Drive
- `book_translation_crew` - Translates books to other languages

## Authentication

All endpoints (except health checks) require JWT bearer token:
```
Authorization: Bearer <token>
```

Tokens must include scope: `sparkjar_internal`

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black src/ tests/
isort src/ tests/
mypy src/
```

### Adding New Features
1. Update feature flags in `src/services/feature_flags.py`
2. Add new endpoints in `src/api/main.py`
3. Update job service if needed
4. Add tests
5. Update this README

## Deployment

The service is designed to run on Railway with:
- PostgreSQL database (Supabase)
- Remote crews service
- Memory and thinking services
- ChromaDB for vector storage

See `docs/DEPLOYMENT.md` for detailed deployment instructions.

## Troubleshooting

### Crews Not Executing
1. Check feature flags: GET `/admin/feature-flags`
2. Verify crews service is running: `curl http://localhost:8001/health`
3. Check logs for connection errors
4. Ensure JWT token has correct scope

### Database Connections
- Service uses connection pooling
- Direct connections for job updates
- See `src/database/connection.py` for configuration

### Memory Errors
- Verify MEMORY_SERVICE_URL is correct
- Check memory service health
- Ensure actor context is provided in crew inputs