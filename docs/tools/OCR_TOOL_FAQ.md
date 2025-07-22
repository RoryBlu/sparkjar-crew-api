# OCR Tool FAQ & Troubleshooting

## Frequently Asked Questions

### General Questions

**Q: What image formats are supported?**
A: PNG and JPEG/JPG only. Convert other formats before processing.

**Q: What's the maximum file size?**
A: Default is 10MB. Can be increased via `max_file_size_mb` parameter up to API limits.

**Q: Does it work with handwritten text?**
A: Yes, though confidence may be lower. Adjust `min_confidence_threshold` for handwriting.

**Q: Is the text extraction real-time?**
A: Processing typically takes 1-3 seconds per image, depending on size and complexity.

**Q: Can it handle multiple languages?**
A: Yes, NVIDIA NIM PaddleOCR supports multiple languages. Best results with Latin scripts.

### Technical Questions

**Q: How does caching work?**
A: Results are cached by MD5 hash of image content. Cache is in-memory only, cleared on restart.

**Q: What happens during rate limiting?**
A: The tool automatically retries with exponential backoff. You don't need to handle it.

**Q: Can I process PDFs?**
A: Not directly. Convert PDF pages to PNG/JPEG first using a PDF library.

**Q: Is batch processing faster than individual calls?**
A: Currently batch processing is sequential. Main benefit is simpler code and automatic error handling.

**Q: Can I use async processing?**
A: The underlying client supports async, but the CrewAI tool interface is synchronous.

### Integration Questions

**Q: How do I use this with CrewAI?**
A: Add `OCRTool()` to your agent's tools list. The agent can then call it directly.

**Q: Can multiple agents share the same tool instance?**
A: Yes, the tool is thread-safe and can be shared. Cache will be shared too.

**Q: How do I handle low confidence results?**
A: Check `result.metadata['low_confidence']` flag and implement manual review workflow.

**Q: Can I customize the OCR engine settings?**
A: Current implementation uses NVIDIA NIM defaults. Contact support for custom requirements.

## Troubleshooting Guide

### Common Errors and Solutions

#### 1. API Key Not Found

**Error:**
```
OCRError: NVIDIA_NIM_API_KEY not configured
```

**Solution:**
```bash
# Set in environment
export NVIDIA_NIM_API_KEY="your-key"

# Or in .env file
echo 'NVIDIA_NIM_API_KEY="your-key"' >> .env

# Verify it's set
echo $NVIDIA_NIM_API_KEY
```

#### 2. File Not Found

**Error:**
```
ValidationResult(is_valid=False, error_type=FILE_NOT_FOUND)
```

**Solution:**
```python
# Use absolute paths
import os
image_path = os.path.abspath("manuscript.png")

# Verify file exists
if not os.path.exists(image_path):
    print(f"File not found: {image_path}")
```

#### 3. Invalid Image Format

**Error:**
```
Unsupported format: bmp. Use PNG or JPEG.
```

**Solution:**
```bash
# Convert to supported format
convert manuscript.bmp manuscript.png

# Or with Python
from PIL import Image
img = Image.open("manuscript.bmp")
img.save("manuscript.png")
```

#### 4. File Too Large

**Error:**
```
File too large: 15.2MB (max: 10.0MB)
```

**Solution:**
```python
# Option 1: Increase limit
tool = OCRTool(max_file_size_mb=20.0)

# Option 2: Resize image
from PIL import Image
img = Image.open("large.png")
img.thumbnail((2000, 2000))  # Max 2000px
img.save("smaller.png")

# Option 3: Reduce quality
img.save("smaller.jpg", quality=85)
```

#### 5. Low Confidence Results

**Symptoms:**
- `result.confidence < 0.5`
- `result.metadata['low_confidence'] == True`
- Garbled or incorrect text

**Solutions:**

1. **Improve Image Quality**
```python
from PIL import Image, ImageEnhance

img = Image.open("blurry.png")

# Increase sharpness
enhancer = ImageEnhance.Sharpness(img)
sharp_img = enhancer.enhance(2.0)

# Increase contrast
enhancer = ImageEnhance.Contrast(sharp_img)
final_img = enhancer.enhance(1.5)

final_img.save("enhanced.png")
```

