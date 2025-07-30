# Crews Moved to sparkjar-crews Service

## Purpose
These crew implementations were moved from `sparkjar-crew-api/src/crews/` to `sparkjar-crews/crews/` as part of the architecture cleanup to properly separate concerns between the API service and crew implementations.

## Architecture Decision
According to the architecture cleanup requirements:
- **sparkjar-crew-api** should focus on API endpoints, job management, and orchestration
- **sparkjar-crews** should contain all crew implementations and be independently scalable
- Services should communicate via HTTP/gRPC interfaces, not direct imports

## Crews Moved
All crew directories from `src/crews/` were archived here after being moved to `sparkjar-crews/crews/`:

- `blog_writer_hierarchical/` - Blog writing crew with hierarchical memory
- `book_ingestion_crew/` - Book manuscript ingestion and OCR processing
- `book_translation_crew/` - Book translation crew (unique to crew-api, moved to sparkjar-crews)
- `contact_form/` - Contact form processing crew
- `entity_research_crew/` - Entity research and analysis crew
- `gen_crew/` - General purpose crew template
- `memory_import_crew/` - Memory data import crew
- `memory_maker_crew/` - Memory creation and processing crew

## Migration Date
Archived on: $(date)

## Next Steps
1. Update crew-api to use HTTP calls to sparkjar-crews service instead of direct imports
2. Remove crew implementation dependencies from crew-api requirements
3. Implement crew service client in crew-api for remote crew execution