# OCR Tool Usage Guide

## Overview

The OCR Tool extracts text from images using NVIDIA NIM PaddleOCR. Built for production use with manuscript processing, it handles validation, caching, retries, and batch processing.

## Quick Start

```python
from src.tools.ocr_tool import OCRTool

# Initialize tool
tool = OCRTool()

# Process single image
result_json = tool._run("/path/to/manuscript.png")
```

## Configuration

```python
tool = OCRTool(
    max_file_size_mb=10.0,        # Max file size (default: 10MB)
    min_confidence_threshold=0.3,  # Min confidence score (default: 0.3)
    enable_caching=True,          # Cache results (default: True)
    api_timeout_seconds=30,       # API timeout (default: 30s)
    max_retries=3                 # Retry attempts (default: 3)
)
```

## Real-World Examples

### Processing Historical Manuscripts

```python
# For old/degraded manuscripts, use lower confidence threshold
manuscript_tool = OCRTool(min_confidence_threshold=0.2)

# Process a page
result_json = manuscript_tool._run("historical_page_1.png")
result = OCRToolResult.parse_raw(result_json)

if result.success:
    print(f"Extracted {result.word_count} words")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Text: {result.text}")
else:
    print(f"Failed: {result.error_message}")
```

### Batch Processing Book Pages

```python
# Process entire book
page_files = [f"page_{i:03d}.png" for i in range(1, 301)]
results = tool.process_batch(page_files)

# Compile results
successful_pages = [r for r in results if r.success]
failed_pages = [r for r in results if not r.success]

print(f"Processed {len(successful_pages)} pages successfully")
print(f"Failed on {len(failed_pages)} pages")

# Combine text
full_text = "\n\n---PAGE BREAK---\n\n".join(
    r.text for r in results if r.success and r.text
)
```

### CrewAI Integration

```python
from crewai import Agent, Task, Crew
from src.tools.ocr_tool import OCRTool

# Create agent with OCR tool
ocr_agent = Agent(
    role="Manuscript Processor",
    goal="Extract and compile text from manuscript images",
    tools=[OCRTool()],
    backstory="Expert in processing historical documents"
)

# Create task
process_task = Task(
    description="Extract text from manuscript pages: {manuscript_files}",
    agent=ocr_agent
)

# Run crew
crew = Crew(agents=[ocr_agent], tasks=[process_task])
result = crew.kickoff({"manuscript_files": ["page1.png", "page2.png"]})
```

## Error Handling

The tool provides specific error types for different failures:

```python
result = OCRToolResult.parse_raw(result_json)

if not result.success:
    match result.error_type:
        case OCRErrorType.FILE_NOT_FOUND:
            print("Check file path")
        case OCRErrorType.INVALID_FORMAT:
            print("Use PNG or JPEG only")
        case OCRErrorType.FILE_TOO_LARGE:
            print(f"Reduce file size below {tool.max_file_size_mb}MB")
        case OCRErrorType.API_ERROR:
            print("API issue - check logs")
        case OCRErrorType.RATE_LIMIT:
            print("Slow down - rate limited")
```

## Performance Optimization

### Caching

```python
# Enable caching for repeated processing
tool = OCRTool(enable_caching=True)

# Process same image multiple times - only first call hits API
for i in range(5):
    result = tool._run("same_image.png")

# Check cache statistics
stats = tool.get_cache_stats()
print(f"Cache has {stats['entries']} entries")
print(f"Estimated size: {stats['size_estimate_mb']:.2f}MB")

# Clear cache if needed
tool.clear_cache()
```

### Batch Processing

```python
# Process multiple images efficiently
images = ["page1.png", "page2.png", "page3.png"]
results = tool.process_batch(images)

# Results maintain order
for image, result in zip(images, results):
    print(f"{image}: {'Success' if result.success else 'Failed'}")
```

## Validation

Always validate before processing:

```python
# Manual validation
validation = tool._validate_image("manuscript.png")

if validation.is_valid:
    print(f"Image format: {validation.image_format}")
    print(f"File size: {validation.file_size_mb:.2f}MB")
    # Safe to process
else:
    print(f"Validation failed: {validation.error_message}")
    print(f"Error type: {validation.error_type}")
```

## Production Best Practices

1. **Set appropriate timeouts** for large manuscripts:
   ```python
   tool = OCRTool(api_timeout_seconds=60)
   ```

2. **Handle low confidence** results:
   ```python
   if result.success and result.confidence < 0.5:
       # Manual review needed
       flag_for_human_review(result.image_path)
   ```

3. **Monitor processing times**:
   ```python
   if result.processing_time_ms > 5000:
       logger.warning(f"Slow OCR: {result.image_path}")
   ```

4. **Use metadata** for tracking:
   ```python
   print(f"Segments found: {result.metadata['segments']}")
   print(f"Low confidence: {result.metadata['low_confidence']}")
   ```

## Testing

Run tests with pytest:

```bash
# Unit tests
pytest tests/tools/test_ocr_tool.py -v

# Integration tests (requires API key)
NVIDIA_NIM_API_KEY=your_key pytest tests/tools/test_ocr_integration.py -v -m integration
```

## Troubleshooting

### API Key Issues
```bash
# Check if key is set
echo $NVIDIA_NIM_API_KEY

# Set in .env file
echo 'NVIDIA_NIM_API_KEY="your_key_here"' >> .env
```

### Image Format Issues
- Only PNG and JPEG supported
- Convert other formats first:
  ```bash
  convert manuscript.tiff manuscript.png
  ```

### Large Files
- Resize images over 10MB:
  ```bash
  convert large.png -resize 50% smaller.png
  ```

### Low Confidence
- Improve image quality
- Adjust threshold: `OCRTool(min_confidence_threshold=0.2)`
- Pre-process images (contrast, sharpness)