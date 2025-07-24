#!/usr/bin/env python3
"""Resize images and run OCR on Castor's manuscripts."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from .tools.google_drive_tool import GoogleDriveTool
from PIL import Image
import json
import requests
import base64
from io import BytesIO

def resize_image(image_path, max_size_mb=1.0):
    """Resize image to be under max_size_mb."""
    img = Image.open(image_path)
    
    # Calculate current size
    with open(image_path, 'rb') as f:
        current_size_mb = len(f.read()) / (1024 * 1024)
    
    if current_size_mb <= max_size_mb:
        return img
    
    # Calculate resize ratio
    ratio = (max_size_mb / current_size_mb) ** 0.5
    new_size = (int(img.width * ratio), int(img.height * ratio))
    
    # Resize with high quality
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    return img

def ocr_image(image_path, language='es'):
    """Run OCR on an image using the API directly."""
    # Resize if needed
    img = resize_image(image_path)
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    
    # Call OCR API
    url = "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
    headers = {
        "Authorization": "Bearer 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",
        "Accept": "application/json",
    }
    
    payload = {
        "input": {
            "image": img_base64,
            "language": language,
            "det_db_box_thresh": 0.3,
            "drop_score": 0.6,
            "use_direction_classify": True
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Extract text
        text_parts = []
        for segment in result.get('output', {}).get('data', []):
            if isinstance(segment, dict) and 'transcription' in segment:
                text_parts.append(segment['transcription'])
        
        return ' '.join(text_parts)
    except Exception as e:
        print(f"OCR error: {e}")
        return ""

def main():
    """Process Castor's manuscripts with resizing."""
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    print("Processing Castor's Spanish Manuscripts")
    print("=" * 50)
    
    # Get images from Google Drive
    tool = GoogleDriveTool()
    result = tool._run(
        folder_path=folder_path,
        client_user_id=client_user_id,
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success':
        print(f"Error accessing files: {data.get('error')}")
        return
    
    files = data.get('files', [])
    print(f"Found {len(files)} images to process\n")
    
    all_text = []
    for i, file in enumerate(files):
        print(f"Processing {file['name']}...")
        local_path = file.get('local_path')
        
        if local_path:
            text = ocr_image(local_path, language='es')
            if text:
                all_text.append(f"=== {file['name']} ===\n{text}\n")
                print(f"  ✓ Extracted {len(text.split())} words")
            else:
                print(f"  ✗ No text extracted")
        else:
            print(f"  ✗ File not downloaded")
    
    # Save combined text
    if all_text:
        output_file = "castor_book1_ocr.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_text))
        print(f"\n✅ OCR complete! Saved to {output_file}")
        print(f"Total pages processed: {len(all_text)}")
    else:
        print("\n❌ No text was extracted from any images")
    
    # Clean up
    tool.cleanup()

if __name__ == "__main__":
    main()