#!/usr/bin/env python3
"""Test script for PaddleOCRTool"""

import os
import sys

# Add the crew-api src directory to the path
sys.path.insert(0, '/Users/r.t.rawlings/sparkjar-crew/services/crew-api/src')

from sparkjar_shared.tools.paddle_ocr_tool import PaddleOCRTool

def test_paddle_ocr():
    # Initialize the tool
    tool = PaddleOCRTool()
    
    # Test with the whiteboard image
    image_path = "OCR/32337 Large Medium.png"
    
    print(f"Testing PaddleOCRTool with image: {image_path}")
    print(f"File size: {os.path.getsize(image_path) / 1024:.2f} KB")
    print("-" * 50)
    
    # Run OCR
    result = tool._run(image_path)
    
    print("OCR Result:")
    print(result)
    
    if "too large" in result:
        print("\n" + "="*50)
        print("NOTE: The tool is working correctly!")
        print("The image is too large for base64 encoding.")
        print("Options:")
        print("1. Use a smaller image (< 180KB)")
        print("2. Host the image online and use its URL")
        print("3. Use an image optimization tool to reduce size")
        print("="*50)
    
    # Extract and display recognized text
    if isinstance(result, str) and result.startswith("OCR completed"):
        print("\n" + "="*50)
        print("✅ OCR SUCCESSFUL!")
        print("="*50)
        print("\nExtracted Text (sorted by confidence):")
        print("-"*50)
        
        # Extract the raw response
        try:
            import ast
            raw_response_str = result.split("Raw response: ")[1]
            raw_response = ast.literal_eval(raw_response_str)
            
            if 'data' in raw_response and len(raw_response['data']) > 0:
                detections = raw_response['data'][0].get('text_detections', [])
                
                # Sort by confidence
                sorted_detections = sorted(
                    detections, 
                    key=lambda x: x['text_prediction']['confidence'], 
                    reverse=True
                )
                
                for detection in sorted_detections:
                    text = detection['text_prediction']['text']
                    confidence = detection['text_prediction']['confidence']
                    print(f"{text:20} (confidence: {confidence:.2%})")
        except Exception as e:
            print(f"Error parsing response: {e}")

if __name__ == "__main__":
    # Check if NVIDIA_API_KEY is set
    if not os.getenv("NVIDIA_API_KEY"):
        print("Error: NVIDIA_API_KEY environment variable is not set!")
        print("Please set it with: export NVIDIA_API_KEY='your-api-key'")
        sys.exit(1)
    
    test_paddle_ocr()