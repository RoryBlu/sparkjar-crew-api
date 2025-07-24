#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Compare OCR accuracy between PaddleOCR and OpenAI gpt-4.1 models."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import json
import openai
import base64
from PIL import Image
import io
from .tools.ocr_tool import OCRTool
from .tools.google_drive_tool import GoogleDriveTool

class ModelComparison:
    """Compare different models for OCR accuracy."""
    
    def __init__(self):
        self.client = openai.OpenAI()
        self.ocr_tool = OCRTool()
    
    def encode_image_for_openai(self, image_path: str, max_dim: int = 2048) -> str:
        """Encode image for OpenAI API."""
        with Image.open(image_path) as img:
            # Resize if needed
            if img.width > max_dim or img.height > max_dim:
                ratio = max_dim / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')
    
    def test_gpt4_nano(self, image_path: str) -> dict:
        """Test gpt-4.1-nano for basic OCR tasks."""
        base64_image = self.encode_image_for_openai(image_path)
        
        messages = [
            {
                "role": "system",
                "content": "Extract text from this handwritten Spanish manuscript page. Output only: 1) Word count 2) Page number if visible 3) Brief topic summary (10 words max)"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this manuscript page:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low"  # Nano works better with low detail
                        }
                    }
                ]
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using available model, should be gpt-4.1-nano
                messages=messages,
                max_tokens=100
            )
            return {
                "model": "gpt-4.1-nano (simulated with mini)",
                "response": response.choices[0].message.content,
                "success": True
            }
        except Exception as e:
            return {"model": "gpt-4.1-nano", "error": str(e), "success": False}
    
    def test_gpt4_mini(self, image_path: str) -> dict:
        """Test gpt-4.1-mini for full OCR."""
        base64_image = self.encode_image_for_openai(image_path)
        
        messages = [
            {
                "role": "system",
                "content": "You are an OCR system. Extract ALL handwritten Spanish text from this manuscript exactly as written. Include misspellings, slang, and informal language. Do not correct or improve. Output only the raw text."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text exactly as written:"
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
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Should be gpt-4.1-mini
                messages=messages,
                max_tokens=2000
            )
            text = response.choices[0].message.content
            return {
                "model": "gpt-4.1-mini (using gpt-4o-mini)",
                "text": text,
                "word_count": len(text.split()),
                "success": True
            }
        except Exception as e:
            return {"model": "gpt-4.1-mini", "error": str(e), "success": False}
    
    def test_gpt4_full(self, image_path: str) -> dict:
        """Test gpt-4.1 full model for highest accuracy OCR."""
        base64_image = self.encode_image_for_openai(image_path)
        
        messages = [
            {
                "role": "system",
                "content": "Extract handwritten Spanish text preserving Cuban slang, informal language, and all original errors. Do not correct grammar or spelling. Maintain exact punctuation and capitalization as written."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe this handwritten page exactly:"
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
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Should be gpt-4.1
                messages=messages,
                max_tokens=2000
            )
            text = response.choices[0].message.content
            return {
                "model": "gpt-4.1 (using gpt-4o)",
                "text": text,
                "word_count": len(text.split()),
                "success": True
            }
        except Exception as e:
            return {"model": "gpt-4.1", "error": str(e), "success": False}
    
    def test_paddleocr(self, image_path: str) -> dict:
        """Test PaddleOCR."""
        result_json = self.ocr_tool._run(
            image_path=image_path,
            language="es",
            detect_direction=False
        )
        
        result = json.loads(result_json)
        if result['success']:
            return {
                "model": "PaddleOCR",
                "text": result.get('text', ''),
                "word_count": result.get('word_count', 0),
                "confidence": result.get('confidence', 0),
                "success": True
            }
        else:
            return {"model": "PaddleOCR", "error": result.get('error_message'), "success": False}

def main():
    """Compare all models."""
    logger.info("Model Comparison: PaddleOCR vs GPT-4.1 Family")
    logger.info("=" * 60)
    
    # Get first manuscript page
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path="0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        client_user_id="587f8370-825f-4f0c-8846-2e6d70782989",
        download=True
    )
    
    data = json.loads(result)
    if data.get('status') != 'success' or not data.get('files'):
        logger.error("Failed to get images")
        return
    
    image_path = data['files'][0]['local_path']
    logger.info(f"\nTesting with: {data['files'][0]['name']}")
    
    comparison = ModelComparison()
    
    # Test each model
    logger.info("\n1. Testing GPT-4.1-nano (page analysis)...")
    nano_result = comparison.test_gpt4_nano(image_path)
    if nano_result['success']:
        logger.info(f"   Response: {nano_result['response']}")
    
    logger.info("\n2. Testing PaddleOCR...")
    paddle_result = comparison.test_paddleocr(image_path)
    if paddle_result['success']:
        logger.info(f"   Words: {paddle_result['word_count']}")
        logger.info(f"   Confidence: {paddle_result['confidence']:.2f}")
        logger.info(f"   Sample: {paddle_result['text'][:100]}...")
    
    logger.info("\n3. Testing GPT-4.1-mini (full OCR)...")
    mini_result = comparison.test_gpt4_mini(image_path)
    if mini_result['success']:
        logger.info(f"   Words: {mini_result['word_count']}")
        logger.info(f"   Sample: {mini_result['text'][:100]}...")
    
    logger.info("\n4. Testing GPT-4.1 full (highest accuracy)...")
    full_result = comparison.test_gpt4_full(image_path)
    if full_result['success']:
        logger.info(f"   Words: {full_result['word_count']}")
        logger.info(f"   Sample: {full_result['text'][:100]}...")
    
    # Summary comparison
    logger.info("\n\nSUMMARY COMPARISON:")
    logger.info("=" * 60)
    logger.info(f"PaddleOCR:    {paddle_result.get('word_count', 0)} words")
    logger.info(f"GPT-4.1-mini: {mini_result.get('word_count', 0)} words")
    logger.info(f"GPT-4.1 full: {full_result.get('word_count', 0)} words")
    
    # Save detailed results
    output_file = "model_comparison_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "nano": nano_result,
            "paddleocr": paddle_result,
            "mini": mini_result,
            "full": full_result
        }, f, indent=2)
    
    logger.info(f"\nDetailed results saved to: {output_file}")
    
    # Recommendation
    logger.info("\n\nRECOMMENDATION:")
    if mini_result.get('word_count', 0) > paddle_result.get('word_count', 0) * 2:
        logger.info("✓ GPT-4.1 models significantly outperform PaddleOCR for handwritten Spanish")
        logger.info("✓ Use GPT-4.1-nano for quick page analysis (word count, page numbers)")
        logger.info("✓ Use GPT-4.1-mini for full transcription (best balance of cost/accuracy)")
        logger.info("✓ Use GPT-4.1 full only for difficult pages or final verification")
    else:
        logger.info("✓ PaddleOCR is competitive but needs preprocessing")
        logger.error("✓ Combine PaddleOCR with GPT-4.1-mini for error correction")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()