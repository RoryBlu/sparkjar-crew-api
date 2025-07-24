# CrewAI API Service

The CrewAI API service is the main orchestration layer for executing CrewAI crews with memory, vector storage, and dynamic crew generation capabilities.

## Overview

This FastAPI-based service provides:
- Asynchronous execution of CrewAI crews via REST API
- JWT-based authentication with scope validation
- Job tracking and status management
- Integration with remote ChromaDB for vector storage
- Dynamic crew generation based on templates
- Schema validation for crew configurations

## Quick Start

```bash
# Setup environment
python setup.py

# Start development server
.venv/bin/python main.py
```

## Architecture

### Core Components

- **API Layer** (`src/api/`): FastAPI endpoints and authentication
- **Crew System** (`src/crews/`): Crew handlers and base classes
- **Services** (`src/services/`): Business logic for jobs, crews, validation
- **Database** (`src/database/`): SQLAlchemy models and connections

### Key Features

1. **Asynchronous Job Execution**: Jobs are queued and executed in background tasks
2. **Schema Validation**: Request data validated against schemas in `object_schemas` table
3. **Authentication**: All endpoints require bearer token with `sparkjar_internal` scope
4. **Crew Registration**: Crews registered in central registry with handler pattern

## API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for detailed endpoint documentation.

## Deployment

The service is designed to run on Railway with:
- PostgreSQL database (Supabase for pgvector support)
- Environment variables configured via Railway
- Health checks at `/health` endpoint

## Environment Variables

Key configuration:
- `DATABASE_URL`: PostgreSQL connection string
- `CHROMA_URL`: ChromaDB server URL
- `API_SECRET_KEY`: JWT signing key
- `HF_API_KEY`: Hugging Face API key