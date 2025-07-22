#!/usr/bin/env python3
"""Improved multi-pass OCR with quality enhancements."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import json
import openai
from .tools.ocr_tool import OCRTool
from .tools.google_drive_tool import GoogleDriveTool
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io
import base64

class ImprovedOCR:
    """Improved OCR with preprocessing and post-processing."""
    
    def __init__(self):
        self.ocr_tool = OCRTool()
        self.openai_client = openai.OpenAI()
    
    def preprocess_image(self, image_path: str, method: str = "standard") -> str:
        """Apply different preprocessing methods to improve OCR."""
        img = cv2.imread(image_path)
        
        if method == "standard":
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Apply slight blur to reduce noise
            processed = cv2.GaussianBlur(gray, (3, 3), 0)
            
        elif method == "adaptive_threshold":
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Apply adaptive thresholding
            processed = cv2.adaptiveThreshold(gray, 255, 
                                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY, 11, 2)
            
        elif method == "enhance_contrast":
            # Using PIL for enhancement
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(pil_img)
            enhanced = enhancer.enhance(2.0)
            # Convert back to cv2
            processed = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2GRAY)
            
        elif method == "denoise":
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Apply denoising
            processed = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
        else:  # "original"
            return image_path
        
        # Save processed image
        temp_path = f"/tmp/processed_{method}_{Path(image_path).name}"
        cv2.imwrite(temp_path, processed)
        return temp_path
    
    def multi_pass_ocr(self, image_path: str) -> dict:
        """Perform multiple OCR passes with different preprocessing."""
        results = []
        
        # Different preprocessing methods
        methods = ["original", "standard", "adaptive_threshold", "enhance_contrast", "denoise"]
        
        for method in methods:
            print(f"\nTrying method: {method}")
            
            # Preprocess image
            processed_path = self.preprocess_image(image_path, method)
            
            # Run OCR
            result_json = self.ocr_tool._run(
                image_path=processed_path,
                language="es",  # Spanish
                detect_direction=False
            )
            
            result = json.loads(result_json)
            
            if result['success']:
                results.append({
                    'method': method,
                    'text': result.get('text', ''),
                    'words': result.get('word_count', 0),
                    'confidence': result.get('confidence', 0)
                })
                print(f"  Words: {result.get('word_count', 0)}, Confidence: {result.get('confidence', 0):.2f}")
            
            # Clean up temp file
            if processed_path != image_path:
                Path(processed_path).unlink(missing_ok=True)
        
        # Select best result (highest word count with good confidence)
        best = max(results, key=lambda x: x['words'] * x['confidence'])
        
        return {
            'best_method': best['method'],
            'text': best['text'],
            'words': best['words'],
            'confidence': best['confidence'],
            'all_results': results
        }
    
    def post_process_with_llm(self, ocr_text: str, image_path: str) -> str:
        """Use LLM to improve OCR results based on context."""
        # Load image for visual analysis
        with Image.open(image_path) as img:
            # Resize for API
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
                "content": "You are an expert at improving OCR results from handwritten Spanish manuscripts."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""The OCR captured this text from a handwritten Spanish manuscript:

"{ocr_text}"

Based on the image and common Spanish patterns, please:
1. Correct obvious OCR errors
2. Fix word boundaries
3. Add proper Spanish accents
4. Maintain the original meaning

Return ONLY the corrected text, nothing else."""
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
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using available model (will update later)
            messages=messages,
            max_tokens=1000
        )
        
        return response.choices[0].message.content

def main():
    """Process all manuscripts with improved OCR."""
    print("Improved Multi-Pass OCR Processing")
    print("=" * 60)
    
    # Initialize
    improved_ocr = ImprovedOCR()
    drive_tool = GoogleDriveTool()
    
    # Get images
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
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
    
    # Process each page
    final_results = []
    
    for i, file in enumerate(files):
        print(f"\n\nProcessing Page {i+1}: {file['name']}")
        print("=" * 60)
        
        image_path = file.get('local_path')
        if image_path:
            # Multi-pass OCR
            ocr_result = improved_ocr.multi_pass_ocr(image_path)
            
            print(f"\nBest method: {ocr_result['best_method']}")
            print(f"Words captured: {ocr_result['words']}")
            print(f"Confidence: {ocr_result['confidence']:.2f}")
            
            # Post-process with LLM
            print("\nImproving with LLM...")
            improved_text = improved_ocr.post_process_with_llm(
                ocr_result['text'], 
                image_path
            )
            
            final_results.append({
                'page': i+1,
                'file': file['name'],
                'ocr_text': ocr_result['text'],
                'improved_text': improved_text,
                'ocr_words': ocr_result['words'],
                'improved_words': len(improved_text.split()),
                'best_method': ocr_result['best_method'],
                'confidence': ocr_result['confidence']
            })
    
    # Save results
    output_file = "castor_improved_ocr_final.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - BOOK 1 - IMPROVED OCR WITH LLM POST-PROCESSING\n")
        f.write("=" * 60 + "\n\n")
        
        total_ocr_words = 0
        total_improved_words = 0
        
        for result in final_results:
            f.write(f"\nPAGE {result['page']}: {result['file']}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Best OCR Method: {result['best_method']}\n")
            f.write(f"OCR Confidence: {result['confidence']:.2f}\n\n")
            
            f.write("RAW OCR TEXT:\n")
            f.write("-" * 40 + "\n")
            f.write(result['ocr_text'] + "\n")
            f.write(f"Words: {result['ocr_words']}\n\n")
            
            f.write("IMPROVED TEXT:\n")
            f.write("-" * 40 + "\n")
            f.write(result['improved_text'] + "\n")
            f.write(f"Words: {result['improved_words']}\n")
            f.write("=" * 50 + "\n\n")
            
            total_ocr_words += result['ocr_words']
            total_improved_words += result['improved_words']
        
        f.write("\nSUMMARY:\n")
        f.write(f"Total OCR words: {total_ocr_words}\n")
        f.write(f"Total improved words: {total_improved_words}\n")
        f.write(f"Improvement: +{total_improved_words - total_ocr_words} words "
                f"({(total_improved_words/total_ocr_words - 1)*100:.1f}% increase)\n")
    
    print(f"\n\n✅ Improved OCR complete!")
    print(f"Results saved to: {output_file}")
    
    # Upload to Google Drive
    print("\nUploading results to Google Drive...")
    upload_result = drive_tool._run(
        action="upload",
        file_path=output_file,
        folder_path=folder_path,
        client_user_id=client_user_id
    )
    print(f"Upload result: {upload_result}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()