"""Batch Processing Book Ingestion Crew - Process ALL files in single crew run"""
from pathlib import Path
import yaml
from crewai import Agent, Crew, Process, Task
import logging
from typing import Dict, Any

# Import needed tools
from tools.google_drive_tool import GoogleDriveTool
from tools.image_viewer_tool import ImageViewerTool
from tools.sj_sequential_thinking_tool import SJSequentialThinkingTool
from tools.sj_memory_tool import SJMemoryTool

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
    tasks_cfg = _load_yaml("tasks_batch.yaml")
    
    # Initialize tools
    google_drive = GoogleDriveTool()
    image_viewer = ImageViewerTool()
    thinking_tool = SJSequentialThinkingTool()
    memory_tool = SJMemoryTool()
    
    # Create agents with proper tools
    agents = {}
    for name, params in agents_cfg.items():
        # Assign tools based on agent role
        if name == "file_manager":
            params["tools"] = [google_drive]
        elif name == "vision_specialist":
            # Vision specialist needs BOTH tools to list AND process
            params["tools"] = [google_drive, image_viewer]
        elif name == "reasoning_specialist":
            params["tools"] = [thinking_tool, image_viewer]
        elif name == "data_specialist":
            params["tools"] = [memory_tool]
        elif name == "project_manager":
            params["tools"] = []
        
        # Create agent
        agents[name] = Agent(**params)
    
    # Create tasks with proper dependencies
    tasks = []
    task_objects = {}
    
    # Create each task
    for task_name, task_cfg in tasks_cfg.items():
        task_cfg_copy = task_cfg.copy()
        agent_name = task_cfg_copy.pop("agent")
        context_names = task_cfg_copy.pop("context", [])
        
        task = Task(
            **task_cfg_copy,
            agent=agents[agent_name]
        )
        
        task_objects[task_name] = task
        tasks.append(task)
    
    # Set up task dependencies
    for task_name, task_cfg in tasks_cfg.items():
        if "context" in task_cfg and task_cfg["context"]:
            context_tasks = [task_objects[ctx] for ctx in task_cfg["context"]]
            task_objects[task_name].context = context_tasks
    
    # Create crew with all tasks
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False  # We use our own memory system
    )
    
    return crew

def kickoff(inputs: Dict[str, Any], logger=None) -> Dict[str, Any]:
    """
    Execute the book ingestion crew - process ALL pages in one run.
    
    Args:
        inputs: Input data including client_user_id, google_drive_folder_path, etc.
        logger: Optional logger
    
    Returns:
        Complete results with all pages processed
    """
    # Get client_user_id
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    # Add total_pages placeholder (will be determined by crew)
    inputs["total_pages"] = "all available"
    
    # Build crew
    crew = build_crew(client_user_id)
    
    # Execute crew - this will process ALL files
    logger.info("Executing batch book ingestion crew")
    result = crew.kickoff(inputs)
    
    return result