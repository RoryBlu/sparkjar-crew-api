# OCR Tool Documentation

## Overview

The OCR Tool is a production-grade optical character recognition system built for manuscript and document processing. It uses NVIDIA NIM PaddleOCR API to extract text from images with enterprise-level reliability, caching, and error handling.

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Usage Guide](./OCR_TOOL_USAGE.md)
5. [API Reference](./OCR_TOOL_API.md)
6. [Testing](./OCR_TOOL_TESTING.md)
7. [Performance & Optimization](#performance--optimization)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)

## Features

### Core Capabilities
- **Text Extraction**: Accurate OCR from PNG and JPEG images
- **Confidence Scoring**: Per-word and overall confidence metrics
- **Batch Processing**: Efficient multi-image processing
- **Result Caching**: MD5-based caching to avoid redundant API calls
- **Error Handling**: Typed errors with detailed context
- **Retry Logic**: Exponential backoff for transient failures
- **Rate Limiting**: Automatic handling of API rate limits

### Production Features
- **Validation**: File size, format, and existence checks before processing
- **Lazy Initialization**: Client only created when needed
- **Connection Pooling**: Efficient HTTP client management
- **Structured Results**: Strongly typed response objects
- **Metadata Tracking**: Processing time, file size, segment count
- **CrewAI Integration**: Works seamlessly as a CrewAI tool

## Architecture

### Component Overview

```
OCRTool (CrewAI Tool)
    ├── Validation Layer
    │   ├── File existence check
    │   ├── Format validation (PNG/JPEG)
    │   └── Size limit enforcement
    │
    ├── Caching Layer
    │   ├── MD5 hash generation
    │   ├── In-memory result cache
    │   └── Cache statistics
    │
    ├── Processing Layer
    │   ├── OCRClient wrapper
    │   ├── Retry mechanism
    │   └── Rate limit handling
    │
    └── Result Layer
        ├── Structured response (OCRToolResult)
        ├── Confidence calculation
        └── Metadata enrichment

OCRClient (NVIDIA NIM API Client)
    ├── Image Encoding
    │   ├── Base64 conversion
    │   └── MIME type detection
    │
    ├── API Communication
    │   ├── HTTP client with timeout
    │   ├── Header management
    │   └── Error propagation
    │
    └── Response Parsing
        ├── Text extraction
        ├── Confidence scores
        └── Bounding box data
```

### Data Flow

1. **Input Validation**
   - Check file exists and is accessible
   - Verify format is PNG or JPEG
   - Ensure file size is within limits

2. **Cache Check**
   - Generate MD5 hash of image
   - Look for cached result
   - Return cached result if found

3. **API Processing**
   - Encode image to base64
   - Send to NVIDIA NIM PaddleOCR
   - Handle retries and rate limits

4. **Result Processing**
   - Parse API response
   - Calculate aggregate metrics
   - Build structured result
   - Cache for future use

## Installation & Setup

### Prerequisites

1. **Python Requirements**
   ```bash
   pip install crewai-tools pydantic httpx pillow
   ```

2. **Environment Variables**
   ```bash
   # Required: NVIDIA NIM API Key
   export NVIDIA_NIM_API_KEY="your-api-key-here"
   
   # Optional: Logging configuration
   export LOG_LEVEL="INFO"
   ```

3. **File Structure**
   ```
   services/crew-api/
   ├── src/
   │   ├── tools/
   │   │   └── ocr_tool.py
   │   └── utils/
   │       └── ocr_client.py
   └── tests/
       └── tools/
           ├── test_ocr_tool.py
           └── test_ocr_integration.py
   ```

### Configuration Options

The OCR tool can be configured with the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_file_size_mb` | float | 10.0 | Maximum file size in megabytes |
| `min_confidence_threshold` | float | 0.3 | Minimum confidence to flag as low |
| `enable_caching` | bool | True | Enable result caching |
| `api_timeout_seconds` | int | 30 | API request timeout |
| `max_retries` | int | 3 | Maximum retry attempts |

## Performance & Optimization

### Caching Strategy

The tool uses an in-memory cache keyed by MD5 hash of the image content:

```python
# Cache hit ratio monitoring
stats = tool.get_cache_stats()
print(f"Cache entries: {stats['entries']}")
print(f"Cache size: {stats['size_estimate_mb']:.2f}MB")
```

### Batch Processing

For multiple images, use the batch processing method:

```python
# Process 100 pages efficiently
results = tool.process_batch(page_files)
```

### Performance Metrics

Typical processing times:
- Small image (< 1MB): 500-1000ms
- Medium image (1-5MB): 1000-3000ms
- Large image (5-10MB): 3000-5000ms

## Security Considerations

### API Key Management
- Store API key in environment variables, not in code
- Use secrets management in production
- Rotate keys regularly

### File Access
- Tool validates file paths to prevent directory traversal
- Only processes files with explicit paths
- No network file access

### Data Privacy
- Results are cached in memory only
- No persistent storage of extracted text
- Cache can be cleared manually

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: NVIDIA_NIM_API_KEY not configured
   Solution: Set the environment variable
   ```

2. **File Too Large**
   ```
   Error: File too large: 15.2MB (max: 10.0MB)
   Solution: Resize image or increase max_file_size_mb
   ```

3. **Rate Limiting**
   ```
   Error: Rate limited, waiting 2000ms
   Solution: Tool handles this automatically with retry
   ```

4. **Low Confidence Results**
   - Check image quality
   - Ensure good contrast
   - Try preprocessing (sharpening, contrast adjustment)

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now tool will log detailed information
tool = OCRTool()
```

### Health Check

Test the OCR setup:

```python
# Quick test
from src.utils.ocr_client import OCRClient

client = OCRClient()
# If this doesn't raise an error, API key is valid
```

## Next Steps

- See [Usage Guide](./OCR_TOOL_USAGE.md) for practical examples
- Check [API Reference](./OCR_TOOL_API.md) for detailed method documentation
- Review [Testing Guide](./OCR_TOOL_TESTING.md) for test coverage details