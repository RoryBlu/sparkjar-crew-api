#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Analyze PaddleOCR bounding box coverage to understand page coverage."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import json
import requests
import os
from PIL import Image
import io
import base64

def get_paddleocr_raw_response(image_path: str) -> dict:
    """Get raw PaddleOCR response with bounding boxes."""
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    
    # Load and encode image
    with Image.open(image_path) as img:
        # Get original dimensions
        original_width, original_height = img.size
        logger.info(f"Original image size: {original_width}x{original_height}")
        
        # Resize for API
        scale = 0.8
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        base64_image = base64.b64encode(buffer.read()).decode('utf-8')
    
    # Make request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": [{
            "type": "image_url",
            "url": f"data:image/jpeg;base64,{base64_image}"
        }]
    }
    
    url = "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json(), original_width, original_height
    else:
        return None, 0, 0

def analyze_coverage(response: dict, img_width: int, img_height: int):
    """Analyze page coverage from bounding boxes."""
    if not response or 'data' not in response:
        return
    
    all_boxes = []
    total_words = 0
    
    for data_item in response['data']:
        if 'text_detections' in data_item:
            for detection in data_item['text_detections']:
                if 'bounding_box' in detection and 'text_prediction' in detection:
                    box = detection['bounding_box']['points']
                    text = detection['text_prediction']['text']
                    confidence = detection['text_prediction']['confidence']
                    
                    # Convert normalized coordinates to pixels
                    min_x = min(p['x'] for p in box) * img_width
                    max_x = max(p['x'] for p in box) * img_width
                    min_y = min(p['y'] for p in box) * img_height
                    max_y = max(p['y'] for p in box) * img_height
                    
                    all_boxes.append({
                        'text': text,
                        'confidence': confidence,
                        'min_x': min_x,
                        'max_x': max_x,
                        'min_y': min_y,
                        'max_y': max_y,
                        'width': max_x - min_x,
                        'height': max_y - min_y
                    })
                    
                    total_words += len(text.split())
    
    logger.info(f"\nDetected {len(all_boxes)} text regions")
    logger.info(f"Total words: {total_words}")
    
    # Calculate coverage
    if all_boxes:
        page_min_x = min(b['min_x'] for b in all_boxes)
        page_max_x = max(b['max_x'] for b in all_boxes)
        page_min_y = min(b['min_y'] for b in all_boxes)
        page_max_y = max(b['max_y'] for b in all_boxes)
        
        coverage_width = page_max_x - page_min_x
        coverage_height = page_max_y - page_min_y
        
        logger.info(f"\nPage coverage:")
        logger.info(f"  X range: {page_min_x:.0f} to {page_max_x:.0f} ({coverage_width:.0f} pixels)")
        logger.info(f"  Y range: {page_min_y:.0f} to {page_max_y:.0f} ({coverage_height:.0f} pixels)")
        logger.info(f"  Coverage: {coverage_width/img_width*100:.1f}% width, {coverage_height/img_height*100:.1f}% height")
        
        # Show text regions
        logger.info(f"\nText regions (sorted by position):")
        sorted_boxes = sorted(all_boxes, key=lambda b: (b['min_y'], b['min_x']))
        for i, box in enumerate(sorted_boxes[:10]):  # First 10
            logger.info(f"  {i+1}. '{box['text'][:30]}...' at ({box['min_x']:.0f},{box['min_y']:.0f}) conf:{box['confidence']:.2f}")
    
    return all_boxes

def main():
    """Analyze PaddleOCR coverage."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    logger.info("PaddleOCR Coverage Analysis")
    logger.info("=" * 60)
    
    # Get first manuscript page
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989",
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') == 'success' and data.get('files'):
        image_path = data['files'][0]['local_path']
        logger.info(f"\nAnalyzing: {data['files'][0]['name']}")
        
        # Get PaddleOCR response
        response, width, height = get_paddleocr_raw_response(image_path)
        
        if response:
            # Save full response
            with open("paddleocr_full_response.json", "w") as f:
                json.dump(response, f, indent=2)
            logger.info("\nFull response saved to paddleocr_full_response.json")
            
            # Analyze coverage
            boxes = analyze_coverage(response, width, height)
            
            # Check if it's standard letter size (8.5x11 inches at ~300 DPI)
            expected_width = 8.5 * 300  # 2550 pixels
            expected_height = 11 * 300  # 3300 pixels
            
            logger.info(f"\nPage size analysis:")
            logger.info(f"  Actual: {width}x{height} pixels")
            logger.info(f"  Standard letter at 300 DPI: {expected_width:.0f}x{expected_height:.0f}")
            logger.info(f"  Likely DPI: {width/8.5:.0f} x {height/11:.0f}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()