"""Individual Page Processing Book Ingestion Crew - uses kickoff_for_each"""
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
from sparkjar_shared.tools.memory.sj_sequential_thinking_tool import SJSequentialThinkingTool
from sparkjar_shared.tools.memory.sj_memory_tool import SJMemoryTool

# Import our utility functions
from utils import parse_baron_filename, sort_book_files

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent / "config"

def _load_yaml(file_name: str):
    """Load YAML configuration."""
    path = CONFIG_DIR / file_name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_page_processing_crew(client_user_id: str) -> Crew:
    """Build a crew specifically for processing individual pages."""
    agents_cfg = _load_yaml("agents_enhanced.yaml")
    
    # Initialize tools
    image_viewer = ImageViewerTool()
    thinking_tool = SJSequentialThinkingTool()
    memory_tool = SJMemoryTool()
    
    # Create agents for page processing
    vision_agent = Agent(**agents_cfg["vision_specialist"])
    vision_agent.tools = [image_viewer]
    
    reasoning_agent = Agent(**agents_cfg["reasoning_specialist"])
    reasoning_agent.tools = [thinking_tool, image_viewer]
    
    data_agent = Agent(**agents_cfg["data_specialist"])
    data_agent.tools = [memory_tool]
    
    # Create tasks for single page processing
    ocr_task = Task(
        description="""
        Process the book page from file: {file_name}
        
        Use ImageViewerTool to:
        1. Load the image from Google Drive using file_id: {file_id}
        2. Perform OCR with language: {language}
        3. If confidence is below {confidence_threshold}, apply multi-pass OCR
        
        Return JSON with:
        - transcription: full text content
        - confidence: overall confidence score
        - metadata: handwriting style, page condition
        """,
        expected_output="""
        JSON object with complete transcription and metadata
        """,
        agent=vision_agent
    )
    
    refine_task = Task(
        description="""
        Review the OCR results and refine if confidence is below {confidence_threshold}.
        
        Use SJSequentialThinkingTool to analyze unclear sections.
        Consider the Spanish handwriting context.
        
        Only execute if initial confidence is low.
        """,
        expected_output="""
        Refined transcription with improved confidence
        """,
        agent=reasoning_agent,
        context=[ocr_task]
    )
    
    store_task = Task(
        description="""
        Store the transcribed page to database using SJMemoryTool.
        
        Create entity: "{book_title}_page_{calculated_page_number}"
        Store transcription as observation with metadata:
        - page_number: {calculated_page_number}
        - file_name: {file_name}
        - confidence: from OCR results
        - processing_date: current date
        
        Use client_user_id: {client_user_id}
        """,
        expected_output="""
        Confirmation of successful storage with entity ID
        """,
        agent=data_agent,
        context=[refine_task]
    )
    
    # Create crew for page processing
    crew = Crew(
        agents=[vision_agent, reasoning_agent, data_agent],
        tasks=[ocr_task, refine_task, store_task],
        process=Process.sequential,
        verbose=True,
        memory=False
    )
    
    return crew

def build_file_listing_crew(client_user_id: str) -> Crew:
    """Build a crew just for listing files."""
    agents_cfg = _load_yaml("agents_enhanced.yaml")
    
    # Initialize Google Drive tool
    google_drive = GoogleDriveTool()
    
    # Create file manager agent
    file_manager = Agent(**agents_cfg["file_manager"])
    file_manager.tools = [google_drive]
    
    # Create file listing task
    list_task = Task(
        description="""
        List all image files from Google Drive folder: {google_drive_folder_path}
        Use client_user_id: {client_user_id} for credentials.
        
        Return a JSON array with file information including:
        - file_name
        - file_id
        - mime_type
        """,
        expected_output="""
        JSON array of file objects with name, id, and mime type
        """,
        agent=file_manager
    )
    
    # Create crew for file listing
    crew = Crew(
        agents=[file_manager],
        tasks=[list_task],
        process=Process.sequential,
        verbose=True,
        memory=False
    )
    
    return crew

def kickoff(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute book ingestion using kickoff_for_each for individual page processing.
    
    This approach:
    1. Lists all files using one crew
    2. Processes each file individually using kickoff_for_each
    """
    logger.info("Starting individual page processing book ingestion")
    
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    # Step 1: List files
    logger.info("Step 1: Listing files from Google Drive")
    listing_crew = build_file_listing_crew(client_user_id)
    listing_result = listing_crew.kickoff(inputs)
    
    # Parse listing result
    if hasattr(listing_result, 'raw'):
        listing_result = listing_result.raw
    
    # Extract file list
    if isinstance(listing_result, str):
        try:
            files = json.loads(listing_result)
        except:
            # Try to extract from markdown
            import re
            json_match = re.search(r'```\s*\[(.+?)\]\s*```', listing_result, re.DOTALL)
            if json_match:
                files = json.loads('[' + json_match.group(1) + ']')
            else:
                logger.error("Could not parse file listing")
                return {"error": "Failed to parse file listing"}
    elif isinstance(listing_result, list):
        files = listing_result
    else:
        files = listing_result.get('files', []) if isinstance(listing_result, dict) else []
    
    logger.info(f"Found {len(files)} files to process")
    
    # Step 2: Sort files and prepare inputs for each page
    sorted_files = sort_book_files(files)
    
    # Prepare input list for kickoff_for_each
    page_inputs = []
    book_metadata = inputs.get("book_metadata", {})
    
    for file_info in sorted_files:
        page_input = {
            "client_user_id": client_user_id,
            "file_name": file_info["file_name"],
            "file_id": file_info["file_id"],
            "calculated_page_number": file_info["calculated_page_number"],
            "mime_type": file_info.get("mime_type", "image/png"),
            "language": inputs.get("language", "es"),
            "confidence_threshold": inputs.get("confidence_threshold", 0.85),
            "book_title": book_metadata.get("title", "Unknown Title"),
            "book_author": book_metadata.get("author", "Unknown Author"),
            "book_year": book_metadata.get("year", "Unknown"),
            "book_description": book_metadata.get("description", "")
        }
        page_inputs.append(page_input)
    
    # Step 3: Process each page individually using kickoff_for_each
    logger.info(f"Step 2: Processing {len(page_inputs)} pages individually")
    processing_crew = build_page_processing_crew(client_user_id)
    
    # Process all pages - CrewAI will handle each one individually
    results = processing_crew.kickoff_for_each(inputs=page_inputs)
    
    # Step 4: Compile results
    successful = []
    failed = []
    
    for i, result in enumerate(results):
        page_num = page_inputs[i]["calculated_page_number"]
        file_name = page_inputs[i]["file_name"]
        
        if hasattr(result, 'raw'):
            result = result.raw
        
        if isinstance(result, str) and "error" not in result.lower():
            successful.append({
                "page_number": page_num,
                "file_name": file_name,
                "status": "success"
            })
        else:
            failed.append({
                "page_number": page_num,
                "file_name": file_name,
                "status": "failed",
                "error": str(result)
            })
    
    # Create summary
    summary = {
        "total_pages": len(page_inputs),
        "processed_successfully": len(successful),
        "failed": len(failed),
        "successful_pages": successful,
        "failed_pages": failed,
        "method": "kickoff_for_each"
    }
    
    logger.info(f"Completed processing. Success: {len(successful)}, Failed: {len(failed)}")
    
    return summary