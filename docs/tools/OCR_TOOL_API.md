# OCR Tool API Reference

## Classes

### OCRTool

Main OCR tool class that integrates with CrewAI.

```python
class OCRTool(BaseTool):
    """
    Production OCR tool for extracting text from manuscript images.
    
    Handles:
    - Single and batch image processing
    - Validation and error handling
    - Rate limiting and retries
    - Result caching for efficiency
    """
```

#### Constructor

```python
OCRTool(
    max_file_size_mb: float = 10.0,
    min_confidence_threshold: float = 0.3,
    enable_caching: bool = True,
    api_timeout_seconds: int = 30,
    max_retries: int = 3
)
```

**Parameters:**
- `max_file_size_mb` (float): Maximum allowed file size in megabytes
- `min_confidence_threshold` (float): Minimum confidence score (0-1) to flag low confidence
- `enable_caching` (bool): Enable in-memory result caching
- `api_timeout_seconds` (int): Timeout for API requests
- `max_retries` (int): Number of retry attempts for failed requests

#### Methods

##### `_run(image_path: str) -> str`

Process a single image and return OCR results as JSON.

**Parameters:**
- `image_path` (str): Path to the image file

**Returns:**
- JSON string containing OCRToolResult

**Example:**
```python
result_json = tool._run("/path/to/manuscript.png")
result = OCRToolResult.parse_raw(result_json)
```

##### `process_batch(image_paths: List[str]) -> List[OCRToolResult]`

Process multiple images efficiently.

**Parameters:**
- `image_paths` (List[str]): List of image file paths

**Returns:**
- List of OCRToolResult objects

**Example:**
```python
results = tool.process_batch(["page1.png", "page2.png", "page3.png"])
for result in results:
    if result.success:
        print(f"Extracted {result.word_count} words")
```

##### `clear_cache() -> None`

Clear the in-memory result cache.

**Example:**
```python
tool.clear_cache()
```

##### `get_cache_stats() -> Dict[str, Any]`

Get cache statistics.

**Returns:**
- Dictionary with cache metrics:
  - `entries` (int): Number of cached results
  - `size_estimate_mb` (float): Estimated cache size in MB

**Example:**
```python
stats = tool.get_cache_stats()
print(f"Cache has {stats['entries']} entries")
```

##### `_validate_image(image_path: str) -> ValidationResult`

Validate an image before processing.

**Parameters:**
- `image_path` (str): Path to validate

**Returns:**
- ValidationResult object with validation status

**Example:**
```python
validation = tool._validate_image("manuscript.png")
if validation.is_valid:
    print(f"File size: {validation.file_size_mb:.2f}MB")
```

### OCRToolResult

Structured result from OCR processing.

```python
class OCRToolResult(BaseModel):
    """Structured result from OCR processing"""
    success: bool
    image_path: str
    text: Optional[str]
    confidence: Optional[float]
    word_count: Optional[int]
    processing_time_ms: Optional[int]
    error_type: Optional[OCRErrorType]
    error_message: Optional[str]
    metadata: Dict[str, Any]
```

**Fields:**
- `success` (bool): Whether OCR was successful
- `image_path` (str): Path to processed image
- `text` (Optional[str]): Extracted text content
- `confidence` (Optional[float]): Average confidence score (0-1)
- `word_count` (Optional[int]): Number of words extracted
- `processing_time_ms` (Optional[int]): Processing time in milliseconds
- `error_type` (Optional[OCRErrorType]): Type of error if failed
- `error_message` (Optional[str]): Error message if failed
- `metadata` (Dict[str, Any]): Additional metadata

### OCRClient

Low-level client for NVIDIA NIM PaddleOCR API.

```python
class OCRClient:
    """Client for NVIDIA NIM PaddleOCR API"""
```

#### Constructor

```python
OCRClient(api_key: Optional[str] = None)
```

**Parameters:**
- `api_key` (Optional[str]): NVIDIA NIM API key. Uses NVIDIA_NIM_API_KEY env var if not provided.

#### Methods

##### `ocr(image_source: Union[str, Path, bytes]) -> OCRResponse`

Perform OCR on an image synchronously.

**Parameters:**
- `image_source`: Path to image file, Path object, or raw bytes

**Returns:**
- OCRResponse object with results

**Example:**
```python
client = OCRClient()
response = client.ocr("manuscript.png")
print(f"Found text: {response.full_text}")
```

