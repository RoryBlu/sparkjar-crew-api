"""File-based Book Ingestion Crew - processes files from list instead of page numbers"""
from pathlib import Path
import yaml
from crewai import Agent, Crew, Process, Task
import logging
from typing import Dict, Any, List
import json

# Import needed tools
from tools.google_drive_tool import GoogleDriveTool
from tools.image_viewer_tool import ImageViewerTool
from tools.sj_sequential_thinking_tool import SJSequentialThinkingTool
from tools.sj_memory_tool import SJMemoryTool

# Import our utility functions
from utils import parse_baron_filename, sort_book_files

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent / "config"

def _load_yaml(file_name: str):
    """Load YAML configuration."""
    path = CONFIG_DIR / file_name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_crew(client_user_id: str) -> Crew:
    """Build the crew from YAML configs."""
    agents_cfg = _load_yaml("agents_enhanced.yaml")
    tasks_cfg = _load_yaml("tasks_file_based.yaml")  # Use new task config
    
    # Initialize tools
    google_drive = GoogleDriveTool()
    image_viewer = ImageViewerTool()
    thinking_tool = SJSequentialThinkingTool()
    memory_tool = SJMemoryTool()
    
    # Create agents
    agents = {}
    for name, params in agents_cfg.items():
        # Assign tools based on agent role
        if name == "file_manager":
            params["tools"] = [google_drive]
        elif name == "vision_specialist":
            params["tools"] = [image_viewer, thinking_tool]
        elif name == "reasoning_specialist":
            params["tools"] = [thinking_tool, image_viewer]
        elif name == "data_specialist":
            params["tools"] = [memory_tool]
        elif name == "project_manager":
            params["tools"] = []
        
        # Create agent
        agents[name] = Agent(**params)
    
    # Create tasks - only the initial listing task
    # We'll create page-specific tasks dynamically
    list_task_cfg = tasks_cfg["list_book_files"].copy()
    agent_name = list_task_cfg.pop("agent")
    list_task = Task(
        **list_task_cfg,
        agent=agents[agent_name]
    )
    
    # Create crew with just the listing task initially
    crew = Crew(
        agents=list(agents.values()),
        tasks=[list_task],
        process=Process.sequential,
        verbose=True,
        memory=False  # Disable memory for now
    )
    
    # Store configs and agents for later use
    crew._agents_dict = agents
    crew._tasks_cfg = tasks_cfg
    crew._memory_tool = memory_tool
    
    return crew

