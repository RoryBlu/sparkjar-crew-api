# sparkjar-crew-api

SparkJAR Crew API - REST API for orchestrating CrewAI crews.

## Overview

This service provides:
- Asynchronous crew job execution
- Job status tracking and results
- Authentication and authorization
- Integration with memory service and MCP registry

## Quick Start

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

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

### Health & Testing
- `GET /health` - Service health check
- `GET /test_chroma` - Test ChromaDB connectivity
- `POST /validate_schema` - Validate JSON against stored schemas

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://...
DATABASE_URL_POOLED=postgresql://...

# Authentication
API_SECRET_KEY=your-secret-key

# External Services
CHROMA_URL=http://chroma.railway.internal:8000
MCP_REGISTRY_URL=http://mcp-registry.railway.internal:8001
MEMORY_SERVICE_URL=http://memory-internal.railway.internal:8001

# OpenAI
OPENAI_API_KEY=your-openai-key

# Embedding Configuration
EMBEDDING_PROVIDER=custom
EMBEDDINGS_API_URL=http://embeddings.railway.internal:8000
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

## Docker

```bash
# Build image
docker build -t sparkjar-crew-api .

# Run container
docker run -p 8000:8000 --env-file .env sparkjar-crew-api
```

## Notes

- Extracted from sparkjar-crew monorepo
- Requires PostgreSQL with pgvector extension
- Integrates with ChromaDB for vector storage
- JWT authentication required for all endpoints