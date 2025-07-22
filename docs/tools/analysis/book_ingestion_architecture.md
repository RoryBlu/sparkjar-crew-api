# Book Ingestion Architecture

## Current State
- **OCR Tool**: `/src/tools/ocr_tool.py` - existing PaddleOCR integration
- **Standalone Scripts**: Various test scripts for nano chunked OCR
- **Missing**: Proper crew integration and book ingestion workflow

## Proposed Architecture

### 1. Enhanced OCR Tool
**Location**: `src/tools/ocr_tool.py`
**Responsibility**: 
- Keep existing PaddleOCR capability for compatibility
- Add new `nano_chunked_ocr()` method using gpt-4.1-nano
- Return structured results with confidence metrics

```python
class OCRTool(BaseTool):
    def nano_chunked_ocr(self, image_path: str, chunk_size: int = 50) -> dict:
        """New method using gpt-4.1-nano chunked strategy."""
        # Implementation from our successful test
        
    def _run(self, image_path: str, method: str = "paddleocr") -> str:
        """Enhanced to support multiple OCR methods."""
        if method == "nano_chunked":
            return self.nano_chunked_ocr(image_path)
        else:
            return self.existing_paddleocr_logic()
```

### 2. Book Ingestion Crew
**Location**: `src/crews/book_ingestion_crew/`
**Structure**:
```
book_ingestion_crew/
├── main.py              # Crew orchestration
├── agents.py            # Specialized agents
├── tasks.py             # Task definitions
└── tools.py             # Crew-specific tools
```

**Workflow**:
1. **Scanner Agent**: Discovers pages in Google Drive folder
2. **OCR Agent**: Processes images using nano chunked OCR
3. **Quality Agent**: Validates and improves transcriptions
4. **Assembly Agent**: Combines pages into complete manuscript
5. **Storage Agent**: Saves results back to Google Drive

### 3. Integration Points

**Input**: Google Drive folder path with manuscript images
**Process**: 
- Use enhanced OCR tool with nano chunked method
- Leverage existing Google Drive tool for file operations
- Apply quality validation and improvement
**Output**: Complete transcribed manuscript uploaded to Drive

## Implementation Plan

1. **Update OCR Tool** - Add nano chunked method to existing tool
2. **Create Book Ingestion Crew** - New crew following existing patterns
3. **Test Integration** - Validate with Castor's manuscripts
4. **Deploy** - Make available via crew API endpoint

## Benefits
- Reuses existing tool infrastructure
- Follows established crew patterns
- Maintains backward compatibility
- Provides structured workflow for book ingestion