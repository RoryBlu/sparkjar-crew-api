#!/usr/bin/env python3
"""Multi-tier OCR strategy using nano liberally and mini strategically."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import json
import openai
import base64
from PIL import Image
import io
from .tools.google_drive_tool import GoogleDriveTool
import re

class MultiTierOCR:
    """Cost-optimized OCR using multiple nano passes before mini."""
    
    def __init__(self):
        self.client = openai.OpenAI()
        self.nano_passes = []
        
    def encode_image(self, image_path: str, target_kb: int = 400) -> tuple:
        """Encode image to target size."""
        with Image.open(image_path) as img:
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            
            # Try quality levels first
            for quality in [95, 85, 75, 65]:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality)
                size_kb = buffer.tell() / 1024
                
                if size_kb <= target_kb:
                    buffer.seek(0)
                    return base64.b64encode(buffer.read()).decode('utf-8'), size_kb
            
            # Need to resize
            scale = 0.8
            new_size = (int(img.width * scale), int(img.height * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            resized.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            size_kb = buffer.tell() / 1024
            
            return base64.b64encode(buffer.read()).decode('utf-8'), size_kb
    
    def nano_pass_1_structure(self, base64_image: str) -> dict:
        """First nano pass: Get page structure and statistics."""
        print("\n🔍 Nano Pass 1: Analyzing page structure...")
        
        messages = [
            {
                "role": "system",
                "content": "Analyze this handwritten Spanish manuscript page. Report: 1) Total word count 2) Number of paragraphs 3) Any page numbers 4) Writing density (sparse/normal/dense) 5) Readability (clear/moderate/difficult)"
            },
            {
                "role": "user",
                "content": [{
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }]
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            max_tokens=200
        )
        
        analysis = response.choices[0].message.content
        print(f"Structure: {analysis}")
        
        # Extract word count
        word_count_match = re.search(r'(\d+)\s*word', analysis, re.IGNORECASE)
        word_count = int(word_count_match.group(1)) if word_count_match else 200
        
        return {
            "analysis": analysis,
            "estimated_words": word_count,
            "pass": 1
        }
    
    def nano_pass_2_extract(self, base64_image: str) -> dict:
        """Second nano pass: Extract all readable text."""
        print("\n📝 Nano Pass 2: Extracting readable text...")
        
        messages = [
            {
                "role": "system",
                "content": "Extract ALL handwritten Spanish text from this manuscript. Include misspellings and slang. For unclear words, use [?] placeholder. Preserve line breaks."
            },
            {
                "role": "user",
                "content": [{
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }]
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            max_tokens=2000
        )
        
        extracted_text = response.choices[0].message.content
        word_count = len(extracted_text.split())
        unclear_count = extracted_text.count('[?]')
        
        print(f"Extracted: {word_count} words, {unclear_count} unclear")
        
        return {
            "text": extracted_text,
            "word_count": word_count,
            "unclear_sections": unclear_count,
            "pass": 2
        }
    
    def nano_pass_3_gaps(self, base64_image: str, extracted_text: str, target_words: int) -> dict:
        """Third nano pass: Identify specific gaps and problem areas."""
        print("\n🔎 Nano Pass 3: Identifying gaps...")
        
        current_words = len(extracted_text.split())
        missing_words = target_words - current_words
        
        messages = [
            {
                "role": "system",
                "content": f"Previous extraction got {current_words} of ~{target_words} words. Identify: 1) Which lines/sections are missing text 2) Words marked with [?] that need clarification 3) Specific areas that are hard to read. Format: Line X: missing Y words after 'abc'"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Current extraction:\n{extracted_text}\n\nIdentify gaps:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            max_tokens=500
        )
        
        gaps_analysis = response.choices[0].message.content
        print(f"Gaps identified: {gaps_analysis[:200]}...")
        
        return {
            "gaps": gaps_analysis,
            "missing_words": missing_words,
            "pass": 3
        }
    
    def nano_pass_4_focus(self, base64_image: str, gaps: str) -> dict:
        """Fourth nano pass: Try to read specific problem areas."""
        print("\n🎯 Nano Pass 4: Focused extraction on gaps...")
        
        messages = [
            {
                "role": "system",
                "content": "Focus ONLY on these specific gaps and try to extract the missing text. Don't repeat already extracted text."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Gaps to focus on:\n{gaps}\n\nExtract ONLY these missing sections:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            max_tokens=1000
        )
        
        additional_text = response.choices[0].message.content
        print(f"Additional text found: {len(additional_text.split())} words")
        
        return {
            "additional_text": additional_text,
            "pass": 4
        }
    
    def mini_final_pass(self, base64_image: str, nano_results: dict) -> str:
        """Mini pass: Fill remaining gaps with context from nano."""
        print("\n✨ Mini Pass: Filling remaining gaps with context...")
        
        # Combine nano findings
        context = f"""Nano extracted {nano_results['pass2']['word_count']} of ~{nano_results['pass1']['estimated_words']} words.

