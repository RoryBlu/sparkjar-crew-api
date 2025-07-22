# OCR Tool Testing Guide

## Overview

The OCR tool includes comprehensive unit and integration tests that verify functionality with real API calls and actual image processing. No mocking - tests use the real code paths.

## Test Structure

```
tests/tools/
├── test_ocr_tool.py          # Unit tests for OCR tool
├── test_ocr_integration.py   # Integration tests for manuscript workflows
└── fixtures/                 # Test images and data
    ├── test_image.png
    ├── test_manuscript.jpg
    └── large_document.png
```

## Running Tests

### Prerequisites

1. **Set API Key**
   ```bash
   export NVIDIA_NIM_API_KEY="your-api-key"
   ```

2. **Install Test Dependencies**
   ```bash
   pip install pytest pytest-asyncio pillow
   ```

### Running All Tests

```bash
# Run all OCR tests
pytest tests/tools/test_ocr*.py -v

# Run with coverage
pytest tests/tools/test_ocr*.py -v --cov=src.tools.ocr_tool --cov=src.utils.ocr_client

# Run only unit tests
pytest tests/tools/test_ocr_tool.py -v

# Run only integration tests
pytest tests/tools/test_ocr_integration.py -v -m integration
```

### Test Categories

Tests are organized by marks:

```bash
# Quick tests (validation, caching)
pytest -m "not integration" tests/tools/test_ocr*.py

# Integration tests (require API key)
pytest -m integration tests/tools/test_ocr*.py

# Performance tests
pytest -m performance tests/tools/test_ocr*.py
```

## Unit Tests

### File: `test_ocr_tool.py`

#### Test Coverage

1. **Initialization Tests**
   ```python
   def test_tool_initialization():
       """Test tool creates with default parameters"""
       
   def test_tool_custom_config():
       """Test tool with custom configuration"""
   ```

2. **Validation Tests**
   ```python
   def test_validate_missing_file():
       """Test validation fails for non-existent file"""
       
   def test_validate_invalid_format():
       """Test validation rejects unsupported formats"""
       
   def test_validate_file_too_large():
       """Test validation enforces size limits"""
       
   def test_validate_valid_image():
       """Test validation passes for valid images"""
   ```

3. **Caching Tests**
   ```python
   def test_cache_hit():
       """Test cached results are returned"""
       
   def test_cache_stats():
       """Test cache statistics tracking"""
       
   def test_clear_cache():
       """Test cache clearing functionality"""
   ```

4. **Error Handling Tests**
   ```python
   def test_missing_api_key():
       """Test graceful handling of missing API key"""
       
   def test_api_error_handling():
       """Test handling of API errors"""
       
   def test_retry_logic():
       """Test exponential backoff retry"""
   ```

5. **Result Processing Tests**
   ```python
   def test_successful_ocr():
       """Test successful OCR processing"""
       
   def test_low_confidence_detection():
       """Test low confidence flagging"""
       
   def test_metadata_enrichment():
       """Test metadata is properly added"""
   ```

### Example Test Implementation

```python
def test_real_ocr_processing():
    """Test actual OCR processing with real image"""
    # Create test image with PIL
    image = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Test Text", fill='black')
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        image.save(f, 'PNG')
        temp_path = f.name
    
    try:
        # Process with OCR tool
        tool = OCRTool()
        result_json = tool._run(temp_path)
        result = OCRToolResult.parse_raw(result_json)
        
        # Verify results
        assert result.success
        assert result.text is not None
        assert result.confidence > 0
        assert result.word_count > 0
        assert result.processing_time_ms > 0
        
    finally:
        # Cleanup
        os.unlink(temp_path)
```

## Integration Tests

### File: `test_ocr_integration.py`

#### Manuscript Processing Tests

```python
@pytest.mark.integration
class TestManuscriptProcessing:
    """Test real manuscript processing workflows"""
    
    def test_historical_manuscript():
        """Test processing degraded historical document"""
        tool = OCRTool(min_confidence_threshold=0.2)
        result = tool._run("fixtures/historical_manuscript.png")
        assert result.success
        
    def test_multi_page_book():
        """Test batch processing of book pages"""
        pages = ["page_001.png", "page_002.png", "page_003.png"]
        tool = OCRTool()
        results = tool.process_batch(pages)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        
    def test_mixed_quality_batch():
        """Test batch with varying image quality"""
        images = [
            "high_quality.png",
            "medium_quality.jpg",
            "low_quality.png"
        ]
        
        tool = OCRTool()
        results = tool.process_batch(images)
        
        # Verify confidence varies by quality
        confidences = [r.confidence for r in results if r.success]
        assert max(confidences) - min(confidences) > 0.2
```

#### CrewAI Integration Tests

