#!/usr/bin/env python3
"""Final comparison of PaddleOCR vs OpenAI transcription."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import openai
import base64
from PIL import Image
import io
import json

# The actual OCR results from PaddleOCR
PADDLEOCR_RESULTS = {
    "page1": "gue estabamonostror todaviane faltaga algo por hacer arte farse for teefong no le puse ateueisn a lgs habeo solamed wondoter Como a la medis hsra me yolioa llanar Enseguiola fue llgue'al chopin reconsci al 40 labarianosplersonalmeute, @sinino. mismi,",
    
    "page2": "salude dardole las bueras terde y lo blamepor ru apodo,ense qida me dijocViene forlo earorsi pue mi reyfueto me dijo mg+oto dejiranoi lor caro cou la riercaneia le dejarian las halia poraso e nasau con ep bote gue oe habiu robaoo lot a dejr locarsspargueado sin panrle el aeguro a los puerto, dolos Cosas 480",
    
    "page3": "de irse le pedi de faor gue degora lor exos eomo estalan forgue lor caror fara hecharle la mereancio.dentro de dst horss toda 483 Manueltambieu estbo obgervando derdlef oto laso de la calle y.lolrer mi dinere. A"
}

def transcribe_with_openai(image_path, paddle_ocr_text, page_num):
    """Get OpenAI's transcription and compare."""
    client = openai.OpenAI()
    
    # Load image
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
            "content": "You are an expert at transcribing handwritten Spanish manuscripts."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Page {page_num} - PaddleOCR captured this text:
"{paddle_ocr_text}"

Words captured: {len(paddle_ocr_text.split())}
Characters captured: {len(paddle_ocr_text)}

Please provide:
1. Your complete transcription of the handwritten page
2. What percentage of the page did PaddleOCR capture?
3. Analysis of what PaddleOCR got right vs wrong
4. The story/content being told

Be thorough in your transcription."""
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
    """Final comparison."""
    from .tools.google_drive_tool import GoogleDriveTool
    
    print("FINAL OCR COMPARISON - PaddleOCR vs OpenAI")
    print("=" * 60)
    
    # Show what PaddleOCR captured
    print("\nPaddleOCR Results Summary:")
    for page, text in PADDLEOCR_RESULTS.items():
        print(f"\n{page}: {len(text.split())} words, {len(text)} characters")
        print(f"Preview: {text[:80]}...")
    
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
    files = data.get('files', [])
    
    # Process each page
    print("\n\nDetailed Analysis:")
    print("=" * 60)
    
    full_transcriptions = []
    
    for i, file in enumerate(files):
        page_key = f"page{i+1}"
        paddle_text = PADDLEOCR_RESULTS.get(page_key, "")
        
        print(f"\n\nAnalyzing Page {i+1}...")
        
        image_path = file.get('local_path')
        if image_path:
            analysis = transcribe_with_openai(image_path, paddle_text, i+1)
            
            full_transcriptions.append({
                'page': i+1,
                'paddle_ocr': paddle_text,
                'analysis': analysis
            })
            
            # Save individual analysis
            with open(f"page{i+1}_analysis.txt", "w", encoding="utf-8") as f:
                f.write(f"PAGE {i+1} ANALYSIS\n")
                f.write("=" * 50 + "\n\n")
                f.write("PADDLEOCR RESULT:\n")
                f.write(paddle_text + "\n\n")
                f.write("OPENAI ANALYSIS:\n")
                f.write(analysis)
    
    # Create final proper transcription
    output_file = "castor_final_transcription.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("CASTOR GONZALEZ - BOOK 1 - FINAL TRANSCRIPTION\n")
        f.write("=" * 60 + "\n")
        f.write("Comparison of PaddleOCR vs OpenAI GPT-4 Vision\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("SUMMARY:\n")
        total_paddle_words = sum(len(PADDLEOCR_RESULTS[f"page{i+1}"].split()) for i in range(3))
        f.write(f"- PaddleOCR captured: {total_paddle_words} total words across 3 pages\n")
        f.write("- Analysis shows PaddleOCR captured fragments but with many errors\n")
        f.write("- Below is the complete transcription from OpenAI\n\n")
        
        for result in full_transcriptions:
            f.write(f"\n{'='*50}\n")
            f.write(f"PAGE {result['page']}\n")
            f.write(f"{'='*50}\n\n")
            f.write(result['analysis'])
            f.write("\n\n")
    
    print(f"\n\n✅ Analysis complete!")
    print(f"Final transcription saved to: {output_file}")
    print(f"Individual page analyses saved to: page1_analysis.txt, page2_analysis.txt, page3_analysis.txt")
    
    # Show summary
    print("\n\nSUMMARY:")
    print(f"PaddleOCR total words captured: {total_paddle_words}")
    print("PaddleOCR captured partial text with significant errors")
    print("OpenAI provided complete transcriptions")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()