#!/usr/bin/env python
"""Test book ingestion with CrewAI agents."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

from crewai import Agent, Task, Crew, Process
from sparkjar_shared.tools.google_drive_tool import GoogleDriveTool
from sparkjar_shared.tools.image_viewer_tool import ImageViewerTool
from sparkjar_shared.tools.simple_db_storage_tool import SimpleDBStorageTool
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_crew_agents():
    """Test book ingestion with CrewAI agents."""
    client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"
    folder_id = "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"
    
    print("🚀 Testing Book Ingestion with CrewAI Agents")
    print("=" * 60)
    
    # Create agents
    file_manager = Agent(
        role="File Manager",
        goal="List and manage files from Google Drive",
        backstory="Expert at navigating Google Drive and organizing files",
        tools=[GoogleDriveTool()],
        verbose=True
    )
    
    ocr_specialist = Agent(
        role="OCR Specialist",
        goal="Extract Spanish text from manuscript pages using advanced OCR",
        backstory="Specialist in reading handwritten Spanish text with high accuracy",
        tools=[ImageViewerTool()],
        verbose=True,
        max_iter=3
    )
    
    storage_specialist = Agent(
        role="Storage Specialist",
        goal="Store transcribed pages in the database efficiently",
        backstory="Database expert ensuring all pages are properly stored",
        tools=[SimpleDBStorageTool()],
        verbose=True
    )
    
    # Create tasks
    list_files_task = Task(
        description=f"""
        List all PNG files from Google Drive folder.
        
        Use GoogleDriveTool with:
        - folder_path: {folder_id}
        - client_user_id: {client_user_id}
        
        Return a JSON list of files with their names and local paths.
        """,
        expected_output="JSON list of files",
        agent=file_manager
    )
    
    # Create crew for listing files
    list_crew = Crew(
        agents=[file_manager],
        tasks=[list_files_task],
        process=Process.sequential,
        verbose=True
    )
    
    print("\n📁 Step 1: Listing files...")
    list_result = list_crew.kickoff()
    
    # Parse files
    try:
        if hasattr(list_result, 'raw'):
            files_data = json.loads(list_result.raw)
        else:
            files_data = json.loads(str(list_result))
        
        if isinstance(files_data, dict) and 'files' in files_data:
            files = files_data['files']
        else:
            files = files_data
            
        png_files = [f for f in files if f.get('name', '').endswith('.png')][:5]
        print(f"Found {len(png_files)} PNG files, processing first 5")
    except:
        print("Failed to parse files list")
        return
    
    # Process each file
    print("\n📄 Step 2: Processing pages...")
    start_time = time.time()
    successful = 0
    
    for i, file_info in enumerate(png_files):
        print(f"\n[{i+1}/5] Processing: {file_info['name']}")
        
        # OCR task
        ocr_task = Task(
            description=f"""
            Extract Spanish text from this manuscript page.
            
            Image path: {file_info['local_path']}
            
            Use ImageViewerTool to read the handwritten Spanish text.
            Return the complete transcription.
            """,
            expected_output="Complete Spanish text transcription",
            agent=ocr_specialist
        )
        
        # Storage task
        storage_task = Task(
            description=f"""
            Store the transcribed page in the database.
            
            Use SimpleDBStorageTool with this JSON:
            {{
                "client_user_id": "{client_user_id}",
                "book_key": "{folder_id}",
                "page_number": {i + 1},
                "file_name": "{file_info['name']}",
                "language_code": "es",
                "page_text": "<use the transcription from previous task>",
                "ocr_metadata": {{
                    "confidence": 0.95,
                    "file_id": "{file_info.get('file_id', '')}"
                }}
            }}
            """,
            expected_output="Confirmation of successful storage",
            agent=storage_specialist,
            context=[ocr_task]
        )
        
        # Create processing crew
        process_crew = Crew(
            agents=[ocr_specialist, storage_specialist],
            tasks=[ocr_task, storage_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = process_crew.kickoff()
            if "success" in str(result).lower():
                successful += 1
                print(f"✅ Page {i+1} processed successfully")
            else:
                print(f"❌ Page {i+1} failed")
        except Exception as e:
            print(f"❌ Error processing page {i+1}: {e}")
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total pages: 5")
    print(f"Successful: {successful}")
    print(f"Failed: {5 - successful}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Rate: {successful/elapsed:.2f} pages/sec")

if __name__ == "__main__":
    test_crew_agents()