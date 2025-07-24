#!/usr/bin/env python
"""Simple test of crew with proper file paths."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

from crewai import Agent, Task, Crew, Process
from tools.image_viewer_tool import ImageViewerTool
import time

def test_simple_crew():
    """Test simple OCR with crew."""
    
    # Local path from download
    local_path = "/var/folders/gr/zmt7qq_s31q25pyx8tgyghpr0000gp/T/drive_files_004qhiph/baron001 1.png"
    
    print("🚀 Simple Crew OCR Test")
    print("=" * 60)
    print(f"Testing with: {local_path}")
    
    # Create OCR agent
    ocr_agent = Agent(
        role="OCR Specialist",
        goal="Extract Spanish text from handwritten pages",
        backstory="Expert at reading Spanish handwriting",
        tools=[ImageViewerTool()],
        verbose=True
    )
    
    # Create OCR task
    ocr_task = Task(
        description=f"""
        Extract all Spanish text from this manuscript page.
        
        Image path: {local_path}
        
        Use the ImageViewerTool to read the handwritten Spanish text.
        Return the complete transcription.
        """,
        expected_output="Complete Spanish text transcription",
        agent=ocr_agent
    )
    
    # Create crew
    crew = Crew(
        agents=[ocr_agent],
        tasks=[ocr_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute
    print("\n📝 Running OCR...")
    start_time = time.time()
    
    try:
        result = crew.kickoff()
        elapsed = time.time() - start_time
        
        print("\n✅ OCR Complete!")
        print(f"Time: {elapsed:.1f} seconds")
        print("\nResult:")
        print("-" * 60)
        if hasattr(result, 'raw'):
            print(result.raw[:500] + "..." if len(result.raw) > 500 else result.raw)
        else:
            result_str = str(result)
            print(result_str[:500] + "..." if len(result_str) > 500 else result_str)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_crew()