Current text:
{nano_results['pass2']['text']}

Additional fragments:
{nano_results['pass4']['additional_text']}

Still missing: {nano_results['pass3']['gaps']}"""
        
        messages = [
            {
                "role": "system",
                "content": "Complete this Spanish manuscript transcription. Fill ONLY the gaps identified. Preserve Cuban slang and informal language. Don't correct grammar."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": context
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=2000
        )
        
        final_text = response.choices[0].message.content
        
        return final_text
    
    def process_page(self, image_path: str) -> dict:
        """Process a page using multi-tier strategy."""
        print(f"\n{'='*60}")
        print(f"Processing: {Path(image_path).name}")
        print(f"{'='*60}")
        
        # Encode image once
        base64_image, size_kb = self.encode_image(image_path)
        print(f"Image size: {size_kb:.1f}KB")
        
        # Multiple nano passes
        results = {}
        results['pass1'] = self.nano_pass_1_structure(base64_image)
        results['pass2'] = self.nano_pass_2_extract(base64_image)
        results['pass3'] = self.nano_pass_3_gaps(
            base64_image, 
            results['pass2']['text'],
            results['pass1']['estimated_words']
        )
        results['pass4'] = self.nano_pass_4_focus(base64_image, results['pass3']['gaps'])
        
        # Only use mini if still missing significant text
        if results['pass3']['missing_words'] > 20:
            final_text = self.mini_final_pass(base64_image, results)
        else:
            # Combine nano results
            final_text = results['pass2']['text']
            if results['pass4']['additional_text']:
                final_text += "\n\n" + results['pass4']['additional_text']
        
        return {
            "image": Path(image_path).name,
            "image_size_kb": size_kb,
            "nano_passes": 4,
            "mini_used": results['pass3']['missing_words'] > 20,
            "estimated_words": results['pass1']['estimated_words'],
            "extracted_words": len(final_text.split()),
            "final_text": final_text
        }

def main():
    """Process manuscript with multi-tier strategy."""
    # Get images
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989",
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success':
        print("Failed to get images")
        return
    
    ocr = MultiTierOCR()
    all_results = []
    
    # Process first 3 pages
    for file in data.get('files', [])[:3]:
        if file.get('local_path'):
            result = ocr.process_page(file['local_path'])
            all_results.append(result)
    
    # Save results
    output_file = "castor_multi_tier_ocr_results.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - MULTI-TIER OCR RESULTS\n")
        f.write("=" * 60 + "\n\n")
        f.write("Strategy: 4 nano passes + mini only for gaps\n")
        f.write("=" * 60 + "\n\n")
        
        total_nano_cost = 0
        total_mini_cost = 0
        
        for i, result in enumerate(all_results):
            f.write(f"\nPAGE {i+1}: {result['image']}\n")
            f.write("-" * 50 + "\n")
            f.write(f"Estimated words: {result['estimated_words']}\n")
            f.write(f"Extracted words: {result['extracted_words']}\n")
            f.write(f"Mini used: {'Yes' if result['mini_used'] else 'No (nano sufficient)'}\n\n")
            f.write("TRANSCRIPTION:\n")
            f.write(result['final_text'] + "\n")
            f.write("-" * 50 + "\n\n")
            
            # Rough cost estimate (4 nano passes vs 1 mini pass)
            total_nano_cost += 4  # 4 nano passes
            if result['mini_used']:
                total_mini_cost += 1
        
        f.write(f"\nCOST SUMMARY:\n")
        f.write(f"Total nano passes: {total_nano_cost} (virtually free)\n")
        f.write(f"Total mini passes: {total_mini_cost} (used only when needed)\n")
        f.write(f"Cost optimization: Used expensive mini only {total_mini_cost}/{len(all_results)} times\n")
    
    print(f"\n✅ Multi-tier OCR complete!")
    print(f"Results saved to: {output_file}")
    
    # Upload to Drive
    print("\nUploading to Google Drive...")
    upload_result = drive_tool._run(
        action="upload",
        file_path=output_file,
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989"
    )
    print(f"Upload: {json.loads(upload_result).get('status')}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()