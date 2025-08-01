"""Simple Individual Page Processing - minimal crew for testing"""
from pathlib import Path
import yaml
from crewai import Agent, Crew, Process, Task
import logging
from typing import Dict, Any, List
import json

# Import needed tools with proper paths
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sparkjar_shared.tools.google_drive_tool import GoogleDriveTool
from sparkjar_shared.tools.image_viewer_tool import ImageViewerTool
from sparkjar_shared.tools.simple_db_storage_tool import SimpleDBStorageTool

# Import our utility functions
from utils import parse_baron_filename, sort_book_files

logger = logging.getLogger(__name__)

def build_simple_crew() -> Crew:
    """Build a minimal crew for OCR and storage."""
    
    # Create simple vision agent
    vision_agent = Agent(
        role="OCR Specialist",
        goal="Extract text from book pages using OCR",
        backstory="Expert at reading handwritten Spanish text",
        tools=[ImageViewerTool()],
        verbose=True
    )
    
    # Create storage agent
    storage_agent = Agent(
        role="Data Storage Specialist",
        goal="Store transcribed pages in database",
        backstory="Expert at managing book data storage",
        tools=[SimpleDBStorageTool()],
        verbose=True
    )
    
    # Create simple OCR task
    ocr_task = Task(
        description="""
        Process book page: {file_name}
        
        1. Use ImageViewerTool with image path: {local_path}
        2. Extract Spanish text from the image
        3. Return the complete transcription in JSON format:
        {{
            "transcription": "<full text>",
            "confidence": <confidence score>
        }}
        
        The image is already downloaded locally at: {local_path}
        """,
        expected_output="JSON with transcription and confidence score",
        agent=vision_agent
    )
    
    # Create storage task
    storage_task = Task(
        description="""
        Store the transcribed page in the database.
        
        Use simple_db_storage tool with these exact parameters in JSON format:
        {{
            "client_user_id": "{client_user_id}",
            "book_key": "{book_key}",
            "page_number": {calculated_page_number},
            "file_name": "{file_name}",
            "language_code": "{language_code}",
            "page_text": "<take the transcription text from the previous task>",
            "ocr_metadata": {{
                "confidence": <take the confidence score from the previous task>,
                "processing_date": "<today's date>"
            }}
        }}
        
        Pass the entire JSON as a single string to the tool.
        """,
        expected_output="Confirmation that page was stored with page_id",
        agent=storage_agent,
        context=[ocr_task]
    )
    
    # Create minimal crew
    crew = Crew(
        agents=[vision_agent, storage_agent],
        tasks=[ocr_task, storage_task],
        process=Process.sequential,
        verbose=True
    )
    
    return crew

def list_files(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List files from Google Drive."""
    logger.info("Listing files from Google Drive")
    
    # Create Google Drive tool
    google_drive = GoogleDriveTool()
    
    # Get file list
    result = google_drive._run(
        folder_path=inputs["google_drive_folder_path"],
        client_user_id=inputs["client_user_id"]
    )
    
    # Parse result - it might be a string or dict
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            logger.error(f"Failed to parse result: {result}")
            return []
    
    if isinstance(result, dict) and result.get("status") == "success":
        files = result.get("files", [])
        logger.info(f"Files structure: {files[0] if files else 'No files'}")
        return files
    else:
        logger.error(f"Failed to list files: {result}")
        return []

def kickoff(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute simple page-by-page processing."""
    logger.info("Starting simple individual page processing")
    
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    # Step 1: List files directly
    files = list_files(inputs)
    logger.info(f"Found {len(files)} files")
    
    if not files:
        return {"error": "No files found"}
    
    # Step 2: Sort files
    sorted_files = sort_book_files(files)
    
    # Step 3: Build crew for processing
    crew = build_simple_crew()
    
    # Step 4: Process first 1 page as a test
    test_pages = sorted_files[:1]
    page_inputs = []
    
    # Extract book_key from folder path
    book_key = inputs.get("google_drive_folder_path", "unknown_book")
    language_code = inputs.get("language", "es")
    
    for file_info in test_pages:
        # Use local_path for the image viewer tool
        local_path = file_info.get("local_path")
        if not local_path:
            logger.error(f"No local_path for {file_info['file_name']}")
            continue
            
        page_input = {
            "file_name": file_info["file_name"],
            "file_id": file_info["file_id"],
            "local_path": local_path,
            "calculated_page_number": file_info["calculated_page_number"],
            "client_user_id": client_user_id,
            "book_key": book_key,
            "language_code": language_code
        }
        page_inputs.append(page_input)
    
    logger.info(f"Processing {len(page_inputs)} pages with kickoff_for_each")
    
    # Process pages individually
    results = crew.kickoff_for_each(inputs=page_inputs)
    
    # Compile results
    successful = 0
    for i, result in enumerate(results):
        if hasattr(result, 'raw'):
            result = result.raw
        logger.info(f"Page {i+1} result: {result[:200]}...")
        if result and len(str(result)) > 50:
            successful += 1
    
    return {
        "total_files": len(files),
        "processed": len(test_pages),
        "successful": successful,
        "method": "simple_kickoff_for_each"
    }