```python
@pytest.mark.integration
def test_crewai_integration():
    """Test OCR tool works with CrewAI agents"""
    from crewai import Agent, Task, Crew
    
    # Create agent with OCR tool
    agent = Agent(
        role="Manuscript Processor",
        tools=[OCRTool()],
        goal="Extract text from images"
    )
    
    # Create task
    task = Task(
        description="Extract text from test_manuscript.png",
        agent=agent
    )
    
    # Run crew
    crew = Crew(agents=[agent], tasks=[task])
    result = crew.kickoff()
    
    assert "text" in result.lower()
```

## Performance Tests

### Benchmarking

```python
@pytest.mark.performance
def test_processing_speed():
    """Benchmark OCR processing speed"""
    import time
    
    tool = OCRTool()
    
    # Small image
    start = time.time()
    tool._run("small_image.png")
    small_time = time.time() - start
    
    # Large image
    start = time.time()
    tool._run("large_image.png")
    large_time = time.time() - start
    
    # Assert reasonable times
    assert small_time < 2.0  # Under 2 seconds
    assert large_time < 5.0  # Under 5 seconds
    
    print(f"Small image: {small_time:.2f}s")
    print(f"Large image: {large_time:.2f}s")
```

### Cache Performance

```python
@pytest.mark.performance
def test_cache_performance():
    """Test cache improves performance"""
    tool = OCRTool(enable_caching=True)
    
    # First call - hits API
    start = time.time()
    tool._run("test_image.png")
    first_call = time.time() - start
    
    # Second call - from cache
    start = time.time()
    tool._run("test_image.png")
    cached_call = time.time() - start
    
    # Cache should be 100x faster
    assert cached_call < first_call / 100
    
    print(f"API call: {first_call:.3f}s")
    print(f"Cached: {cached_call:.3f}s")
    print(f"Speedup: {first_call/cached_call:.1f}x")
```

## Test Fixtures

### Creating Test Images

```python
def create_test_manuscript(text: str, quality: str = "high") -> str:
    """Create test manuscript image"""
    if quality == "high":
        size = (800, 1000)
        font_size = 16
        noise = 0
    elif quality == "medium":
        size = (600, 800)
        font_size = 14
        noise = 10
    else:  # low
        size = (400, 600)
        font_size = 12
        noise = 20
    
    # Create image
    image = Image.new('RGB', size, color='beige')
    draw = ImageDraw.Draw(image)
    
    # Add text
    y = 50
    for line in text.split('\n'):
        draw.text((50, y), line, fill='black')
        y += font_size + 10
    
    # Add noise for low quality
    if noise > 0:
        pixels = image.load()
        for i in range(noise * 100):
            x = random.randint(0, size[0]-1)
            y = random.randint(0, size[1]-1)
            pixels[x, y] = (
                random.randint(200, 255),
                random.randint(200, 255),
                random.randint(200, 255)
            )
    
    # Save
    path = f"test_manuscript_{quality}.png"
    image.save(path)
    return path
```

### Test Data

```python
# Historical manuscript text
HISTORICAL_TEXT = """
The Historie of the World
In Five Bookes
By Sir Walter Raleigh, Knight

Containing the Beginning and first state of all Nations;
their Antiquities, Governments, Laws, Religions, and Customes;
"""

# Modern document text
MODERN_TEXT = """
MEMORANDUM

TO: All Staff
FROM: Management
DATE: January 15, 2024
RE: New OCR System Implementation

We are pleased to announce the deployment of our new OCR system
for manuscript processing. This system will significantly improve
our ability to digitize historical documents.
"""
```

## Debugging Tests

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now tests will show detailed logs
def test_with_logging():
    tool = OCRTool()
    result = tool._run("test.png")
```

### Capture API Responses

```python
def test_debug_api_response():
    """Debug test to inspect raw API response"""
    from src.utils.ocr_client import OCRClient
    
    client = OCRClient()
    response = client.ocr("test_image.png")
    
    # Inspect raw response
    print("Raw API Response:")
    print(json.dumps(response.raw_response, indent=2))
    
    # Inspect parsed results
    for i, result in enumerate(response.results):
        print(f"\nSegment {i}:")
        print(f"  Text: {result.text}")
        print(f"  Confidence: {result.confidence:.2%}")
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
name: OCR Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      env:
        NVIDIA_NIM_API_KEY: ${{ secrets.NVIDIA_NIM_API_KEY }}
      run: |
        pytest tests/tools/test_ocr*.py -v --cov
```

## Test Best Practices

1. **Always Use Real Images**: Create test images with PIL, don't mock
2. **Test Edge Cases**: Empty images, rotated text, handwriting
3. **Verify Metrics**: Check confidence, word count, processing time
4. **Clean Up**: Always remove temporary test files
5. **Test Failures**: Verify error types and messages are correct
6. **Performance Baseline**: Set reasonable time expectations
7. **Integration Reality**: Test with actual CrewAI workflows