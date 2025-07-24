# Kiro Project Settings

## File References
When working with this codebase, these are the key files to reference:

### Core Architecture
- `#[[file:README.md]]` - Main project overview
- `#[[file:README_MONOREPO.md]]` - Monorepo structure
- `#[[file:STATUS.md]]` - Current project status
- `#[[file:docker-compose.yml]]` - Service orchestration

### Main Services
- `#[[file:services/crew-api/main.py]]` - Primary API entry point
- `#[[file:services/crew-api/src/api/main.py]]` - API routes
- `#[[file:services/memory-service/mcp_server.py]]` - Memory service
- `#[[file:services/mcp-registry/main.py]]` - Registry service

### Database & Models
- `#[[file:shared/database/models.py]]` - Shared database models
- `#[[file:services/crew-api/src/database/models.py]]` - API-specific models
- `#[[file:shared/schemas/memory_schemas.py]]` - Memory schemas

### Configuration
- `#[[file:.env.example]]` - Environment variables template
- `#[[file:shared/config/config.py]]` - Shared configuration
- `#[[file:services/crew-api/src/config.py]]` - API configuration

### Testing
- `#[[file:services/crew-api/tests/]]` - Main test suite
- `#[[file:pytest.ini]]` - Test configuration
- `#[[file:conftest.py]]` - Test fixtures

### Documentation
- `#[[file:docs/API.md]]` - API documentation
- `#[[file:docs/EMBEDDING_SYSTEM.md]]` - Embedding system docs
- `#[[file:services/crew-api/docs/DEPLOYMENT_READINESS_CHECKLIST.md]]` - Deployment criteria

## Common Tasks

### Running Tests
```bash
# Run all tests
pytest

# Run specific service tests
cd services/crew-api && pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Starting Services
```bash
# All services
docker-compose up

# Specific service
docker-compose up crew-api

# Development mode
cd services/crew-api && python main.py
```

### Database Operations
```bash
# Create schema
python scripts/create_database_schema.py

# Run migrations
python scripts/migrate_to_pgvector.py

# Inspect schema
python scripts/inspect_db_schema.py
```