2. **Adjust Threshold**
```python
# Lower threshold for difficult images
tool = OCRTool(min_confidence_threshold=0.2)
```

3. **Preprocess Image**
```python
import cv2
import numpy as np

# Read image
img = cv2.imread('manuscript.png')

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Apply threshold
_, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

# Save preprocessed
cv2.imwrite('preprocessed.png', thresh)
```

#### 6. API Timeout

**Error:**
```
httpx.ReadTimeout: The read operation timed out
```

**Solution:**
```python
# Increase timeout
tool = OCRTool(api_timeout_seconds=60)

# For very large images, consider resizing first
```

#### 7. Rate Limiting

**Error:**
```
HTTPStatusError: 429 Too Many Requests
```

**Solution:**
```python
# Tool handles this automatically with retry
# To adjust retry behavior:
tool = OCRTool(max_retries=5)

# Add delay between batch items
import time
for image in images:
    result = tool._run(image)
    time.sleep(0.5)  # 500ms delay
```

### Performance Issues

#### Slow Processing

**Diagnosis:**
```python
result = OCRToolResult.parse_raw(result_json)
print(f"Processing took: {result.processing_time_ms}ms")
```

**Solutions:**

1. **Enable Caching**
```python
tool = OCRTool(enable_caching=True)
# Second call to same image will be instant
```

2. **Resize Large Images**
```python
# Check image size first
from PIL import Image
img = Image.open("huge.png")
if img.size[0] > 3000 or img.size[1] > 3000:
    img.thumbnail((3000, 3000))
    img.save("resized.png")
```

3. **Process in Parallel** (for multiple images)
```python
from concurrent.futures import ThreadPoolExecutor

def process_image(path):
    return tool._run(path)

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(process_image, image_paths))
```

#### High Memory Usage

**Issue:** Processing many images fills memory with cache.

**Solution:**
```python
# Monitor cache size
stats = tool.get_cache_stats()
if stats['size_estimate_mb'] > 100:
    tool.clear_cache()

# Or disable caching
tool = OCRTool(enable_caching=False)
```

### Debugging Techniques

#### 1. Enable Detailed Logging

```python
import logging

# Set to DEBUG for maximum detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now run OCR
tool = OCRTool()
result = tool._run("problem_image.png")
```

#### 2. Inspect Raw API Response

```python
from src.utils.ocr_client import OCRClient

client = OCRClient()
response = client.ocr("test.png")

# Look at raw response
import json
print(json.dumps(response.raw_response, indent=2))

# Check individual segments
for i, segment in enumerate(response.results):
    print(f"Segment {i}: '{segment.text}' (conf: {segment.confidence:.2%})")
```

#### 3. Test Image Validation

```python
# Validate without processing
tool = OCRTool()
validation = tool._validate_image("test.png")

print(f"Valid: {validation.is_valid}")
print(f"Format: {validation.image_format}")
print(f"Size: {validation.file_size_mb:.2f}MB")
if not validation.is_valid:
    print(f"Error: {validation.error_message}")
```

#### 4. Compare Results

```python
# Test with different settings
configs = [
    {"min_confidence_threshold": 0.3},
    {"min_confidence_threshold": 0.5},
    {"max_file_size_mb": 20.0},
]

for config in configs:
    tool = OCRTool(**config)
    result_json = tool._run("test.png")
    result = OCRToolResult.parse_raw(result_json)
    print(f"Config {config}: Confidence={result.confidence:.2%}")
```

### Getting Help

If you're still having issues:

1. **Check logs** for detailed error messages
2. **Verify API key** is valid and has quota
3. **Test with a known good image** (simple text on white background)
4. **Check the [examples](./OCR_TOOL_USAGE.md)** for working code
5. **Review [API documentation](./OCR_TOOL_API.md)** for correct usage

For additional support:
- GitHub Issues: Report bugs or request features
- API Support: Contact NVIDIA for API-specific issues
- Community: Share solutions and get help from other users