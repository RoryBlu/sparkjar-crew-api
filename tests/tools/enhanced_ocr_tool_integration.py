#!/usr/bin/env python3
"""Integrate nano chunked OCR into the existing OCR tool."""
import sys
from pathlib import Path

# First, let me add the nano chunked method to the existing OCR tool
def enhance_ocr_tool():
    """Add nano chunked method to existing OCR tool."""
    
    # Read the current OCR tool
    ocr_tool_path = "src/tools/ocr_tool.py"
    
    # The nano chunked method we'll add
    nano_method = '''
    def nano_chunked_ocr(self, image_path: str, chunk_size: int = 50) -> dict:
        """
        Perform OCR using gpt-4.1-nano with chunked reading strategy.
        
        Args:
            image_path: Path to image file
            chunk_size: Number of words to extract per chunk
            
        Returns:
            Dict with transcribed text and metadata
        """
        try:
            import openai
            import base64
            from PIL import Image
            import io
            import re
            
            client = openai.OpenAI()
            
            # Encode image (reuse existing logic)
            base64_image = self._encode_image(image_path, max_size_kb=400)
            
            # Step 1: Get total word count
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
            
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=messages,
                max_tokens=50
            )
            
            result = response.choices[0].message.content
            word_match = re.search(r'(\d+)\s*words?', result, re.IGNORECASE)
            total_words = int(word_match.group(1)) if word_match else 300
            
            # Step 2: Extract text in chunks
            num_chunks = (total_words + chunk_size - 1) // chunk_size
            all_text_chunks = []
            
            for chunk_num in range(num_chunks):
                start_word = chunk_num * chunk_size + 1
                end_word = min((chunk_num + 1) * chunk_size, total_words)
                
                messages = [
                    {
                        "role": "system",
                        "content": f"Extract words {start_word} to {end_word} from this handwritten Spanish manuscript. Return ONLY the words, no commentary or formatting."
                    },
                    {
                        "role": "user",
                        "content": [{
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }]
                    }
                ]
                
                response = client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=messages,
                    max_tokens=chunk_size * 3
                )
                
                chunk_text = response.choices[0].message.content.strip()
                # Remove any commentary/formatting
                chunk_text = re.sub(r'^[^a-zA-ZáéíóúñÁÉÍÓÚÑ]*', '', chunk_text)
                chunk_text = re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s.,;:!?()-]+$', '', chunk_text)
                
                if chunk_text:
                    all_text_chunks.append(chunk_text)
                
                # Stop if we've extracted enough
                total_extracted = len(' '.join(all_text_chunks).split())
                if total_extracted >= total_words * 0.9:
                    break
            
            # Combine chunks
            full_text = ' '.join(all_text_chunks)
            actual_words = len(full_text.split())
            
            return {
                "method": "nano_chunked",
                "text": full_text,
                "word_count": actual_words,
                "target_words": total_words,
                "coverage": actual_words / total_words * 100,
                "chunks_used": len(all_text_chunks),
                "nano_calls": len(all_text_chunks) + 1,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Nano chunked OCR failed: {str(e)}")
            return {
                "method": "nano_chunked",
                "success": False,
                "error": str(e)
            }
'''

    print("Enhanced OCR tool method ready for integration:")
    print("- nano_chunked_ocr() method")
    print("- Cleaner text extraction (no commentary)")
    print("- Word-range based chunking")
    print("- Better error handling")
    
    return nano_method

