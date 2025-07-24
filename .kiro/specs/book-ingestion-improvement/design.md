# Book Ingestion Crew V2 Design Document

## Project: Vervelyn Publishing Book Ingestion System
**Date**: 2025-01-20  
**Client**: Vervelyn Publishing  
**Design Version**: 2.0

## 1. Executive Summary

This design document details the implementation approach for enhancing the book ingestion crew with multi-pass OCR, database storage, and embeddings generation. The system follows standard CrewAI patterns where agents use the ImageViewerTool for all image analysis since agents cannot view images directly.

## 2. Architecture Overview

### 2.1 System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Google Drive   │────▶│ Book Ingestion   │────▶│  Client DB      │
│ (Source Images) │     │     Crew         │     │ (PostgreSQL)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐           ┌──────────────┐
                        │ImageViewerTool│           │   Object     │
                        │  (GPT-4o)     │           │ Embeddings   │
                        └──────────────┘           └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  Sequential  │
                        │Thinking Tool │
                        └──────────────┘
```

### 2.2 Component Architecture

```
book_ingestion_crew/
├── crew.py                      # Standard CrewAI kickoff function
├── config/
│   ├── agents_enhanced.yaml     # Agent definitions
│   └── tasks_enhanced.yaml      # Multi-pass OCR as tasks
└── ../tools/
    ├── database_storage_tool.py # Multi-tenant database storage
    ├── image_viewer_tool.py     # CRITICAL: Agents use this to view images
    ├── google_drive_tool.py     # Existing Google Drive tool
    └── sj_sequential_thinking_tool.py # Existing thinking tool
```

## 3. Detailed Component Design

### 3.1 Multi-Pass OCR as Tasks Using ImageViewerTool

**OCR is implemented as CrewAI tasks where agents use the ImageViewerTool to view images. Agents CANNOT view images directly.**

#### Task: ocr_initial_pass
```yaml
ocr_initial_pass:
  description: |
    Perform initial OCR on page {page_number} using the ImageViewerTool.
    File path: {file_path}
    Language: {language}
    
    Use the image_viewer tool with this prompt:
    "You are transcribing a {language} manuscript page {page_number}.
    Book Context:
    - Title: {book_title}
    - Author: {book_author}
    - Time Period: {book_time_period}
    - Location: {book_location}
    
    Instructions:
    1. Transcribe EXACTLY what you see
    2. Use book context to interpret dates, places, and names
    3. Mark unclear text with [?] if partially readable
    4. Mark as [illegible] if completely unreadable
    5. Track confidence levels (HIGH/MEDIUM/LOW)
    
    Return JSON with:
    - transcription: complete text
    - unclear_sections: list of uncertainties
    - overall_confidence: 0.0-1.0
    - metadata: additional details"
  agent: vision_specialist
  expected_output: |
    JSON containing:
    - transcription: full page text
    - unclear_sections: array of unclear parts
    - overall_confidence: confidence score
    - metadata: OCR process details
```

#### Task: ocr_refinement_pass
```yaml
ocr_refinement_pass:
  description: |
    Refine the OCR results for page {page_number} using ImageViewerTool.
    File path: {file_path}
    
    Use the image_viewer tool with this enhanced prompt:
    "Review this transcription against the original image.
    
    Previous transcription:
    {initial_transcription}
    
    Unclear sections to focus on:
    {unclear_sections}
    
    Previous page ending: {previous_page_context}
    
    Using the image and context:
    - Story narrative flow from previous pages
    - Letter shapes and patterns in {language}
    - Common {language} word patterns
    - Logical word relationships
    
    Improve the transcription focusing on unclear sections.
    Return updated JSON with refinements."
  agent: vision_specialist
  context: [ocr_initial_pass]
  expected_output: |
    Refined JSON with:
    - transcription: improved text
    - unclear_sections: remaining uncertainties
    - overall_confidence: updated score
    - changes_made: list of improvements
