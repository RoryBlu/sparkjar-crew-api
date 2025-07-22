# Book Ingestion Crew - Integration Plan

## Current State Analysis

### ✅ What's Working:
1. **Crew Structure**: Well-organized with agents, tasks, and tools
2. **Google Drive Tool**: Works when given correct path
3. **Basic OCR Tool**: PaddleOCR implementation exists

### ❌ Issues Found:
1. **Path Problem**: Hardcoded path was wrong (case sensitive)
   - Wrong: `"Sparkjar/vervelyn/castor gonzalez/book 1/"`
   - Right: `"0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"`

2. **OCR Quality**: Current PaddleOCR only extracts ~41 words per page
3. **Module Import Issues**: Path problems when running crew

## Proposed Integration

### 1. Enhanced OCR Tool Update
Add our successful nano chunked method to `src/tools/ocr_tool.py`:

```python
def nano_chunked_ocr(self, image_path: str, chunk_size: int = 50, overlap: int = 10) -> str:
    """
    Enhanced OCR using gpt-4.1-nano with overlapping chunks.
    
    Returns JSON result compatible with existing crew expectations.
    """
    # Implementation from our successful test
    # Returns same format as _run() for compatibility
```

### 2. Crew Task Update
Modify the OCR task to use nano chunked method:

```yaml
# In tasks.yaml
process_with_ocr:
  description: >
    Process each image using enhanced nano chunked OCR.
    Use 50-word chunks with 10-word overlap for accuracy.
    Mini validates and merges overlapping sections.
```

### 3. Running the Crew Properly

From crew-api directory:
```bash
cd services/crew-api
python -m src.crews.book_ingestion_crew.main
```

Or create a runner script at project root:
```python
#!/usr/bin/env python3
# Use proper package imports - no sys.path manipulation needed
from sparkjar_crew.services.crew_api.src.crews.book_ingestion_crew.crew import kickoff

inputs = {
    "google_drive_folder_path": "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
    "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
    "job_id": "castor-book-nano-ocr",
    "method": "nano_chunked"  # New parameter
}

result = kickoff(inputs)
```

## Next Steps

1. **Update OCR Tool**: Add nano_chunked_ocr method
2. **Update Crew Config**: Modify tasks.yaml to use new method
3. **Fix Imports**: Ensure proper module paths
4. **Test End-to-End**: Run complete pipeline with verbose output

## Expected Results

- **Coverage**: 95%+ text extraction (vs 15% with PaddleOCR)
- **Cost**: ~20 nano calls + 1-2 mini calls per page
- **Quality**: Validated, merged text without repetition