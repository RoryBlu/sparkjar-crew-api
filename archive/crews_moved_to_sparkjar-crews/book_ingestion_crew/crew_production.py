"""Production Book Ingestion Crew - processes pages individually with proper logging"""
from pathlib import Path
import yaml
from crewai import Agent, Crew, Process, Task
import logging
from typing import Dict, Any, List
import json
import time

# Import needed tools
from tools.google_drive_tool import GoogleDriveTool
from tools.image_viewer_tool import ImageViewerTool
from tools.simple_db_storage_tool import SimpleDBStorageTool

# Import utility functions
from .utils import parse_baron_filename, sort_book_files

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent / "config"

def _load_yaml(file_name: str):
    """Load YAML configuration."""
    path = CONFIG_DIR / file_name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_production_crew(client_user_id: str) -> Crew:
    """Build production crew for page processing."""
    
    # Create OCR agent with GPT-4o for vision
    ocr_agent = Agent(
        role="OCR Specialist",
        goal="Extract Spanish text from handwritten pages with maximum accuracy",
        backstory="Expert in reading Spanish handwritten manuscripts using advanced OCR",
        tools=[ImageViewerTool()],
        verbose=True,
        model="gpt-4o"  # Use GPT-4o for vision tasks
    )
    
    # Create storage agent
    storage_agent = Agent(
        role="Data Storage Specialist", 
        goal="Store transcribed pages reliably in database",
        backstory="Database expert ensuring proper data storage and integrity",
        tools=[SimpleDBStorageTool()],
        verbose=True,
        model="gpt-4o-mini"  # Use mini for storage tasks
    )
    
    # Create tasks for page processing
    ocr_task = Task(
        description="""
        Extract Spanish text from page {page_number}: {file_name}
        
        Use ImageViewerTool with local_path: {local_path}
        Apply multi-pass OCR if needed for handwritten Spanish text.
        
        Return the complete transcribed text.
        """,
        expected_output="Complete Spanish text transcription",
        agent=ocr_agent
    )
    
    storage_task = Task(
        description="""
        Store the transcribed page in database.
        
        Use SimpleDBStorageTool with these exact parameters as JSON:
        {{
            "client_user_id": "{client_user_id}",
            "book_key": "{book_key}",
            "page_number": {page_number},
            "file_name": "{file_name}",
            "language_code": "{language_code}",
            "page_text": "<transcribed text from previous task>",
            "ocr_metadata": {{
                "confidence": 0.95,
                "processing_time": 0,
                "file_id": "{file_id}"
            }}
        }}
        
        Replace <transcribed text from previous task> with actual text.
        """,
        expected_output="Confirmation of successful storage",
        agent=storage_agent,
        context=[ocr_task]
    )
    
    # Create crew
    crew = Crew(
        agents=[ocr_agent, storage_agent],
        tasks=[ocr_task, storage_task],
        process=Process.sequential,
        verbose=True,
        memory=False  # Disable CrewAI memory
    )
    
    return crew

def get_files_from_drive(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get files from Google Drive."""
    drive_tool = GoogleDriveTool()
    result = drive_tool._run(
        folder_path=inputs["google_drive_folder_path"],
        client_user_id=inputs["client_user_id"]
    )
    
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            logger.error(f"Failed to parse drive result: {result}")
            return []
    
    if isinstance(result, dict) and result.get("status") == "success":
        files = result.get("files", [])
        # Filter for PNG files
        png_files = [f for f in files if f.get('name', '').endswith('.png')]
        return png_files
    else:
        logger.error(f"Failed to list files: {result}")
        return []

def kickoff(inputs: Dict[str, Any], simple_logger=None) -> Dict[str, Any]:
    """
    Execute production book ingestion crew.
    
    This processes pages individually using kickoff_for_each.
    All agent output is captured in crew_job_event table.
    """
    start_time = time.time()
    
    if simple_logger:
        simple_logger.log({
            "event_type": "crew_start",
            "message": "Starting production book ingestion crew",
            "timestamp": time.time()
        })
    
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    # Get process limit if specified
    process_limit = inputs.get("process_pages_limit")
    
    # Step 1: Get files from Google Drive
    logger.info("Fetching files from Google Drive...")
    if simple_logger:
        simple_logger.log({
            "event_type": "task_start",
            "task": "fetch_files",
            "message": "Fetching files from Google Drive"
        })
    
    files = get_files_from_drive(inputs)
    logger.info(f"Found {len(files)} PNG files")
    
    if not files:
        return {
            "status": "error",
            "error": "No PNG files found in folder",
            "total_pages": 0
        }
    
    # Step 2: Sort files by page number
    sorted_files = sort_book_files(files)
    
    # Apply limit if specified
    if process_limit:
        sorted_files = sorted_files[:process_limit]
        logger.info(f"Limited to processing {process_limit} pages")
    
    # Step 3: Build crew
    crew = build_production_crew(client_user_id)
    
    # Step 4: Prepare inputs for each page
    page_inputs = []
    book_key = inputs.get("google_drive_folder_path")
    language_code = inputs.get("language", "es")
    
    for file_info in sorted_files:
        local_path = file_info.get("local_path")
        if not local_path:
            logger.warning(f"No local_path for {file_info['file_name']}, skipping")
            continue
        
        page_input = {
            "client_user_id": client_user_id,
            "book_key": book_key,
            "page_number": file_info["calculated_page_number"],
            "file_name": file_info["file_name"],
            "file_id": file_info["file_id"],
            "local_path": local_path,
            "language_code": language_code
        }
        page_inputs.append(page_input)
    
    logger.info(f"Processing {len(page_inputs)} pages with kickoff_for_each")
    
    if simple_logger:
        simple_logger.log({
            "event_type": "task_start", 
            "task": "process_pages",
            "message": f"Processing {len(page_inputs)} pages individually",
            "page_count": len(page_inputs)
        })
    
    # Step 5: Process pages individually
    # CrewAI will log all agent interactions automatically
    results = crew.kickoff_for_each(inputs=page_inputs)
    
    # Step 6: Compile results
    successful = []
    failed = []
    
    for i, result in enumerate(results):
        page_info = page_inputs[i]
        
        if hasattr(result, 'raw'):
            result_str = result.raw
        else:
            result_str = str(result)
        
        # Check if storage was successful
        if "success" in result_str.lower() and "error" not in result_str.lower():
            successful.append({
                "page_number": page_info["page_number"],
                "file_name": page_info["file_name"]
            })
        else:
            failed.append({
                "page_number": page_info["page_number"],
                "file_name": page_info["file_name"],
                "error": result_str[:200]  # First 200 chars of error
            })
    
    elapsed_time = time.time() - start_time
    
    # Create summary
    summary = {
        "status": "completed",
        "total_pages": len(page_inputs),
        "processed_successfully": len(successful), 
        "failed": len(failed),
        "processing_time": f"{elapsed_time:.1f}s",
        "average_time_per_page": f"{elapsed_time/len(page_inputs):.1f}s" if page_inputs else "0s",
        "successful_pages": successful,
        "failed_pages": failed
    }
    
    logger.info(f"Completed processing. Success: {len(successful)}, Failed: {len(failed)}")
    
    if simple_logger:
        simple_logger.log({
            "event_type": "crew_complete",
            "message": f"Completed processing {len(page_inputs)} pages",
            "successful": len(successful),
            "failed": len(failed),
            "elapsed_time": elapsed_time
        })
    
    return summary