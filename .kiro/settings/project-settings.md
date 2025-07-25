# Kiro Project Settings

## File References
When working with this codebase, these are the key files to reference:

### Core Architecture
- `#[[file:README.md]]` - Main project overview
- `#[[file:REQUIREMENTS_UPDATE_SUMMARY.md]]` - Latest dependency updates
- `#[[file:Dockerfile]]` - Main Docker configuration
- `#[[file:Dockerfile.standalone]]` - Standalone service deployment
- `#[[file:Dockerfile.local]]` - Local development setup

### Main Entry Points
- `#[[file:main.py]]` - Primary API entry point
- `#[[file:src/api/main.py]]` - FastAPI routes and endpoints
- `#[[file:src/chat/api/routes.py]]` - Chat system routes

### Database & Models
- `#[[file:src/database/models.py]]` - Database models
- `#[[file:src/database/connection.py]]` - Database connectivity
- `#[[file:sql/create_book_ingestion_tables.sql]]` - Book ingestion schema
- `#[[file:sql/object_schemas_seed_sql.sql]]` - Schema seeds

### Configuration
- `#[[file:src/config.py]]` - Main API configuration
- `#[[file:src/chat/config.py]]` - Chat system configuration
- `#[[file:requirements.txt]]` - Python dependencies (CrewAI 0.148.0)

### Crews
- `#[[file:src/crews/base.py]]` - Base crew handler interface
- `#[[file:src/crews/gen_crew/gen_crew_handler.py]]` - Dynamic crew generation
- `#[[file:src/crews/book_ingestion_crew/book_ingestion_crew_handler.py]]` - Book processing
- `#[[file:src/crews/memory_maker_crew/memory_maker_crew_handler.py]]` - Memory extraction

### Services
- `#[[file:src/services/job_service.py]]` - Job lifecycle management
- `#[[file:src/services/crew_service.py]]` - Crew execution
- `#[[file:src/services/json_validator.py]]` - Schema validation
- `#[[file:src/services/vectorization_service.py]]` - Embedding generation

### Chat System
- `#[[file:src/chat/services/conversation_manager.py]]` - Conversation handling
- `#[[file:src/chat/services/session_manager.py]]` - Session management
- `#[[file:src/chat/clients/memory_service.py]]` - Memory integration
- `#[[file:src/chat/clients/thinking_service.py]]` - Sequential thinking

### Tools
- `#[[file:src/tools/README_SJ_TOOLS.md]]` - Tool documentation
- `#[[file:src/tools/sj_memory_tool_hierarchical.py]]` - Hierarchical memory
- `#[[file:src/tools/ocr_tool.py]]` - OCR via NVIDIA API
- `#[[file:src/tools/google_drive_tool.py]]` - Google Drive integration

### Testing
- `#[[file:tests/]]` - Main test suite
- `#[[file:tests/conftest.py]]` - Test fixtures
- `#[[file:run_tests.sh]]` - Test execution script

### Documentation
- `#[[file:docs/API_DOCUMENTATION.md]]` - API documentation
- `#[[file:docs/CHAT_API_DOCUMENTATION.md]]` - Chat API docs
- `#[[file:docs/DEPLOYMENT_READINESS_CHECKLIST.md]]` - Deployment criteria
- `#[[file:docs/tools/OCR_TOOL_README.md]]` - OCR tool documentation

## Common Tasks

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (CrewAI 0.148.0)
pip install --upgrade pip
pip install -r requirements.txt

# Quick setup (if available)
python setup.py
```

### Running Tests
```bash
# Run all tests
./run_tests.sh

# Run specific test files
pytest tests/test_config.py -v

# Run with coverage
pytest --cov=src tests/

# Test chat system
python scripts/test_chat_system.py
```

### Starting Services
```bash
# Development mode (recommended)
.venv/bin/python main.py

# Using Docker (standalone)
docker build -f Dockerfile.standalone -t sparkjar-crew-api .
docker run -p 8000:8000 --env-file .env sparkjar-crew-api

# Local Docker development
docker build -f Dockerfile.local -t sparkjar-crew-api:local .
docker run -p 8000:8000 -v $(pwd):/app --env-file .env sparkjar-crew-api:local
```

### Database Operations
```bash
# Create book ingestion tables
psql $DATABASE_URL < sql/create_book_ingestion_tables.sql

# Seed schemas
psql $DATABASE_URL < sql/object_schemas_seed_sql.sql

# Seed specific schemas
python scripts/seed_book_ingestion_schema.py
python scripts/seed_blog_writing_schemas.py
python scripts/seed_contact_form_schema.py
```

### Crew Operations
```bash
# Test crew directly
python src/crews/entity_research_crew/main.py OpenAI --entity_domain technology

# Execute book ingestion
python execute_book_ingestion_crew.py

# Monitor book ingestion
python scripts/book_ingestion_utils/monitor_book_ingestion.py
```

### Utility Scripts
```bash
# Generate test token
python generate_test_token.py

# Vectorize job events
.venv/bin/python scripts/vectorize_job_openai.py --job-id <job_id>

# Test system integration
python scripts/test_system_integration.py

# Validate requirements
python scripts/validate_requirements.py
```

### Development Utilities
```bash
# Check ChromaDB connection
curl http://localhost:8000/test_chroma

# Health check
curl http://localhost:8000/health

# Test OCR functionality
python src/utils/ocr_example.py
```

## Current State (July 2025)

### Dependency Status
- ✅ CrewAI updated to 0.148.0 (latest)
- ✅ All dependency conflicts resolved
- ✅ ChromaDB configured for client mode
- ✅ OCR using NVIDIA API (no local paddleocr)

### Deployment Readiness
- ❌ NOT READY - Tests failing (3/15 passing)
- ❌ Virtual environment needs setup
- ❌ Configuration tests need updates
- ✅ Documentation comprehensive
- ✅ API structure sound

### Active Crews
1. **gen_crew** - Dynamic crew generation
2. **book_ingestion_crew** - Book processing with OCR
3. **memory_maker_crew** - Text analysis and memory extraction
4. **entity_research_crew** - Entity research and analysis

### Key Environment Variables
```bash
# Required for operation
CHROMA_URL=http://your-chromadb-server:8000
DATABASE_URL=postgresql://user:pass@host/db
API_SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
NVIDIA_OCR_ENDPOINT=your-nvidia-endpoint

# Optional
EMBEDDING_PROVIDER=openai  # or custom
MCP_REGISTRY_URL=http://mcp-registry:8000
```