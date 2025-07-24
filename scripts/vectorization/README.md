# Crew Job Event Vectorization

This directory contains scripts for vectorizing crew job events for similarity search and analysis.

## Current Approach: Supabase with pgvector

All crew job events are now vectorized and stored in the **Supabase `object_embeddings` table**, NOT in ChromaDB.

### Why Supabase over ChromaDB?

1. **Data Consistency**: Keep embeddings alongside the source data in PostgreSQL
2. **Multi-tenant Support**: Built-in client_id support for data isolation
3. **Unified Storage**: No need to sync between databases
4. **Better Integration**: Direct SQL queries and joins with other data
5. **Cost Efficiency**: No separate vector database to maintain

### The `object_embeddings` Table

```sql
CREATE TABLE object_embeddings (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL,
    sj_table TEXT NOT NULL,           -- "crew_job_event"
    sj_column TEXT NOT NULL,          -- "event_data"
    vectorize_text TEXT NOT NULL,     -- The searchable text
    sj_column_embedding vector(1536), -- Vector embedding (adjusts to provider)
    column_metadata JSONB,            -- Event metadata
    create_time TIMESTAMP WITH TIME ZONE
);
```

## Usage

### Basic Vectorization

```bash
# Vectorize job events from a JSON file
python scripts/vectorization/vectorize_job_events.py /path/to/job_result.json

# Or use default location (/tmp/job_result.json)
python scripts/vectorization/vectorize_job_events.py
```

### Embedding Providers

The script automatically uses the provider configured in `.env`:

```bash
# For OpenAI embeddings (1536 dimensions)
EMBEDDING_PROVIDER=openai

# For custom embeddings (768 dimensions) 
EMBEDDING_PROVIDER=custom
```

### What Gets Vectorized?

For each crew job event:
1. **Event Type**: The type of event (e.g., "agent_action", "task_complete")
2. **Event Data**: Key fields like message, thought, action, observation, error
3. **Metadata**: Timestamps, agent names, task names, status
4. **Context**: Job ID, event index, and other relevant metadata

### Example Event Document

```
Event Type: agent_action
Time: 2024-01-15T10:30:00Z
agent_name: Research Agent
action: Searching for company information
message: Found relevant data about the target company
status: success
```

## Similarity Search

The script includes built-in similarity search testing:

```python
# Test queries automatically run after vectorization:
- "research findings"
- "agent task execution" 
- "error or failure"
```

Results show similar events with cosine similarity scores (0.0 to 1.0).

## Integration with Crew API

The crew API's `VectorizationService` also uses this same approach:
- Stores in `object_embeddings` table
- Uses configured embedding provider
- Maintains consistency across the system

## Migration from ChromaDB

If you have existing data in ChromaDB:
1. The old ChromaDB script has been removed
2. All new vectorization uses Supabase
3. ChromaDB remains for CrewAI's internal memory only
4. Application data should be in Supabase for consistency

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root
2. **Connection Errors**: Check DATABASE_URL_DIRECT in .env
3. **Dimension Mismatch**: Verify EMBEDDING_PROVIDER matches existing data
4. **No Results**: Check client_id consistency and similarity threshold

### Debugging

Enable verbose output:
```bash
python -u scripts/vectorization/vectorize_job_events.py
```

Check the database directly:
```sql
-- Count embeddings for a job
SELECT COUNT(*) FROM object_embeddings 
WHERE column_metadata->>'job_id' = 'your-job-id';

-- View recent embeddings
SELECT id, sj_table, vectorize_text, column_metadata 
FROM object_embeddings 
ORDER BY create_time DESC 
LIMIT 10;
```