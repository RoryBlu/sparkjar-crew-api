#!/usr/bin/env python3
"""Multi-pass OCR implementation for improved quality."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import json
import base64
import requests
from PIL import Image
import io
from typing import List, Dict, Tuple

def encode_image_with_size(image_path: str, target_size_kb: int) -> str:
    """Encode image to base64 with specific target size."""
    with Image.open(image_path) as img:
        # Convert RGBA to RGB if necessary
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        
        quality = 95
        scale = 1.0
        
        while True:
            # Resize if scale < 1
            if scale < 1.0:
                new_size = (int(img.width * scale), int(img.height * scale))
                temp_img = img.resize(new_size, Image.Resampling.LANCZOS)
            else:
                temp_img = img
            
            # Save to buffer
            buffer = io.BytesIO()
            temp_img.save(buffer, format='JPEG', quality=quality)
            size_kb = buffer.tell() / 1024
            
            if size_kb <= target_size_kb:
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode('utf-8')
            
            # Adjust parameters
            if quality > 70:
                quality -= 5
            else:
                scale *= 0.9

def perform_ocr_pass(image_path: str, pass_config: Dict) -> Dict:
    """Perform a single OCR pass with specific configuration."""
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_NIM_API_KEY not found in environment variables")
    
    # Encode image with specified size
    target_size = pass_config.get('image_size_kb', 400)
    base64_image = encode_image_with_size(image_path, target_size)
    
    # Prepare request
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
    
    # Add any additional parameters
    if 'params' in pass_config:
        payload.update(pass_config['params'])
    
    url = "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
    
    print(f"Pass {pass_config['name']}: Image size {target_size}KB")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Pass {pass_config['name']} successful")
            return {
                'pass_name': pass_config['name'],
                'config': pass_config,
                'success': True,
                'result': result
            }
        else:
            print(f"✗ Pass {pass_config['name']} failed: {response.status_code}")
            return {
                'pass_name': pass_config['name'],
                'config': pass_config,
                'success': False,
                'error': f"Status {response.status_code}: {response.text}"
            }
    except Exception as e:
        print(f"✗ Pass {pass_config['name']} error: {str(e)}")
        return {
            'pass_name': pass_config['name'],
            'config': pass_config,
            'success': False,
            'error': str(e)
        }

def extract_text_from_result(result: Dict) -> str:
    """Extract text from OCR result."""
    try:
        if 'response' in result and 'text' in result['response']:
            return result['response']['text']
        elif 'text' in result:
            return result['text']
        else:
            # Try to find text in nested structure
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, str) and len(value) > 10:
                        return value
            return ""
    except:
        return ""

def merge_ocr_results(results: List[Dict]) -> str:
    """Merge results from multiple OCR passes."""
    all_texts = []
    
    for pass_result in results:
        if pass_result['success']:
            text = extract_text_from_result(pass_result['result'])
            if text:
                all_texts.append({
                    'pass': pass_result['pass_name'],
                    'text': text,
                    'words': len(text.split())
                })
    
    if not all_texts:
        return ""
    
    # For now, return the pass with most words
    # In future, implement more sophisticated merging
    best = max(all_texts, key=lambda x: x['words'])
    print(f"\nBest result from {best['pass']} with {best['words']} words")
    
    return best['text']

def multi_pass_ocr(image_path: str) -> str:
    """Perform multiple OCR passes with different configurations."""
    print(f"\nPerforming multi-pass OCR on: {image_path}")
    print("=" * 60)
    
    # Define multiple pass configurations
    pass_configs = [
        {
            'name': 'Standard 400KB',
            'image_size_kb': 400,
            'params': {}
        },
        {
            'name': 'High Quality 180KB',
            'image_size_kb': 180,
            'params': {}
        },
        {
            'name': 'Ultra Compressed 100KB',
            'image_size_kb': 100,
            'params': {}
        },
        {
            'name': 'Medium Quality 250KB',
            'image_size_kb': 250,
            'params': {}
        }
    ]
    
    # Perform all passes
    results = []
    for config in pass_configs:
        result = perform_ocr_pass(image_path, config)
        results.append(result)
    
    # Merge results
    final_text = merge_ocr_results(results)
    
    # Save detailed results
    with open(f"multi_pass_results_{Path(image_path).stem}.json", 'w') as f:
        json.dump({
            'image': image_path,
            'passes': results,
            'final_text': final_text
        }, f, indent=2)
    
    return final_text

def process_all_manuscripts():
    """Process all manuscript pages with multi-pass OCR."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    print("Multi-Pass OCR Processing for Castor's Manuscripts")
    print("=" * 60)
    
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
    
    # Process each page
    all_results = []
    
    for i, file in enumerate(files):
        print(f"\n\nProcessing Page {i+1}: {file['name']}")
        print("-" * 60)
        
        image_path = file.get('local_path')
        if image_path:
            text = multi_pass_ocr(image_path)
            
            all_results.append({
                'page': i+1,
                'file': file['name'],
                'text': text,
                'words': len(text.split())
            })
    
    # Save final results
    output_file = "castor_multipass_final.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - BOOK 1 - MULTI-PASS OCR RESULTS\n")
        f.write("=" * 60 + "\n\n")
        
        total_words = 0
        for result in all_results:
            f.write(f"\nPAGE {result['page']}: {result['file']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Words captured: {result['words']}\n\n")
            f.write(result['text'] + "\n")
            f.write("-" * 40 + "\n\n")
            total_words += result['words']
        
        f.write(f"\nTOTAL WORDS CAPTURED: {total_words}\n")
    
    print(f"\n\n✅ Multi-pass OCR complete!")
    print(f"Results saved to: {output_file}")
    print(f"Total words captured: {total_words}")
    
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
    process_all_manuscripts()