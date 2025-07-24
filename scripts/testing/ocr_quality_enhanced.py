#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Enhanced OCR with quality improvements and multiple passes."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import os
import json
import base64
import requests
from PIL import Image, ImageEnhance, ImageFilter
import io
import numpy as np

def preprocess_image(image_path, enhancement_level=1):
    """Preprocess image for better OCR results."""
    img = Image.open(image_path)
    
    # Convert to RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    if enhancement_level > 0:
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)
        
        # Apply slight denoise
        if enhancement_level > 1:
            img = img.filter(ImageFilter.MedianFilter(size=3))
    
    return img

def resize_for_ocr(img, target_kb=200):
    """Resize image optimally for OCR."""
    # Start with high quality
    quality = 90
    scale = 1.0
    
    while True:
        # Apply scale if needed
        if scale < 1.0:
            new_size = (int(img.width * scale), int(img.height * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            resized = img
        
        # Save to buffer
        buffer = io.BytesIO()
        resized.save(buffer, format='JPEG', quality=quality)
        size_kb = len(buffer.getvalue()) / 1024
        
        if size_kb <= target_kb:
            return buffer.getvalue(), resized.size
        
        # Try reducing quality first
        if quality > 70:
            quality -= 10
        else:
            # Then reduce size
            scale *= 0.9
            
        if scale < 0.3:
            # Last resort
            buffer = io.BytesIO()
            resized.save(buffer, format='JPEG', quality=60)
            return buffer.getvalue(), resized.size

def ocr_with_params(image_bytes, language='es', params=None):
    """Run OCR with specific parameters."""
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    url = "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Build payload with parameters
    payload = {
        "input": [{
            "type": "image_url",
            "url": f"data:image/jpeg;base64,{base64_image}"
        }]
    }
    
    # Add optional parameters if provided
    if params:
        payload["parameters"] = params
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error {response.status_code}: {response.text[:200]}")
        return None

def extract_text_with_confidence(response_data):
    """Extract text and confidence from response."""
    results = []
    
    if 'data' in response_data:
        for item in response_data['data']:
            if 'text_detections' in item:
                for detection in item['text_detections']:
                    if 'text_prediction' in detection:
                        text = detection['text_prediction'].get('text', '')
                        confidence = detection['text_prediction'].get('confidence', 0)
                        bbox = detection.get('bounding_box', {})
                        
                        results.append({
                            'text': text,
                            'confidence': confidence,
                            'bbox': bbox
                        })
    
    return results

def merge_text_by_lines(detections, y_threshold=0.02):
    """Merge text detections into lines based on vertical position."""
    if not detections:
        return []
    
    # Sort by vertical position (top of bounding box)
    sorted_detections = sorted(detections, 
                              key=lambda x: x['bbox'].get('points', [{}])[0].get('y', 0))
    
    lines = []
    current_line = []
    current_y = None
    
    for det in sorted_detections:
        bbox_points = det['bbox'].get('points', [])
        if bbox_points:
            y = bbox_points[0].get('y', 0)
            
            if current_y is None or abs(y - current_y) < y_threshold:
                current_line.append(det)
                if current_y is None:
                    current_y = y
            else:
                # New line
                if current_line:
                    # Sort line by x position
                    current_line.sort(key=lambda x: x['bbox']['points'][0].get('x', 0))
                    lines.append(current_line)
                current_line = [det]
                current_y = y
    
    # Add last line
    if current_line:
        current_line.sort(key=lambda x: x['bbox']['points'][0].get('x', 0))
        lines.append(current_line)
    
    return lines

def process_image_multiple_passes(image_path, language='es'):
    """Process image with multiple passes and different strategies."""
    logger.info(f"\nProcessing: {Path(image_path).name}")
    logger.info("-" * 60)
    
    all_detections = []
    
    # Pass 1: Normal processing
    logger.info("\nPass 1: Standard processing")
    img = preprocess_image(image_path, enhancement_level=0)
    img_bytes, size = resize_for_ocr(img, target_kb=200)
    logger.info(f"  Image size: {size}, {len(img_bytes)/1024:.1f}KB")
    
    response = ocr_with_params(img_bytes, language)
    if response:
        detections = extract_text_with_confidence(response)
        logger.info(f"  Found {len(detections)} text regions")
        all_detections.extend(detections)
    
    # Pass 2: Enhanced contrast
    logger.info("\nPass 2: Enhanced contrast")
    img = preprocess_image(image_path, enhancement_level=1)
    img_bytes, size = resize_for_ocr(img, target_kb=180)
    
    response = ocr_with_params(img_bytes, language)
    if response:
        detections = extract_text_with_confidence(response)
        logger.info(f"  Found {len(detections)} text regions")
        
        # Add new detections not in first pass
        existing_texts = {d['text'] for d in all_detections}
        for det in detections:
            if det['text'] not in existing_texts and det['confidence'] > 0.5:
                all_detections.append(det)
    
    # Pass 3: Different size
    logger.info("\nPass 3: Different resolution")
    img = preprocess_image(image_path, enhancement_level=0)
    img_bytes, size = resize_for_ocr(img, target_kb=300)
    
    response = ocr_with_params(img_bytes, language)
    if response:
        detections = extract_text_with_confidence(response)
        logger.info(f"  Found {len(detections)} text regions")
        
        # Add high-confidence new detections
        existing_texts = {d['text'] for d in all_detections}
        for det in detections:
            if det['text'] not in existing_texts and det['confidence'] > 0.6:
                all_detections.append(det)
    
    return all_detections

def format_final_text(detections):
    """Format detections into readable text."""
    # Group by lines
    lines = merge_text_by_lines(detections)
    
    formatted_text = []
    for line in lines:
        line_text = ' '.join([det['text'] for det in line])
        avg_confidence = sum(det['confidence'] for det in line) / len(line)
        
        # Mark low confidence lines
        if avg_confidence < 0.7:
            line_text = f"[low confidence: {avg_confidence:.2f}] {line_text}"
        
        formatted_text.append(line_text)
    
    return '\n'.join(formatted_text)

def main():
    """Process all manuscript pages with enhanced OCR."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    logger.info("Enhanced OCR Processing - Castor's Manuscripts")
    logger.info("=" * 60)
    logger.info("Using multiple passes and quality enhancements")
    
    # Get images
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path=folder_path,
        client_user_id=client_user_id,
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success':
        logger.error(f"Error: {data.get('error')}")
        return
    
    files = data.get('files', [])
    logger.info(f"\nFound {len(files)} images")
    
    all_pages = []
    
    # Process each image
    for i, file in enumerate(files):
        local_path = file.get('local_path')
        if local_path:
            detections = process_image_multiple_passes(local_path, language='es')
            
            # Format text
            page_text = format_final_text(detections)
            
            # Stats
            total_words = sum(len(d['text'].split()) for d in detections)
            avg_conf = sum(d['confidence'] for d in detections) / len(detections) if detections else 0
            
            logger.info(f"\nPage {i+1} Summary:")
            logger.info(f"  Total detections: {len(detections)}")
            logger.info(f"  Total words: {total_words}")
            logger.info(f"  Average confidence: {avg_conf:.2f}")
            
            all_pages.append({
                'page': i + 1,
                'file': file['name'],
                'text': page_text,
                'stats': {
                    'detections': len(detections),
                    'words': total_words,
                    'confidence': avg_conf
                }
            })
    
    # Save enhanced results
    output_file = "castor_manuscript_enhanced.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - BOOK 1 - ENHANCED MANUSCRIPT TRANSCRIPTION\n")
        f.write("=" * 60 + "\n")
        f.write("Transcribed using NVIDIA PaddleOCR with multiple passes\n")
        f.write("=" * 60 + "\n\n")
        
        for page in all_pages:
            f.write(f"\n{'='*50}\n")
            f.write(f"PAGE {page['page']}: {page['file']}\n")
            f.write(f"Stats: {page['stats']['detections']} detections, ")
            f.write(f"{page['stats']['words']} words, ")
            f.write(f"confidence: {page['stats']['confidence']:.2f}\n")
            f.write(f"{'='*50}\n\n")
            f.write(page['text'])
            f.write("\n\n")
    
    logger.info(f"\n\n✅ Enhanced transcription complete!")
    logger.info(f"   Saved to: {output_file}")
    
    # Upload to Drive
    logger.info("\nUploading to Google Drive...")
    upload_result = drive_tool.upload_file(
        folder_path=folder_path,
        client_user_id=client_user_id,
        file_path=output_file,
        file_name="castor_book1_transcript_enhanced.txt",
        mime_type="text/plain"
    )
    
    upload_data = json.loads(upload_result)
    if upload_data.get('status') == 'success':
        logger.info("✅ Uploaded to Google Drive successfully!")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()