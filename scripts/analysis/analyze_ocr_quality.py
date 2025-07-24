#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Analyze OCR quality by comparing with OpenAI Vision."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import openai
import base64
from PIL import Image
import io
import json

def analyze_with_openai(image_path, ocr_result):
    """Use OpenAI to analyze what the OCR missed."""
    client = openai.OpenAI()
    
    # Load and resize image for OpenAI
    with Image.open(image_path) as img:
        # Resize if needed
        max_dim = 2048
        if img.width > max_dim or img.height > max_dim:
            ratio = max_dim / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        base64_image = base64.b64encode(buffer.read()).decode('utf-8')
    
    messages = [
        {
            "role": "system",
            "content": "You are an expert at analyzing handwritten Spanish manuscripts and OCR quality."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""I have a handwritten Spanish manuscript page. An OCR system extracted this text:

"{ocr_result}"

Please analyze:
1. How much of the page content was captured? (estimate percentage)
2. What type of content is this? (letter, diary, story, etc.)
3. Are there obvious missing sections?
4. What's the general topic/content of the text?
5. Estimate: how many words should be on this page vs how many were captured?

Please be specific and analytical."""
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
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000
    )
    
    return response.choices[0].message.content

def main():
    """Analyze OCR quality."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    # Read current OCR results
    with open("castor_manuscript_final.txt", "r", encoding="utf-8") as f:
        ocr_content = f.read()
    
    # Extract individual page results - get the actual text from page 1
    # The text is on line 12 of the file
    lines = ocr_content.split('\n')
    page1_text = ""
    for i, line in enumerate(lines):
        if "PAGE 1: IMG_5610.jpg" in line:
            # Get the text which is 2 lines after the page header
            if i + 2 < len(lines):
                page1_text = lines[i + 2]
            break
    
    logger.info("OCR Quality Analysis")
    logger.info("=" * 60)
    logger.info("\nCurrent OCR Result (Page 1):")
    logger.info("-" * 40)
    logger.info(page1_text)
    logger.info("-" * 40)
    logger.info(f"Words captured: {len(page1_text.split())}")
    logger.info(f"Characters: {len(page1_text)}")
    
    # Get the first image
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path=folder_path,
        client_user_id=client_user_id,
        download=True,
        max_files=1
    )
    
    data = json.loads(result)
    if data.get('status') == 'success' and data.get('files'):
        file = data['files'][0]
        image_path = file.get('local_path')
        
        if image_path:
            logger.info("\n\nAnalyzing with OpenAI Vision...")
            logger.info("=" * 60)
            
            analysis = analyze_with_openai(image_path, page1_text)
            logger.info(analysis)
            
            # Save analysis
            with open("ocr_quality_analysis.txt", "w", encoding="utf-8") as f:
                f.write("OCR QUALITY ANALYSIS\n")
                f.write("=" * 60 + "\n\n")
                f.write("Current OCR Output:\n")
                f.write("-" * 40 + "\n")
                f.write(page1_text + "\n")
                f.write("-" * 40 + "\n\n")
                f.write("OpenAI Analysis:\n")
                f.write(analysis)
            
            logger.info("\n\nAnalysis saved to: ocr_quality_analysis.txt")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()