def create_book_ingestion_crew_structure():
    """Create the book ingestion crew structure."""
    
    crew_structure = {
        "main.py": '''#!/usr/bin/env python3
"""Book Ingestion Crew - Main orchestration."""
from crewai import Agent, Task, Crew
from .tools.ocr_tool import OCRTool
from .tools.google_drive_tool import GoogleDriveTool

class BookIngestionCrew:
    def __init__(self):
        self.ocr_tool = OCRTool()
        self.drive_tool = GoogleDriveTool()
    
    def create_agents(self):
        scanner = Agent(
            role="Document Scanner",
            goal="Discover and organize manuscript pages from Google Drive",
            backstory="Expert at finding and cataloging document images",
            tools=[self.drive_tool],
            verbose=True
        )
        
        ocr_specialist = Agent(
            role="OCR Specialist", 
            goal="Extract text from handwritten manuscripts with high accuracy",
            backstory="Specialist in handwritten Spanish text recognition using advanced OCR techniques",
            tools=[self.ocr_tool],
            verbose=True
        )
        
        quality_reviewer = Agent(
            role="Quality Reviewer",
            goal="Validate and improve transcription quality",
            backstory="Expert in Cuban Spanish and manuscript review",
            verbose=True
        )
        
        return {"scanner": scanner, "ocr": ocr_specialist, "quality": quality_reviewer}
    
    def create_tasks(self, agents, folder_path, client_user_id):
        scan_task = Task(
            description=f"Scan Google Drive folder {folder_path} for manuscript images",
            agent=agents["scanner"],
            expected_output="List of image files with metadata"
        )
        
        ocr_task = Task(
            description="Extract text from each manuscript page using nano chunked OCR",
            agent=agents["ocr"],
            expected_output="Complete transcriptions for all pages",
            context=[scan_task]
        )
        
        quality_task = Task(
            description="Review and improve transcription quality, preserving original language",
            agent=agents["quality"], 
            expected_output="Final reviewed manuscript transcription",
            context=[ocr_task]
        )
        
        return [scan_task, ocr_task, quality_task]
    
    def run_ingestion(self, folder_path: str, client_user_id: str):
        agents = self.create_agents()
        tasks = self.create_tasks(agents, folder_path, client_user_id)
        
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            verbose=True
        )
        
        return crew.kickoff()
''',
        
        "README.md": '''# Book Ingestion Crew

Specialized crew for processing handwritten manuscript books from Google Drive.

## Features
- Google Drive integration for source images
- Advanced OCR using gpt-4.1-nano chunked reading
- Quality review preserving original language
- Structured output with metadata

## Usage
```python
crew = BookIngestionCrew()
result = crew.run_ingestion(
    folder_path="path/to/manuscript/folder",
    client_user_id="client-id"
)
```

## Process
1. **Scanner Agent**: Discovers manuscript pages in Drive folder
2. **OCR Agent**: Extracts text using nano chunked strategy  
3. **Quality Agent**: Reviews and improves transcriptions
4. **Output**: Complete manuscript with metadata
'''
    }
    
    print("\nBook Ingestion Crew structure:")
    for filename, content in crew_structure.items():
        print(f"- {filename}")
    
    return crew_structure

def main():
    """Show integration plan."""
    print("BOOK INGESTION ARCHITECTURE INTEGRATION")
    print("=" * 60)
    
    print("\n1. Enhanced OCR Tool Integration:")
    nano_method = enhance_ocr_tool()
    
    print("\n2. Book Ingestion Crew Structure:")
    crew_structure = create_book_ingestion_crew_structure()
    
    print("\n3. Next Steps:")
    print("   a. Add nano_chunked_ocr() to src/tools/ocr_tool.py")
    print("   b. Create src/crews/book_ingestion_crew/ directory")
    print("   c. Implement crew files")
    print("   d. Test with Castor's manuscripts")
    print("   e. Add API endpoint for crew execution")
    
    print("\n4. Benefits:")
    print("   ✓ Reuses existing tool infrastructure")
    print("   ✓ Follows established crew patterns") 
    print("   ✓ Cost-effective (nano-only strategy)")
    print("   ✓ Handles complete book ingestion workflow")
    
    print(f"\n5. Files to upload exist:")
    print(f"   ✓ castor_nano_chunked_final.txt ({Path('castor_nano_chunked_final.txt').stat().st_size} bytes)")
    print(f"   ✓ Results already uploaded to Google Drive")

if __name__ == "__main__":
    main()