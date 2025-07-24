#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""OCR using OpenAI Vision API."""
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

def resize_for_openai(image_path, max_size_mb=20):
    """Resize image for OpenAI (max 20MB)."""
    with Image.open(image_path) as img:
        # Convert RGBA to RGB
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        
        # Check size
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        size_mb = len(buffer.getvalue()) / (1024 * 1024)
        
        if size_mb <= max_size_mb:
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Resize if needed
        scale = (max_size_mb / size_mb) ** 0.5
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        resized.save(buffer, format='JPEG', quality=85)
        logger.info(f"   Resized from {img.size} to {new_size} ({len(buffer.getvalue())/1024/1024:.1f}MB)")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

def ocr_with_gpt4(image_path, language='Spanish'):
    """Use GPT-4 Vision for OCR."""
    logger.info(f"\nProcessing: {Path(image_path).name}")
    logger.info("-" * 50)
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    client = openai.OpenAI(api_key=api_key)
    
    # Encode image
    base64_image = resize_for_openai(image_path)
    
    # Prepare messages
    messages = [
        {
            "role": "system",
            "content": f"You are an expert OCR system specializing in {language} handwritten manuscripts. Extract ALL text from the image, preserving the original layout as much as possible. Include even partially visible or unclear text, marking uncertain words with [?]. For cursive {language} text, pay special attention to accents and special characters."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Please extract all {language} text from this handwritten manuscript page. Preserve line breaks and formatting. Mark any uncertain words with [?]."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]
    
    try:
        # Use GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o as requested, but will update to gpt-4.1-mini later
            messages=messages,
            max_tokens=4000,
            temperature=0.1
        )
        
        text = response.choices[0].message.content
        logger.info(f"✅ Extracted {len(text)} characters")
        return text
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

def main():
    """Process Castor's manuscripts with OpenAI."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    logger.info("OCR with OpenAI Vision - Castor's Spanish Manuscripts")
    logger.info("=" * 50)
    
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
    logger.info(f"Found {len(files)} images\n")
    
    # Process each image
    all_texts = []
    for i, file in enumerate(files):
        local_path = file.get('local_path')
        if local_path:
            text = ocr_with_gpt4(local_path, language='Spanish')
            if text:
                all_texts.append(f"\n\n{'='*50}\nPAGE {i+1}: {file['name']}\n{'='*50}\n\n{text}")
    
    # Save results
    if all_texts:
        output_file = "castor_manuscript_transcription.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("CASTOR GONZALEZ - BOOK 1 - MANUSCRIPT TRANSCRIPTION\n")
            f.write("=" * 60 + "\n")
            f.write(f"Transcribed using OpenAI GPT-4 Vision\n")
            f.write(f"Total pages: {len(all_texts)}\n")
            f.write("=" * 60)
            f.write(''.join(all_texts))
        
        logger.info(f"\n✅ Transcription complete!")
        logger.info(f"   Saved to: {output_file}")
        logger.info(f"   Pages transcribed: {len(all_texts)}")
        
        # Also print the text
        logger.info("\nTRANSCRIPTION PREVIEW:")
        logger.info("=" * 60)
        for text in all_texts:
            logger.info(text[:500] + "..." if len(text) > 500 else text)
    else:
        logger.info("\n❌ No text extracted")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()