##### `ocr_async(image_source: Union[str, Path, bytes]) -> OCRResponse`

Perform OCR on an image asynchronously.

**Parameters:**
- `image_source`: Path to image file, Path object, or raw bytes

**Returns:**
- OCRResponse object with results

**Example:**
```python
async def process():
    client = OCRClient()
    response = await client.ocr_async("manuscript.png")
    return response.full_text
```

### OCRResponse

Response from OCR processing.

```python
class OCRResponse(BaseModel):
    """Complete OCR response from PaddleOCR"""
    results: List[OCRTextResult]
    full_text: str
    raw_response: Optional[Dict[str, Any]]
```

**Fields:**
- `results` (List[OCRTextResult]): All detected text segments
- `full_text` (str): All text concatenated
- `raw_response` (Optional[Dict]): Raw API response

### OCRTextResult

Individual text detection result.

```python
class OCRTextResult(BaseModel):
    """Individual text detection result"""
    text: str
    confidence: float
    bounding_box: Optional[OCRBoundingBox]
```

**Fields:**
- `text` (str): Detected text content
- `confidence` (float): Confidence score (0-1)
- `bounding_box` (Optional[OCRBoundingBox]): Text location in image

## Enums

### ImageFormat

Supported image formats.

```python
class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
```

### OCRErrorType

Types of OCR errors.

```python
class OCRErrorType(str, Enum):
    FILE_NOT_FOUND = "file_not_found"
    INVALID_FORMAT = "invalid_format"
    FILE_TOO_LARGE = "file_too_large"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    PROCESSING_ERROR = "processing_error"
    VALIDATION_ERROR = "validation_error"
```

## Exceptions

### OCRError

Base exception for OCR operations.

```python
class OCRError(Exception):
    """Base OCR error with context"""
    def __init__(
        self,
        error_type: OCRErrorType,
        message: str,
        details: Optional[Dict[str, Any]] = None
    )
```

**Attributes:**
- `error_type` (OCRErrorType): Type of error
- `message` (str): Error message
- `details` (Dict[str, Any]): Additional error context

## Convenience Functions

### `ocr_image()`

Quick OCR function for one-off use.

```python
def ocr_image(
    image_source: Union[str, Path, bytes],
    api_key: Optional[str] = None
) -> OCRResponse
```

**Example:**
```python
from src.utils.ocr_client import ocr_image

response = ocr_image("manuscript.png")
print(response.full_text)
```

### `ocr_image_async()`

Async version of quick OCR function.

```python
async def ocr_image_async(
    image_source: Union[str, Path, bytes],
    api_key: Optional[str] = None
) -> OCRResponse
```

**Example:**
```python
from src.utils.ocr_client import ocr_image_async

async def main():
    response = await ocr_image_async("manuscript.png")
    print(response.full_text)
```

## Complete Example

```python
from src.tools.ocr_tool import OCRTool, OCRToolResult, OCRErrorType

# Initialize tool with custom settings
tool = OCRTool(
    max_file_size_mb=20.0,
    min_confidence_threshold=0.5,
    enable_caching=True
)

# Process single image
try:
    result_json = tool._run("historical_manuscript.png")
    result = OCRToolResult.parse_raw(result_json)
    
    if result.success:
        print(f"Text: {result.text}")
        print(f"Confidence: {result.confidence:.2%}")
        print(f"Words: {result.word_count}")
        print(f"Time: {result.processing_time_ms}ms")
        
        # Check for low confidence
        if result.metadata.get("low_confidence"):
            print("Warning: Low confidence detection")
    else:
        # Handle specific error types
        match result.error_type:
            case OCRErrorType.FILE_NOT_FOUND:
                print("File not found")
            case OCRErrorType.FILE_TOO_LARGE:
                print("File too large")
            case _:
                print(f"Error: {result.error_message}")
                
except Exception as e:
    print(f"Unexpected error: {e}")

# Process batch
page_files = [f"page_{i:03d}.png" for i in range(1, 11)]
results = tool.process_batch(page_files)

# Compile successful results
successful = [r for r in results if r.success]
full_text = "\n\n".join(r.text for r in successful if r.text)

print(f"Processed {len(successful)}/{len(results)} pages successfully")

# Check cache performance
stats = tool.get_cache_stats()
print(f"Cache stats: {stats}")
```