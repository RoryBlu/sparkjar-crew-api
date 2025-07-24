"""Enhanced Book Ingestion Crew using standard CrewAI patterns"""
from pathlib import Path
import yaml
from crewai import Agent, Crew, Process, Task
import logging

# Import needed tools
from tools.google_drive_tool import GoogleDriveTool
from tools.image_viewer_tool import ImageViewerTool
from tools.sj_sequential_thinking_tool import SJSequentialThinkingTool
from tools.database_storage_tool import DatabaseStorageTool

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
    tasks_cfg = _load_yaml("tasks_enhanced.yaml")
    
    # Initialize tools
    google_drive = GoogleDriveTool()
    image_viewer = ImageViewerTool()
    thinking_tool = SJSequentialThinkingTool()
    storage_tool = DatabaseStorageTool(client_user_id=client_user_id)
    
    # Create agents
    agents = {}
    for name, params in agents_cfg.items():
        # Assign tools based on agent role
        if name == "file_manager":
            params["tools"] = [google_drive]
        elif name == "vision_specialist":
            params["tools"] = [image_viewer]
        elif name == "reasoning_specialist":
            params["tools"] = [thinking_tool, image_viewer]
        elif name == "data_specialist":
            params["tools"] = [storage_tool]
        elif name == "project_manager":
            params["tools"] = []  # No tools needed
            
        # Use model instead of llm
        if "model" in params:
            params["llm"] = params.pop("model")
            
        agents[name] = Agent(**params)
    
    # Create tasks
    tasks = []
    task_dict = {}
    
    for task_name, cfg in tasks_cfg.items():
        task = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=agents[cfg["agent"]]
        )
        tasks.append(task)
        task_dict[task_name] = task
    
    # Set up task context (dependencies)
    for task_name, cfg in tasks_cfg.items():
        if "context" in cfg and cfg["context"]:
            context_tasks = [task_dict[ctx] for ctx in cfg["context"] if ctx in task_dict]
            if context_tasks:
                task_dict[task_name].context = context_tasks
    
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False  # Disable CrewAI memory - we use our own
    )

def kickoff(inputs: dict, logger=None):
    """Entry point for the book ingestion crew.
    
    Args:
        inputs: Input data from the job
        logger: Optional SparkJAR logger
    
    Returns:
        Crew execution result
    """
    # Extract client_user_id for database tool
    client_user_id = inputs.get("client_user_id")
    if not client_user_id:
        raise ValueError("client_user_id is required")
    
    # Build crew with client-specific database
    crew = build_crew(client_user_id)
    
    # Execute crew - CrewAI handles all errors internally
    return crew.kickoff(inputs)