```

#### Task: ocr_reasoning_pass
```yaml
ocr_reasoning_pass:
  description: |
    Use sequential thinking AND ImageViewerTool to resolve remaining uncertainties.
    Page {page_number}, File path: {file_path}
    
    Current transcription:
    {refined_transcription}
    
    Remaining unclear sections:
    {remaining_unclear}
    
    1. Create a thinking session to analyze the problem
    2. Use image_viewer tool with focused prompts for each unclear section
    3. Document your reasoning process step by step
    
    For each unclear section, use image_viewer with prompts like:
    "Focus on this specific text area: [unclear section]
    Consider: letter patterns, word size, spacing, {language} patterns
    Previous context suggests: [context clues]
    What is the most likely text?"
    
    Combine visual analysis with logical reasoning.
  agent: reasoning_specialist
  context: [ocr_refinement_pass]
  expected_output: |
    Final JSON with:
    - transcription: final text with all deductions
    - confidence: final confidence score  
    - thinking_session_id: session used
    - deductions_made: reasoned corrections
```

### 3.2 ImageViewerTool Enhancement

**The ImageViewerTool is critical because agents cannot view images directly. All image analysis must go through this tool.**

```python
class ImageViewerTool(BaseTool):
    """Tool for viewing images using GPT-4o vision model."""
    
    name = "image_viewer"
    description = "View and analyze images using GPT-4o vision capabilities"
    
    def _run(self, image_path: str, prompt: str, context: dict = None) -> dict:
        """
        View an image and analyze it according to the prompt.
        
        Args:
            image_path: Path to the image file
            prompt: Analysis instructions for GPT-4o
            context: Optional context from previous passes
            
        Returns:
            Structured response based on prompt requirements
        """
        # Load image
        with open(image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
        # Prepare messages for GPT-4o
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        # Add context if provided
        if context:
            context_msg = f"Previous analysis context: {json.dumps(context)}"
            messages[0]["content"].insert(0, {"type": "text", "text": context_msg})
            
        # Call GPT-4o
        response = openai.chat.completions.create(
            model="gpt-4o",  # Must use GPT-4o for vision
            messages=messages,
            max_tokens=4096,
            temperature=0.1  # Low temperature for accuracy
        )
        
        # Parse response as JSON
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"text": response.choices[0].message.content}
```

### 3.3 Database Storage Tool

**File**: `tools/database_storage_tool.py`

```python
class DatabaseStorageTool(BaseTool):
    """Multi-tenant database storage tool."""
    
    name = "database_storage"
    description = "Store transcribed pages and generate embeddings"
    
    def __init__(self, client_user_id: str):
        super().__init__()
        self.client_user_id = client_user_id
        self.client_id = None
        self.db_url = None
        self._init_database()
    
    def _init_database(self):
        """Resolve client_id and get database URL from client_secrets."""
        # Get main database session
        session = get_db_session()
        
        # Resolve client_user_id to client_id
        client_user = session.query(ClientUsers).filter(
            ClientUsers.id == self.client_user_id
        ).first()
        
        if not client_user:
            raise ValueError(f"Client user not found: {self.client_user_id}")
            
        self.client_id = client_user.clients_id
        
        # Get database URL from client_secrets
        secret = session.query(ClientSecrets).filter(
            ClientSecrets.client_id == self.client_id,
            ClientSecrets.secret_key == "database_url"
        ).first()
        
        if not secret:
            raise ValueError(f"Database URL not found for client: {self.client_id}")
            
        self.db_url = secret.secret_value
        session.close()
    
    def _run(self, **kwargs) -> dict:
        """Store page and generate embeddings."""
        # Connect to client database
        engine = create_engine(self.db_url)
        
        with engine.begin() as conn:
            # Store page
            page_id = self._store_page(conn, kwargs)
            
            # Generate embeddings
            embedding_count = self._generate_embeddings(conn, page_id, kwargs)
            
        return {
            "page_id": str(page_id),
            "embedding_count": embedding_count,
            "success": True
        }
