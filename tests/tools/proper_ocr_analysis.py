#!/usr/bin/env python3
"""Properly analyze OCR results against original images."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import openai
import base64
from PIL import Image
import io
import json

def get_actual_ocr_texts():
    """Extract the actual OCR results."""
    with open("castor_manuscript_final.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract each page's text
    pages = []
    
    # Page 1
    start = content.find("PAGE 1: IMG_5610.jpg")
    end = content.find("PAGE 2: IMG_5611.jpg")
    if start != -1 and end != -1:
        text = content[start:end].strip()
        # Get just the text part
        lines = text.split('\n')
        ocr_text = ""
        for i, line in enumerate(lines):
            if line.strip() == "" and i > 2:  # After header and separator
                if i + 1 < len(lines):
                    ocr_text = lines[i + 1].strip()
                break
        pages.append(ocr_text)
    
    # Page 2
    start = content.find("PAGE 2: IMG_5611.jpg")
    end = content.find("PAGE 3: IMG_5612.jpg")
    if start != -1 and end != -1:
        text = content[start:end].strip()
        lines = text.split('\n')
        ocr_text = ""
        for i, line in enumerate(lines):
            if line.strip() == "" and i > 2:
                if i + 1 < len(lines):
                    ocr_text = lines[i + 1].strip()
                break
        pages.append(ocr_text)
    
    # Page 3
    start = content.find("PAGE 3: IMG_5612.jpg")
    if start != -1:
        text = content[start:].strip()
        lines = text.split('\n')
        ocr_text = ""
        for i, line in enumerate(lines):
            if line.strip() == "" and i > 2:
                if i + 1 < len(lines):
                    ocr_text = lines[i + 1].strip()
                break
        pages.append(ocr_text)
    
    return pages

def analyze_page_with_openai(image_path, ocr_text, page_num):
    """Analyze a specific page."""
    client = openai.OpenAI()
    
    # Load and resize image
    with Image.open(image_path) as img:
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
            "content": "You are an expert at transcribing handwritten Spanish manuscripts and evaluating OCR quality."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Page {page_num} OCR Result:
"{ocr_text}"

Words captured by OCR: {len(ocr_text.split())}

Please:
1. Transcribe what you can read from the handwritten page
2. Compare it with the OCR result - what percentage was captured correctly?
3. What are the main errors or missing parts?
4. What's the actual content about?
5. Provide your best transcription of the full page

Be detailed and specific."""
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
        max_tokens=2000
    )
    
    return response.choices[0].message.content

def main():
    """Analyze all pages."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    print("Comprehensive OCR Analysis - Castor's Manuscripts")
    print("=" * 60)
    
    # Get actual OCR texts
    ocr_texts = get_actual_ocr_texts()
    print(f"\nFound OCR results for {len(ocr_texts)} pages")
    
    for i, text in enumerate(ocr_texts):
        print(f"\nPage {i+1} OCR: {len(text.split())} words")
        print(f"Preview: {text[:100]}...")
    
    # Get images
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path=folder_path,
        client_user_id=client_user_id,
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success':
        print("Failed to get images")
        return
    
    files = data.get('files', [])
    
    # Analyze each page
    full_analysis = []
    
    for i, (file, ocr_text) in enumerate(zip(files, ocr_texts)):
        print(f"\n\nAnalyzing Page {i+1} with OpenAI...")
        print("-" * 60)
        
        image_path = file.get('local_path')
        if image_path:
            analysis = analyze_page_with_openai(image_path, ocr_text, i+1)
            full_analysis.append({
                'page': i+1,
                'file': file['name'],
                'ocr_text': ocr_text,
                'analysis': analysis
            })
            
            print(f"Analysis complete for page {i+1}")
    
    # Save comprehensive analysis
    output_file = "castor_ocr_comprehensive_analysis.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ MANUSCRIPT - COMPREHENSIVE OCR ANALYSIS\n")
        f.write("=" * 60 + "\n\n")
        
        for result in full_analysis:
            f.write(f"\n{'='*60}\n")
            f.write(f"PAGE {result['page']}: {result['file']}\n")
            f.write(f"{'='*60}\n\n")
            f.write("OCR RESULT:\n")
            f.write("-" * 40 + "\n")
            f.write(result['ocr_text'] + "\n")
            f.write("-" * 40 + "\n\n")
            f.write("OPENAI ANALYSIS:\n")
            f.write(result['analysis'])
            f.write("\n\n")
    
    print(f"\n\n✅ Analysis complete! Saved to: {output_file}")
    
    # Also create a proper transcription file
    transcription_file = "castor_book1_proper_transcription.txt"
    with open(transcription_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - BOOK 1 - PROPER TRANSCRIPTION\n")
        f.write("=" * 60 + "\n")
        f.write("Transcribed with OpenAI GPT-4 Vision\n")
        f.write("=" * 60 + "\n\n")
        
        for result in full_analysis:
            f.write(f"\n{'='*50}\n")
            f.write(f"PAGE {result['page']}\n")
            f.write(f"{'='*50}\n\n")
            
            # Extract the transcription from analysis
            analysis = result['analysis']
            if "best transcription" in analysis.lower():
                # Find the transcription section
                lines = analysis.split('\n')
                in_transcription = False
                for line in lines:
                    if "best transcription" in line.lower() or "transcription:" in line.lower():
                        in_transcription = True
                        continue
                    if in_transcription and line.strip():
                        f.write(line + "\n")
    
    print(f"Proper transcription saved to: {transcription_file}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()