def process_single_file(crew: Crew, file_info: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single file through the OCR pipeline."""
    logger.info(f"Processing file: {file_info['file_name']} (page {file_info['calculated_page_number']})")
    
    # Get agents and task configs
    agents = crew._agents_dict
    tasks_cfg = crew._tasks_cfg
    
    # Prepare file-specific inputs
    file_inputs = {
        **inputs,  # Include all original inputs
        "file_name": file_info["file_name"],
        "file_id": file_info["file_id"],
        "calculated_page_number": file_info["calculated_page_number"],
        "mime_type": file_info.get("mime_type", "image/png")
    }
    
    # Add book metadata with defaults
    book_metadata = inputs.get("book_metadata", {})
    file_inputs.update({
        "book_title": book_metadata.get("title", "Unknown Title"),
        "book_author": book_metadata.get("author", "Unknown Author"),
        "book_description": book_metadata.get("description", "No description"),
        "book_year": book_metadata.get("year", "Unknown")
    })
    
    # Create page processing task
    process_task_cfg = tasks_cfg["process_book_page"].copy()
    agent_name = process_task_cfg.pop("agent")
    process_task = Task(
        **process_task_cfg,
        agent=agents[agent_name]
    )
    
    # Execute OCR task
    ocr_result = process_task.execute(context=file_inputs)
    
    # Parse OCR result
    if isinstance(ocr_result, str):
        try:
            ocr_data = json.loads(ocr_result)
        except:
            ocr_data = {"transcription": ocr_result, "overall_confidence": 0.5}
    else:
        ocr_data = ocr_result
    
    # Check if refinement is needed
    confidence_threshold = inputs.get("confidence_threshold", 0.85)
    if ocr_data.get("overall_confidence", 1.0) < confidence_threshold:
        logger.info(f"Confidence {ocr_data.get('overall_confidence')} below threshold, refining...")
        
        # Add OCR results to context
        file_inputs["initial_transcription"] = ocr_data.get("transcription", "")
        file_inputs["unclear_sections"] = ocr_data.get("unclear_sections", [])
        
        # Create refinement task
        refine_task_cfg = tasks_cfg["refine_transcription"].copy()
        agent_name = refine_task_cfg.pop("agent")
        refine_task = Task(
            **refine_task_cfg,
            agent=agents[agent_name]
        )
        
        # Execute refinement
        refined_result = refine_task.execute(context=file_inputs)
        
        # Update OCR data with refined results
        if isinstance(refined_result, str):
            try:
                ocr_data = json.loads(refined_result)
            except:
                pass
        else:
            ocr_data = refined_result
    
    # Store results in database
    storage_inputs = {
        **file_inputs,
        "page_text": ocr_data.get("transcription", ""),
        "ocr_metadata": {
            "initial_confidence": ocr_data.get("overall_confidence", 0),
            "final_confidence": ocr_data.get("overall_confidence", 0),
            "passes_used": 2 if ocr_data.get("overall_confidence", 1.0) < confidence_threshold else 1,
            "unclear_sections": len(ocr_data.get("unclear_sections", [])),
            "handwriting_style": ocr_data.get("metadata", {}).get("handwriting_style", "unknown"),
            "page_condition": ocr_data.get("metadata", {}).get("page_condition", "unknown")
        }
    }
    
    # Create storage task
    storage_task_cfg = tasks_cfg["store_page_results"].copy()
    agent_name = storage_task_cfg.pop("agent")
    storage_task = Task(
        **storage_task_cfg,
        agent=agents[agent_name]
    )
    
    # Execute storage
    storage_result = storage_task.execute(context=storage_inputs)
    
    return {
        "page_number": file_info["calculated_page_number"],
        "file_name": file_info["file_name"],
        "transcription_length": len(ocr_data.get("transcription", "")),
        "confidence": ocr_data.get("overall_confidence", 0),
        "storage_result": storage_result
    }

def kickoff(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the book ingestion crew with file-based processing.
    
    This version lists all files first, then processes each one individually.
    """
    logger.info("Starting file-based book ingestion crew")
    
    # Get client_user_id
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    # Build crew
    crew = build_crew(client_user_id)
    
    # Execute the file listing task
    logger.info("Listing files from Google Drive...")
    listing_result = crew.kickoff(inputs)
    
    # Parse the listing result
    logger.info(f"Listing result type: {type(listing_result)}")
    
    # Handle CrewOutput object
    if hasattr(listing_result, 'raw'):
        # It's a CrewOutput, get the raw result
        raw_output = listing_result.raw
        logger.info(f"Raw output from crew: {type(raw_output)}")
        listing_result = raw_output
    
    if isinstance(listing_result, str):
        try:
            # Try to parse as JSON array (crew's Final Answer)
            files = json.loads(listing_result)
            logger.info(f"Parsed {len(files)} files from JSON")
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```\s*\[(.+?)\]\s*```', listing_result, re.DOTALL)
            if json_match:
                try:
                    files = json.loads('[' + json_match.group(1) + ']')
                    logger.info(f"Extracted {len(files)} files from markdown")
                except:
                    logger.error(f"Could not parse extracted JSON")
                    files = []
            else:
                logger.error(f"Could not parse listing result as JSON")
                files = []
    elif isinstance(listing_result, list):
        files = listing_result
    elif isinstance(listing_result, dict):
        # If it's a dict with 'files' key
        files = listing_result.get('files', [])
    else:
        logger.error(f"Unexpected listing result type: {type(listing_result)}")
        files = []
    
    # Check if files already have calculated_page_number (from agent)
    if files and 'calculated_page_number' in files[0]:
        # Agent already calculated page numbers, just sort by them
        sorted_files = sorted(files, key=lambda x: x['calculated_page_number'])
        logger.info(f"Using agent-calculated page numbers for {len(sorted_files)} files")
    else:
        # Use our parser to calculate page numbers
        sorted_files = sort_book_files(files)
        logger.info(f"Calculated page numbers for {len(sorted_files)} files")
    
    # Process each file
    results = []
    for i, file_info in enumerate(sorted_files):
        logger.info(f"Processing file {i+1}/{len(sorted_files)}: {file_info['file_name']}")
        
        try:
            result = process_single_file(crew, file_info, inputs)
            results.append(result)
            logger.info(f"Successfully processed page {result['page_number']}")
        except Exception as e:
            logger.error(f"Error processing {file_info['file_name']}: {e}")
            results.append({
                "page_number": file_info.get("calculated_page_number", i+1),
                "file_name": file_info["file_name"],
                "error": str(e)
            })
    
    # Create final summary
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    
    summary = {
        "total_files": len(sorted_files),
        "processed_successfully": len(successful),
        "failed": len(failed),
        "results": results,
        "average_confidence": sum(r.get("confidence", 0) for r in successful) / len(successful) if successful else 0
    }
    
    logger.info(f"Completed processing. Success: {len(successful)}, Failed: {len(failed)}")
    
    return summary