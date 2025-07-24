#!/usr/bin/env python3
"""Debug OCR response structure."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import json
import base64
import requests
from PIL import Image
import io

# Use the test script that worked before
image_path = "/var/folders/gr/zmt7qq_s31q25pyx8tgyghpr0000gp/T/drive_files_g190gfov/IMG_5610.jpg"

# If not exists, get it
if not os.path.exists(image_path):
    from .tools.google_drive_tool import GoogleDriveTool
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989",
        download=True
    )
    data = json.loads(result)
    if data.get('status') == 'success' and data.get('files'):
        image_path = data['files'][0]['local_path']

# Load and encode image
with Image.open(image_path) as img:
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    
    # Resize to ~400KB
    quality = 85
    scale = 0.8
    new_size = (int(img.width * scale), int(img.height * scale))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)
    base64_image = base64.b64encode(buffer.read()).decode('utf-8')
    print(f"Image size: {buffer.tell() / 1024:.1f}KB")

# Make request
api_key = os.getenv("NVIDIA_NIM_API_KEY")
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

print("Sending request...")
response = requests.post(url, headers=headers, json=payload)

print(f"\nResponse status: {response.status_code}")
print(f"Response headers: {dict(response.headers)}")

if response.status_code == 200:
    result = response.json()
    print("\nFull response structure:")
    print(json.dumps(result, indent=2))
    
    # Try different ways to extract text
    print("\n\nAttempting to extract text:")
    
    # Method 1
    if 'response' in result:
        print(f"Found 'response' key: {type(result['response'])}")
        if isinstance(result['response'], str):
            print(f"Response is string: {result['response'][:200]}...")
        elif isinstance(result['response'], dict):
            print(f"Response is dict with keys: {list(result['response'].keys())}")
    
    # Method 2
    if 'choices' in result:
        print(f"Found 'choices' key")
        for i, choice in enumerate(result.get('choices', [])):
            if 'message' in choice and 'content' in choice['message']:
                print(f"Choice {i} content: {choice['message']['content'][:200]}...")
    
    # Method 3 - check all string values
    print("\nAll string values in response:")
    def find_strings(obj, path=""):
        if isinstance(obj, str) and len(obj) > 10:
            print(f"{path}: {obj[:100]}...")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                find_strings(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                find_strings(v, f"{path}[{i}]")
    
    find_strings(result)
    
else:
    print(f"Error response: {response.text}")