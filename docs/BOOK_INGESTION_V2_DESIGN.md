# Book Ingestion Crew V2 Design Document

## Overview

Design for a CrewAI-based book ingestion system that follows standard patterns without unnecessary abstractions.

## Key Design Principles

1. **Use CrewAI as intended** - Agents and tasks in YAML, simple kickoff function
2. **No client-specific code** - Use database lookups for client configuration
3. **OCR passes are tasks, not tools** - Each pass is a separate task in the workflow
4. **Let CrewAI orchestrate** - No custom PageProcessor or orchestration logic

## Request Schema

The crew receives this standard request:
```json
{
  "job_key": "book_ingestion_crew",
  "client_user_id": "uuid",  // User within client org
  "actor_type": "synth|human",
  "actor_id": "uuid",
  "google_drive_folder_path": "path/to/images/",
  "language": "es|en|fr|de|it",
  "output_format": "txt|md|json",
  "confidence_threshold": 0.85,
  "book_metadata": {
    "title": "Book Title",
    "author": "Author Name",
    "description": "Description",
    "year": 2024
  }
}
```

## Database Design

### Client Database Resolution
1. Request contains `client_user_id`
2. Look up `client_users` table to get `clients_id`
3. Look up `client_secrets` table with `clients_id` to get `database_url`
4. Connect to client-specific database

### Tables in Client Database
```sql
-- Stores transcribed pages
CREATE TABLE book_ingestions (
    id UUID PRIMARY KEY,
    book_key TEXT NOT NULL,        -- From folder path
    page_number INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    language_code TEXT NOT NULL,
    version TEXT DEFAULT 'original',
    page_text TEXT NOT NULL,
    ocr_metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Stores embeddings for search
CREATE TABLE object_embeddings (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES book_ingestions(id),
    embedding vector(1536),
    chunk_index INTEGER,
    chunk_text TEXT,
    start_char INTEGER,
    end_char INTEGER,
    embeddings_metadata JSONB,
    created_at TIMESTAMP
);
```

## Agent Architecture

### 1. File Manager Agent
- **Role**: Manage Google Drive operations
- **Tools**: google_drive_tool
- **Tasks**: List files, download images

### 2. Vision Specialist Agent  
- **Role**: OCR using GPT-4o vision
- **Tools**: image_viewer (GPT-4o)
- **Tasks**: Initial OCR pass, refinement pass

### 3. Reasoning Specialist Agent
- **Role**: Resolve complex text using reasoning
- **Tools**: sj_sequential_thinking, image_viewer
- **Tasks**: Complex text resolution when needed

### 4. Data Specialist Agent
- **Role**: Store data and generate embeddings
- **Tools**: database_storage
- **Tasks**: Store pages, generate embeddings

### 5. Project Manager Agent
- **Role**: Compile results and reporting
- **Tools**: None
- **Tasks**: Final summary and quality check

## Task Workflow

```yaml
1. list_files_task:
   - List all files from Google Drive folder
   - Extract page numbers from filenames
   - Sort by page number
   - Output: File list with IDs

2. process_page_initial:
   - For each page: Download and OCR
   - Use book metadata for context
   - Mark unclear sections
   - Output: Initial transcription

3. refine_unclear_text:
   - If confidence < threshold
   - Re-examine with previous page context
   - Focus on unclear sections
   - Output: Refined transcription

4. resolve_complex_text:
   - If still unclear after refinement
   - Use sequential thinking tool
   - Document reasoning process
   - Output: Final transcription

5. store_page_data:
   - Store to client database
   - Generate overlapping embeddings
   - Output: Storage confirmation

6. compile_results:
   - Summarize all pages processed
   - Report any failures
   - Calculate average confidence
   - Output: Final report
```

## Tool Design

### DatabaseStorageTool
```python
class DatabaseStorageTool(BaseTool):
    # Takes client_user_id in constructor
    # Resolves to client_id via database lookup
    # Gets database_url from client_secrets
    # Stores pages and embeddings
```

### Key Features:
- No hardcoded client names or URLs
- Lazy database connection
- Transactional safety
- Automatic embedding generation

## Implementation Notes

1. **crew.py** - Standard pattern:
   ```python
   def kickoff(inputs: dict, logger=None):
       client_user_id = inputs.get("client_user_id")
       crew = build_crew(client_user_id)
       return crew.kickoff(inputs)
   ```

2. **No custom orchestration** - CrewAI handles:
   - Task sequencing
   - Error handling  
   - Progress tracking
   - Result compilation

3. **Configuration in YAML** - All agent/task definitions in config files

4. **Database secrets** - Stored in client_secrets table, not environment

## Testing Approach

1. Store client database URL in client_secrets
2. Create tables in client database
3. Run crew with test Google Drive folder
4. Verify pages stored with embeddings

## Benefits of This Design

- ✅ Follows CrewAI patterns exactly
- ✅ No client-specific code or environment variables
- ✅ Multi-tenant by design
- ✅ Easy to maintain and extend
- ✅ Clear separation of concerns

## What We're NOT Doing

- ❌ No PageProcessor class (CrewAI is the orchestrator)
- ❌ No vervelyn_db.py (use generic client lookup)
- ❌ No multi-pass OCR tool (use tasks instead)
- ❌ No custom error handling (CrewAI handles it)
- ❌ No hardcoded client configurations