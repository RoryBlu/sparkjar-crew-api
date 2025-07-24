#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Test OCR on a single image."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import os
import base64
import openai
from PIL import Image
import io
import json

def ocr_single_image():
    """Test on just one image."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    logger.info("Testing OCR on single image...")
    
    # Get just one image
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path=folder_path,
        client_user_id=client_user_id,
        download=True,
        max_files=1
    )
    
    data = json.loads(result)
    if data.get('status') != 'success' or not data.get('files'):
        logger.error("Failed to get image")
        return
    
    file = data['files'][0]
    image_path = file['local_path']
    logger.info(f"Image: {file['name']} ({file['size']/1024/1024:.1f}MB)")
    
    # Try OCR with a simple prompt
    client = openai.OpenAI()
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Resize if needed
    img = Image.open(image_path)
    logger.info(f"Original size: {img.size}")
    
    # Resize to reasonable size
    max_dimension = 2048
    if img.width > max_dimension or img.height > max_dimension:
        ratio = max_dimension / max(img.width, img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.info(f"Resized to: {img.size}")
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    base64_image = base64.b64encode(buffer.read()).decode('utf-8')
    
    logger.info("Sending to OpenAI...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using mini for faster response
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all Spanish text from this handwritten page. Just return the text, nothing else."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        text = response.choices[0].message.content
        logger.info(f"\nExtracted text ({len(text)} chars):")
        logger.info("-" * 50)
        logger.info(text)
        
        # Save it
        with open("page1_ocr.txt", "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"\nSaved to: page1_ocr.txt")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    ocr_single_image()