```

### 3.4 Embedding Generation Strategy

```python
def _generate_embeddings(self, conn, page_id, page_text, metadata):
    """Generate overlapping embeddings for semantic search."""
    
    # Configuration
    CHUNK_SIZE = 512        # Characters per chunk
    OVERLAP_SIZE = 128      # Overlap between chunks
    
    chunks = []
    start = 0
    
    while start < len(page_text):
        end = start + CHUNK_SIZE
        
        # Extend to word boundary
        if end < len(page_text):
            while end < len(page_text) and page_text[end] != ' ':
                end += 1
        
        chunk_text = page_text[start:end]
        
        # Generate embedding
        embedding = self.embedding_client.create_embedding(chunk_text)
        
        # Store with metadata
        self._store_embedding(
            conn,
            source_id=page_id,
            embedding=embedding,
            chunk_index=len(chunks),
            chunk_text=chunk_text,
            start_char=start,
            end_char=end,
            metadata={
                "book_key": metadata.book_key,
                "page_number": metadata.page_number,
                "language_code": metadata.language_code,
                "version": metadata.version,
                "chunk_index": len(chunks),
                "total_chunks": None,  # Updated after
                "overlap_chars": OVERLAP_SIZE,
                "model": "text-embedding-3-small",
                "dimension": 1536,
                "token_count": self._count_tokens(chunk_text),
                "processing_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        chunks.append(chunk_text)
        start = end - OVERLAP_SIZE  # Overlap for context
    
    return len(chunks)
```

### 3.5 CrewAI Orchestration

**CrewAI handles all orchestration through agents and tasks. The key difference is that agents must use ImageViewerTool for all image operations.**

#### crew.py Implementation
```python
def build_crew(client_user_id: str) -> Crew:
    """Build the crew from YAML configs."""
    agents_cfg = _load_yaml("agents_enhanced.yaml")
    tasks_cfg = _load_yaml("tasks_enhanced.yaml")
    
    # Initialize tools
    google_drive = GoogleDriveTool()
    image_viewer = ImageViewerTool()  # Critical for all image operations
    thinking_tool = SJSequentialThinkingTool()
    storage_tool = DatabaseStorageTool(client_user_id=client_user_id)
    
    # Create agents with appropriate tools
    # IMPORTANT: Agents cannot view images directly - must use ImageViewerTool
    agents = {}
    for name, params in agents_cfg.items():
        if name == "file_manager":
            params["tools"] = [google_drive]
        elif name == "vision_specialist":
            params["tools"] = [image_viewer]  # Primary tool for image analysis
        elif name == "reasoning_specialist":
            params["tools"] = [thinking_tool, image_viewer]  # Both tools needed
        elif name == "data_specialist":
            params["tools"] = [storage_tool]
            
        agents[name] = Agent(**params)
    
    # Create tasks from YAML
    tasks = []
    for task_name, cfg in tasks_cfg.items():
        task = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=agents[cfg["agent"]]
        )
        tasks.append(task)
    
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

def kickoff(inputs: dict, logger=None):
    """Standard CrewAI kickoff - no custom error handling."""
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    crew = build_crew(client_user_id)
    return crew.kickoff(inputs)
```

### 3.6 Security Architecture

#### Client Secret Management
```sql
-- Client database URLs are stored in the database, NOT environment variables
-- This supports multi-tenancy without hardcoding client configurations

INSERT INTO client_secrets (client_id, secret_key, secret_value, created_at)
VALUES (
    '1d1c2154-242b-4f49-9ca8-e57129ddc823',  -- Vervelyn's client_id
    'database_url',
    'postgresql://postgres.xkwzjvmckmgfbpxvqrpn:K6kTX6jGjGi1Nw6W@aws-0-us-east-1.pooler.supabase.com:5432/postgres',
    NOW()
);
```

#### No Environment Variables for Client Data
- ❌ NO `VERVELYN_DB_URL` in environment
- ❌ NO client-specific environment variables
- ✅ ALL client secrets in database
- ✅ Multi-tenant by design

## 4. Data Flow

### 4.1 Request Flow
```
1. API Request → Validation (schema: book_ingestion_crew)
2. Job Creation → Queue for processing
3. Crew Kickoff → Standard CrewAI execution
4. Client Resolution → client_user_id → client_id → database_url
5. Task Execution → Sequential processing by CrewAI
```

### 4.2 Task Execution Flow (CrewAI Managed)
```
1. list_book_files task:
   - File Manager Agent lists all images
   - Extracts page numbers from filenames
   - Outputs sorted file list

2. For each page (CrewAI iteration):
   a. ocr_initial_pass task:
      - Vision Specialist uses ImageViewerTool
      - Tool performs OCR with GPT-4o vision
      - Returns structured JSON with unclear sections
      
   b. ocr_refinement_pass task (if needed):
      - Vision Specialist uses ImageViewerTool again
      - Tool receives previous results as context
      - Focuses on unclear sections
      
   c. ocr_reasoning_pass task (if still unclear):
      - Reasoning Specialist uses BOTH tools:
        * Sequential thinking for reasoning
        * ImageViewerTool for targeted re-examination
      - Combines visual analysis with logical deduction
      
   d. store_page_to_database task:
      - Data Specialist stores final results
      - Generates overlapping embeddings

3. compile_book_results task:
   - Project Manager aggregates results
   - Reports success/failure statistics
```

## 5. Error Handling Strategy

### 5.1 CrewAI Default Error Handling
- CrewAI provides built-in retry logic
- Failed tasks are logged and can be retried
- No custom error handling needed in crew.py

### 5.2 Tool-Level Error Handling
- ImageViewerTool handles image loading failures
- Database tool handles connection failures
- Embedding generation wrapped in transactions
- Failed embeddings don't break page storage

### 5.3 Failure Modes

| Failure Type | Recovery Strategy |
|--------------|-------------------|
| Image Load Failure | Skip page, log error |
| OCR API Timeout | CrewAI retries automatically |
| Database Connection | Tool reconnects with backoff |
| Embedding Generation | Page stored without embeddings |
| Sequential Thinking | Falls back to refinement results |

## 6. Testing Strategy

### 6.1 Test Script
```python
# scripts/test_book_ingestion_v2.py
inputs = {
    "job_key": "book_ingestion_crew",
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "actor_type": "synth",
    "actor_id": "e30fc9f3-57da-4cf0-84e7-ea9188dd5fba",
    "google_drive_folder_path": "sparkjar/vervelyn/castor gonzalez/book 1/",
    "language": "es",
    "output_format": "txt",
    "confidence_threshold": 0.85,
    "book_metadata": {
        "title": "Castor Gonzalez Book 1",
        "author": "Castor Gonzalez",
        "description": "First book manuscript",
        "year": 2024
    }
}
```

### 6.2 Test Coverage
- ImageViewerTool functionality
- Database connection resolution
- Page storage with embeddings
- Multi-pass OCR accuracy
- Sequential thinking integration
- End-to-end workflow

## 7. Performance Considerations

### 7.1 Processing Strategy
- Sequential processing (required for context)
- One page at a time to manage memory
- ImageViewerTool caches image data
- Embeddings generated per page
- Database connections pooled

### 7.2 Resource Management
- Image files cleaned up after processing
- Thinking sessions closed properly
- Database transactions committed promptly
- Memory released between pages

## 8. Railway Deployment

### 8.1 Environment Configuration
```yaml
# Railway environment variables (NO CLIENT-SPECIFIC VARS)
OPENAI_API_KEY: [Already configured]
GOOGLE_DRIVE_CREDENTIALS: [Already configured]
MEMORY_SERVICE_URL: http://memory-internal.railway.internal:8001
DATABASE_URL: [Main Supabase database]
DATABASE_URL_POOLED: [Pooled connection]
DATABASE_URL_DIRECT: [Direct connection]

# Client database URLs: Stored in client_secrets table ONLY
```

### 8.2 Service Updates
- crew-api service: Deploy enhanced book ingestion crew
- No new services needed
- Uses existing infrastructure

### 8.3 Deployment Steps
```bash
# 1. Store client database URL (use actual client_id)
python scripts/store_client_secret.py \
  --client-id 1d1c2154-242b-4f49-9ca8-e57129ddc823 \
  --secret-key database_url \
  --secret-value "postgresql://postgres.xkwzjvmckmgfbpxvqrpn:K6kTX6jGjGi1Nw6W@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# 2. Create database tables in client database
python scripts/create_book_ingestion_tables.py

# 3. Seed object schema
python scripts/seed_book_ingestion_schema.py

# 4. Deploy to Railway (automatic from GitHub push)
git push origin main

# 5. Test with provided values
python scripts/test_book_ingestion_v2.py
```

### 8.4 Health Checks
- ImageViewerTool connectivity to GPT-4o
- Client database connectivity on startup
- Embedding generation capability

## 9. Monitoring & Observability

### 9.1 Metrics
- Pages processed per hour
- OCR confidence scores
- Number of refinement passes needed
- ImageViewerTool response times
- Embedding generation time
- Database write performance

### 9.2 Logging
```python
logger.info("Page processing", extra={
    "client_id": self.client_id,
    "page_number": page_num,
    "ocr_passes": pass_count,
    "confidence": confidence_score,
    "image_viewer_calls": tool_call_count,
    "embeddings_created": embedding_count
})
```

### 9.3 Railway Monitoring
- Use Railway metrics dashboard
- Monitor memory usage during image processing
- Track GPT-4o API rate limits

## 10. Key Design Decisions

### 10.1 What We're Building
- ✅ Standard CrewAI crew with agents and tasks in YAML
- ✅ ImageViewerTool for ALL image operations (agents can't view images)
- ✅ DatabaseStorageTool that resolves client from client_user_id
- ✅ Multi-pass OCR as sequential tasks using ImageViewerTool
- ✅ Client secrets stored in database (multi-tenant support)
- ✅ Simple kickoff function without custom error handling

### 10.2 What We're NOT Building
- ❌ NO direct image viewing by agents
- ❌ NO PageProcessor class (CrewAI is the orchestrator)
- ❌ NO vervelyn_db.py (generic client lookup instead)
- ❌ NO ocr_multipass_tool.py (OCR passes are tasks)
- ❌ NO client-specific environment variables
- ❌ NO custom orchestration logic

### 10.3 Implementation Order

1. **Database Setup** (Day 1)
   - Store client secret in database
   - Create tables in client database
   - Seed object schema

2. **Tool Development** (Day 1-2)
   - Verify ImageViewerTool works with GPT-4o
   - Implement DatabaseStorageTool
   - Test client resolution logic

3. **Crew Configuration** (Day 2)
   - Create agents_enhanced.yaml
   - Create tasks_enhanced.yaml with ImageViewerTool usage
   - Update crew.py

4. **Testing** (Day 3)
   - Test ImageViewerTool with sample pages
   - Verify multi-pass accuracy
   - Check database storage

5. **Deployment** (Day 3-4)
   - Push to GitHub
   - Monitor Railway deployment
   - Run production test

---

**Document Status**: APPROVED AND READY  
**Author**: Senior Development Team  
**Follows**: Standard CrewAI patterns  
**Key Constraint**: Agents use ImageViewerTool for all image operations  
**Estimated Implementation**: 3-4 days