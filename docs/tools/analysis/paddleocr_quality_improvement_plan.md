# PaddleOCR Quality Improvement Plan

## Current State Analysis

Based on our analysis of NVIDIA PaddleOCR's performance on Castor Gonzalez's handwritten Spanish manuscripts:

### Performance Metrics
- **Page 1**: Captured 38 words (approx. 23% accuracy)
- **Page 2**: Captured 55 words (poor accuracy)
- **Page 3**: Captured 37 words (approx. 15% accuracy)
- **Total**: 130 words captured across 3 pages

### Key Issues Identified

1. **Word Boundary Detection**: PaddleOCR merged multiple words ("estabamonostror" instead of "estabamos nosotros")
2. **Character Recognition**: Many characters misidentified, especially cursive connections
3. **Context Loss**: Unable to maintain sentence structure and meaning
4. **Handwriting Style**: Struggles with cursive Spanish handwriting

### What PaddleOCR Got Right
- Some individual words were partially recognized
- Basic word shapes were detected
- Image preprocessing (resizing) worked correctly

### What PaddleOCR Got Wrong
- Word segmentation failures
- Character substitution errors
- Complete loss of diacritical marks (accents)
- Unable to handle cursive connections

## Improvement Strategies

### 1. Multi-Pass Processing with Different Parameters

```python
def multi_pass_ocr(image_path):
    """Perform multiple OCR passes with different parameters."""
    passes = []
    
    # Pass 1: Standard detection
    result1 = ocr_with_paddleocr(image_path, det_db_thresh=0.3)
    passes.append(result1)
    
    # Pass 2: Higher sensitivity
    result2 = ocr_with_paddleocr(image_path, det_db_thresh=0.1)
    passes.append(result2)
    
    # Pass 3: Different detection algorithm
    result3 = ocr_with_paddleocr(image_path, det_algorithm="EAST")
    passes.append(result3)
    
    return merge_results(passes)
```

### 2. Image Preprocessing Enhancements

```python
def enhance_image_for_ocr(image_path):
    """Apply multiple preprocessing techniques."""
    img = cv2.imread(image_path)
    
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Apply adaptive thresholding for cursive text
    thresh = cv2.adaptiveThreshold(gray, 255, 
                                  cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 11, 2)
    
    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(thresh)
    
    # 4. Deskew
    angle = determine_skew(denoised)
    rotated = rotate_image(denoised, angle)
    
    return rotated
```

### 3. Post-Processing with Language Models

Since NVIDIA PaddleOCR captured fragments, we can use a language model to reconstruct the text:

```python
def improve_ocr_with_llm(ocr_result, image_path):
    """Use LLM to improve OCR results."""
    prompt = f"""
    OCR captured these fragments from a handwritten Spanish manuscript:
    {ocr_result}
    
    Based on these fragments and common Spanish patterns, 
    reconstruct the likely original text.
    """
    
    # Send to gpt-4.1-mini for reconstruction
    improved_text = llm_reconstruct(prompt, image_path)
    return improved_text
```

### 4. Alternative Approaches

1. **Segment-then-OCR**: Break the image into smaller segments (words/lines) before OCR
2. **Ensemble Methods**: Combine results from multiple OCR engines
3. **Fine-tuning**: Train a custom model on similar handwriting samples

### 5. API Parameter Optimization

Based on NVIDIA's PaddleOCR API documentation, we should experiment with:

```python
# Detection parameters
det_db_thresh: [0.1, 0.3, 0.5]  # Detection confidence threshold
det_db_box_thresh: [0.5, 0.6, 0.7]  # Box confidence threshold

# Recognition parameters  
rec_batch_num: [1, 6, 10]  # Batch size for recognition
use_angle_cls: true  # Enable angle classification
```

## Implementation Priority

1. **Immediate**: Implement multi-pass processing with parameter variations
2. **Short-term**: Add comprehensive image preprocessing pipeline
3. **Medium-term**: Integrate LLM post-processing for text reconstruction
4. **Long-term**: Consider training custom model for Spanish cursive

## Expected Improvements

With these enhancements, we expect to:
- Increase word capture rate from ~23% to 60-70%
- Improve character accuracy significantly
- Better preserve sentence structure
- Handle cursive connections more effectively

## Next Steps

1. Implement multi-pass OCR function
2. Test different parameter combinations
3. Create preprocessing pipeline
4. Integrate with crew workflow
5. Set up quality metrics tracking