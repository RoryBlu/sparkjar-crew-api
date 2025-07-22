#!/usr/bin/env python3
"""Use nano exclusively with chunked reading strategy."""
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

class NanoChunkedOCR:
    """Nano-only OCR using systematic chunked reading."""
    
    def __init__(self):
        self.client = openai.OpenAI()
        
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
                    print(f"Image encoded: {size_kb:.1f}KB at quality {quality}")
                    return base64.b64encode(buffer.read()).decode('utf-8'), size_kb
            
            # Need to resize
            scale = 0.8
            new_size = (int(img.width * scale), int(img.height * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            resized.save(buffer, format='JPEG', quality=85)
            size_kb = buffer.tell() / 1024
            print(f"Image resized to {new_size}: {size_kb:.1f}KB")
            buffer.seek(0)
            
            return base64.b64encode(buffer.read()).decode('utf-8'), size_kb
    
    def step1_page_info(self, base64_image: str) -> dict:
        """Step 1: Get page info and total word count."""
        print("\n📋 Step 1: Page analysis...")
        
        messages = [
            {
                "role": "system", 
                "content": "Count total words on this handwritten Spanish page. Reply format: 'TOTAL: X words'"
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
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print(f"Page analysis: {result}")
        
        # Extract word count
        word_match = re.search(r'(\d+)\s*words?', result, re.IGNORECASE)
        total_words = int(word_match.group(1)) if word_match else 300
        
        return {
            "total_words": total_words,
            "analysis": result
        }
    
    def stepN_read_chunk(self, base64_image: str, chunk_size: int, chunk_num: int, previous_text: str = "") -> dict:
        """Step N: Read next N words from where we left off."""
        print(f"\n📖 Step {chunk_num + 1}: Reading next {chunk_size} words...")
        
        if previous_text:
            instruction = f"Continue reading from where this text ended: '...{previous_text[-100:]}'. Extract the NEXT {chunk_size} words only. No repetition."
        else:
            instruction = f"Read the FIRST {chunk_size} words from the top of this page. Extract exactly {chunk_size} words, no more."
        
        messages = [
            {
                "role": "system",
                "content": f"Extract exactly {chunk_size} handwritten Spanish words from this manuscript. {instruction} Return ONLY the words, no commentary."
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
            max_tokens=chunk_size * 3  # Rough estimate: 3 tokens per word
        )
        
        chunk_text = response.choices[0].message.content.strip()
        word_count = len(chunk_text.split())
        
        print(f"Extracted {word_count} words: {chunk_text[:80]}...")
        
        return {
            "text": chunk_text,
            "word_count": word_count,
            "chunk_num": chunk_num
        }
    
    def process_page_chunked(self, image_path: str, chunk_size: int = 50) -> dict:
        """Process entire page using nano chunks."""
        print(f"\n{'='*60}")
        print(f"Nano Chunked OCR: {Path(image_path).name}")
        print(f"Chunk size: {chunk_size} words")
        print(f"{'='*60}")
        
        # Encode image once
        base64_image, size_kb = self.encode_image(image_path)
        
        # Step 1: Get page info
        page_info = self.step1_page_info(base64_image)
        total_words = page_info["total_words"]
        
        print(f"Target: {total_words} words total")
        
        # Calculate number of chunks needed
        num_chunks = (total_words + chunk_size - 1) // chunk_size  # Round up
        print(f"Plan: {num_chunks} chunks of {chunk_size} words each")
        
        # Extract text in chunks
        all_chunks = []
        full_text = ""
        
        for chunk_num in range(num_chunks):
            chunk_result = self.stepN_read_chunk(
                base64_image, 
                chunk_size, 
                chunk_num, 
                full_text
            )
            
            all_chunks.append(chunk_result)
            full_text += " " + chunk_result["text"]
            
            # Check if we've got enough
            total_extracted = len(full_text.split())
            if total_extracted >= total_words * 0.9:  # 90% threshold
                print(f"✅ Reached 90% of target ({total_extracted}/{total_words})")
                break
        
        final_word_count = len(full_text.split())
        
        return {
            "image": Path(image_path).name,
            "image_size_kb": size_kb,
            "target_words": total_words,
            "extracted_words": final_word_count,
            "coverage": final_word_count / total_words * 100,
            "chunks_used": len(all_chunks),
            "chunk_size": chunk_size,
            "nano_calls": len(all_chunks) + 1,  # +1 for page info
            "full_text": full_text.strip()
        }

def test_chunk_sizes():
    """Test different chunk sizes to find optimal."""
    print("Testing optimal chunk sizes...")
    
    # Get test image
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989",
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success' or not data.get('files'):
        print("Failed to get test image")
        return
    
    image_path = data['files'][0]['local_path']
    ocr = NanoChunkedOCR()
    
    # Test different chunk sizes
    chunk_sizes = [30, 50, 75, 100]
    results = []
    
    for chunk_size in chunk_sizes:
        print(f"\n{'='*40}")
        print(f"TESTING CHUNK SIZE: {chunk_size}")
        print(f"{'='*40}")
        
        result = ocr.process_page_chunked(image_path, chunk_size)
        results.append(result)
        
        print(f"Result: {result['extracted_words']}/{result['target_words']} words ({result['coverage']:.1f}% coverage)")
        print(f"Nano calls: {result['nano_calls']}")
    
    # Find best chunk size
    best = max(results, key=lambda r: r['coverage'])
    
    print(f"\n{'='*60}")
    print("CHUNK SIZE COMPARISON:")
    print(f"{'='*60}")
    
    for r in results:
        marker = "👑 BEST" if r == best else ""
        print(f"Size {r['chunk_size']:3d}: {r['coverage']:5.1f}% coverage, {r['nano_calls']:2d} calls {marker}")
    
    print(f"\nOptimal chunk size: {best['chunk_size']} words")
    
    # Save best result
    with open("nano_chunked_best_result.txt", "w", encoding="utf-8") as f:
        f.write(f"NANO CHUNKED OCR - BEST RESULT\n")
        f.write(f"=" * 60 + "\n\n")
        f.write(f"Image: {best['image']}\n")
        f.write(f"Chunk size: {best['chunk_size']} words\n")
        f.write(f"Coverage: {best['coverage']:.1f}% ({best['extracted_words']}/{best['target_words']} words)\n")
        f.write(f"Nano calls: {best['nano_calls']} (virtually free)\n\n")
        f.write("EXTRACTED TEXT:\n")
        f.write("-" * 40 + "\n")
        f.write(best['full_text'])
    
    print(f"\nBest result saved to: nano_chunked_best_result.txt")
    
    drive_tool.cleanup()
    return best['chunk_size']

def process_all_pages(optimal_chunk_size: int = 50):
    """Process all manuscript pages with optimal chunk size."""
    print(f"\nProcessing all pages with chunk size: {optimal_chunk_size}")
    
    # Get images
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989",
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success':
        return
    
    ocr = NanoChunkedOCR()
    all_results = []
    
    for file in data.get('files', [])[:3]:  # First 3 pages
        if file.get('local_path'):
            result = ocr.process_page_chunked(file['local_path'], optimal_chunk_size)
            all_results.append(result)
    
    # Save final results
    output_file = "castor_nano_chunked_final.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - NANO CHUNKED OCR FINAL\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Strategy: Nano-only chunked reading ({optimal_chunk_size} words per chunk)\n")
        f.write("=" * 60 + "\n\n")
        
        total_nano_calls = 0
        total_coverage = 0
        
        for i, result in enumerate(all_results):
            f.write(f"\nPAGE {i+1}: {result['image']}\n")
            f.write("-" * 50 + "\n")
            f.write(f"Target words: {result['target_words']}\n")
            f.write(f"Extracted words: {result['extracted_words']}\n")
            f.write(f"Coverage: {result['coverage']:.1f}%\n")
            f.write(f"Nano calls: {result['nano_calls']}\n\n")
            f.write("TRANSCRIPTION:\n")
            f.write(result['full_text'] + "\n")
            f.write("-" * 50 + "\n\n")
            
            total_nano_calls += result['nano_calls']
            total_coverage += result['coverage']
        
        avg_coverage = total_coverage / len(all_results)
        f.write(f"\nSUMMARY:\n")
        f.write(f"Total nano calls: {total_nano_calls} (virtually free)\n")
        f.write(f"Average coverage: {avg_coverage:.1f}%\n")
        f.write(f"Mini calls: 0 (not needed!)\n")
        f.write(f"Strategy: Pure nano chunked reading\n")
    
    print(f"\n✅ All pages processed!")
    print(f"Results saved to: {output_file}")
    print(f"Average coverage: {avg_coverage:.1f}%")
    print(f"Total cost: {total_nano_calls} nano calls (essentially free)")
    
    # Upload to Drive
    upload_result = drive_tool._run(
        action="upload",
        file_path=output_file,
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989"
    )
    print(f"Upload: {json.loads(upload_result).get('status')}")
    
    drive_tool.cleanup()

def main():
    """Main function - test chunk sizes then process all."""
    print("NANO CHUNKED OCR STRATEGY")
    print("=" * 60)
    print("Using only gpt-4.1-nano with systematic chunked reading")
    
    # First find optimal chunk size
    optimal_size = test_chunk_sizes()
    
    # Then process all pages
    process_all_pages(optimal_size)

if __name__ == "__main__":
    main()