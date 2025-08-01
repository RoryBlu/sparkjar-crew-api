#!/usr/bin/env python3
"""Test PaddleOCRTool with a URL"""

import os
import sys

# Add the crew-api src directory to the path
sys.path.insert(0, '/Users/r.t.rawlings/sparkjar-crew/services/crew-api/src')

from sparkjar_shared.tools.paddle_ocr_tool import PaddleOCRTool

def test_paddle_ocr_url():
    # Initialize the tool
    tool = PaddleOCRTool()
    
    # Test with a sample image URL (simple text image)
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Example.png/200px-Example.png"
    
    print(f"Testing PaddleOCRTool with URL: {image_url}")
    print("-" * 50)
    
    # Run OCR
    result = tool._run(image_url)
    
    print("OCR Result:")
    print(result)

if __name__ == "__main__":
    # Check if NVIDIA_API_KEY is set
    if not os.getenv("NVIDIA_API_KEY"):
        print("Error: NVIDIA_API_KEY environment variable is not set!")
        print("Please set it with: export NVIDIA_API_KEY='your-api-key'")
        sys.exit(1)
    
    test_paddle_ocr_url()