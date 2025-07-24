# SparkJAR Crew Tools Documentation

## Available Tools

### OCR Tool
A production-grade optical character recognition tool for extracting text from manuscript images using NVIDIA NIM PaddleOCR.

#### Documentation
- **[Overview & Setup](./OCR_TOOL_README.md)** - Complete introduction, features, and architecture
- **[Usage Guide](./OCR_TOOL_USAGE.md)** - Practical examples and best practices  
- **[API Reference](./OCR_TOOL_API.md)** - Detailed API documentation for all classes and methods
- **[Testing Guide](./OCR_TOOL_TESTING.md)** - Comprehensive testing strategies and examples
- **[Migration Guide](./OCR_TOOL_MIGRATION.md)** - Migrate from Tesseract, Google Vision, or AWS Textract
- **[FAQ & Troubleshooting](./OCR_TOOL_FAQ.md)** - Common questions and debugging techniques

#### Key Features
- Text extraction from PNG/JPEG images
- Confidence scoring and validation
- Result caching for performance
- Batch processing support
- CrewAI native integration
- Production-grade error handling

#### Quick Start
```python
from src.tools.ocr_tool import OCRTool

# Initialize and use
tool = OCRTool()
result = tool._run("manuscript.png")
```

---

## Tool Development Guidelines

When creating new tools for SparkJAR Crew, follow these patterns established by the OCR tool:

### 1. Structure
- Inherit from `crewai_tools.BaseTool`
- Implement `_run()` method for CrewAI
- Use Pydantic models for structured results
- Include proper error handling with typed errors

### 2. Production Features
- Validation before processing
- Caching where appropriate
- Retry logic for external APIs
- Comprehensive error messages
- Performance metrics in results

### 3. Testing
- Real integration tests (no mocking)
- Unit tests for all methods
- Performance benchmarks
- CrewAI integration tests

### 4. Documentation
- README with architecture overview
- Usage guide with real examples
- Complete API reference
- Testing documentation
- Migration guides if replacing existing tools

## Contributing

To add a new tool:

1. Create tool implementation in `src/tools/`
2. Add comprehensive tests in `tests/tools/`
3. Write documentation in `docs/tools/`
4. Update this index with your tool

Follow the OCR tool as a reference implementation for production-grade CrewAI tools.