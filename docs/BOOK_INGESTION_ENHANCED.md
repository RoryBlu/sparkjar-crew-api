# Book Ingestion Crew v2 Documentation

## Overview

The book ingestion crew processes manuscript images using CrewAI agents with:

- **GPT-4o vision** for high-accuracy OCR
- **Sequential thinking** for complex text resolution
- **Client-specific database storage** (no hardcoded URLs)
- **Context-aware processing** using book metadata
- **Standard CrewAI patterns** (no custom abstractions)

## Architecture

### Components

1. **OCR Multipass Tool** (`src/tools/ocr_multipass_tool.py`)
   - Pass 1: Initial transcription with confidence tracking
   - Pass 2: Context refinement using previous results
   - Pass 3: Sequential thinking for complex sections

2. **Database Storage Tool** (`src/tools/database_storage_tool.py`)
   - Transactional storage to PostgreSQL
   - Automatic embedding generation
   - Duplicate page handling

3. **Page Processor** (`src/utils/page_processor.py`)
   - Orchestrates page-by-page processing
   - Todo list management
   - Error recovery and resumability

4. **Enhanced Crew** (`src/crews/book_ingestion_crew/crew_enhanced.py`)
   - Validates requests
   - Manages async processing
   - Provides detailed results

## Database Schema

### book_ingestions Table
```sql
CREATE TABLE book_ingestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_key TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    language_code TEXT NOT NULL,
    version TEXT NOT NULL,
    page_text TEXT NOT NULL,
    ocr_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(book_key, page_number, version)
);
```

### object_embeddings Table
```sql
CREATE TABLE object_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES book_ingestions(id) ON DELETE CASCADE,
    embedding vector(1536),
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    embeddings_metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Request Schema

```json
{
  "job_id": "string",
  "job_key": "book_ingestion_crew",
  "client_id": "uuid",
  "client_user_id": "uuid",
  "actor_type": "user|synth",
  "actor_id": "uuid",
  "google_drive_folder_path": "string",
  "language": "en|es|fr|de|it|pt|nl|pl|ru|ja|zh",
  "version": "original|translation|draft_v1",
  "page_naming_pattern": "page_###.jpg",
  
  // Optional book context for better OCR
  "book_title": "string",
  "book_author": "string",
  "book_genre": "string",
  "book_time_period": "string",
  "book_location": "string"
}
```

## Setup Instructions

### 1. Set Database Credentials

Store client database URLs in the client_secrets table:
```sql
INSERT INTO client_secrets (client_id, secret_key, secret_value)
VALUES ('vervelyn_publishing_client_id', 'database_url', 'postgresql://...');
```

### 2. Create Database Tables

```bash
python services/crew-api/scripts/create_vervelyn_tables.py
```

### 3. Seed Schema

```bash
python services/crew-api/scripts/seed_book_ingestion_schema.py
```

### 4. Test the System

```bash
python services/crew-api/scripts/test_book_ingestion.py
```

## Usage Example

### API Request

```bash
curl -X POST http://localhost:8000/crew_job \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_key": "book_ingestion_crew",
    "client_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_user_id": "660e8400-e29b-41d4-a716-446655440001",
    "actor_type": "user",
    "actor_id": "770e8400-e29b-41d4-a716-446655440002",
    "google_drive_folder_path": "/Manuscripts/Borges/ElJardin",
    "language": "es",
    "version": "original",
    "book_title": "El Jardín de los Senderos que se Bifurcan",
    "book_author": "Jorge Luis Borges",
    "book_genre": "Fiction",
    "book_time_period": "1940s",
    "book_location": "Argentina"
  }'
```

### Response

```json
{
  "status": "completed",
  "result": {
    "message": "Processed 660 of 660 pages successfully",
    "job_id": "job_20250120_123456",
    "client_id": "550e8400-e29b-41d4-a716-446655440000",
    "book_key": "ElJardin",
    "total_pages": 660,
    "completed_pages": 660,
    "failed_pages": 0,
    "processing_time_seconds": 2145.67,
    "summary": {
      "total": 660,
      "pending": 0,
      "in_progress": 0,
      "completed": 660,
      "failed": 0,
      "progress_percentage": 100.0
    }
  }
}
```

## OCR Strategy

### Pass 1: Initial Transcription
- GPT-4o views image and transcribes text
- Marks unclear sections with [?] or [illegible]
- Tracks confidence levels (HIGH/MEDIUM/LOW)
- Uses book context for proper nouns

### Pass 2: Context Refinement
- Reviews original image with Pass 1 results
- Focuses on unclear sections
- Uses previous page context
- Applies linguistic patterns

### Pass 3: Sequential Thinking (if needed)
- Creates thinking session for complex deduction
- Analyzes letter patterns
- Considers narrative flow
- Makes educated guesses with 90%+ confidence

## Monitoring

### Logs
- Page processing progress
- OCR pass distribution
- Confidence scores
- Processing times

### Database Queries
```sql
-- Check processing status
SELECT book_key, COUNT(*) as pages, 
       MIN(created_at) as started, 
       MAX(created_at) as completed
FROM book_ingestions
GROUP BY book_key;

-- Find low confidence pages
SELECT book_key, page_number, 
       ocr_metadata->>'overall_confidence' as confidence
FROM book_ingestions
WHERE (ocr_metadata->>'overall_confidence')::float < 0.95
ORDER BY page_number;

-- Search for text
SELECT b.page_number, b.file_name, 
       e.chunk_text
FROM object_embeddings e
JOIN book_ingestions b ON e.source_id = b.id
WHERE e.chunk_text ILIKE '%search_term%'
ORDER BY b.page_number, e.chunk_index;
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify VERVELYN_DB_URL is set correctly
   - Check network connectivity to Supabase
   - Ensure tables are created

2. **OCR Accuracy Issues**
   - Add more book context (title, author, time period)
   - Check image quality (minimum 300 DPI)
   - Verify language setting matches manuscript

3. **Processing Interrupted**
   - Crew automatically resumes from last completed page
   - Check todo status in logs
   - Failed pages are logged with error details

4. **Slow Processing**
   - Normal: ~3-5 seconds per page
   - Multi-pass OCR increases accuracy but takes time
   - Monitor GPT-4o API rate limits

## Performance Metrics

- **Accuracy**: 100% target (vs 85-90% single pass)
- **Speed**: 660 pages in ~35 minutes
- **Embeddings**: ~5-10 chunks per page
- **Storage**: ~2KB per page + embeddings

## Future Enhancements

1. **Parallel Processing** (currently sequential for context)
2. **Batch Embedding Generation**
3. **Image Preprocessing** (deskew, denoise)
4. **Multiple Language Support** in single book
5. **Handwriting Style Learning**

## Support

For issues or questions:
- Check logs in Railway dashboard
- Review failed pages in database
- Contact team with job_id for investigation