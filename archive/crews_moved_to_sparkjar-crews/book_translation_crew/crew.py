"""Book Translation Crew - Simple crew for translating ingested books."""
from pathlib import Path
import yaml
from crewai import Agent, Crew, Process, Task
import logging
from typing import Dict, Any, List

# Import needed tools with proper paths
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sparkjar_shared.tools.simple_db_storage_tool import SimpleDBStorageTool
from sparkjar_shared.tools.simple_db_query_tool import SimpleDBQueryTool

logger = logging.getLogger(__name__)

def build_translation_crew() -> Crew:
    """Build a simple crew for book translation."""
    
    # Load configurations
    config_path = Path(__file__).parent / "config"
    
    with open(config_path / "agents.yaml", "r") as f:
        agents_config = yaml.safe_load(f)
    
    with open(config_path / "tasks.yaml", "r") as f:
        tasks_config = yaml.safe_load(f)
    
    # Create tools
    storage_tool = SimpleDBStorageTool()
    query_tool = SimpleDBQueryTool()
    
    # Create single translation agent
    translation_agent = Agent(
        role=agents_config["translation_agent"]["role"],
        goal=agents_config["translation_agent"]["goal"],
        backstory=agents_config["translation_agent"]["backstory"],
        tools=[query_tool, storage_tool],
        llm_config={
            "model": agents_config["translation_agent"]["model"],
            "temperature": 0.3  # Lower temperature for consistent translations
        },
        verbose=True
    )
    
    # Create tasks in sequence
    query_task = Task(
        description=tasks_config["query_pages"]["description"],
        expected_output=tasks_config["query_pages"]["expected_output"],
        agent=translation_agent
    )
    
    translate_task = Task(
        description=tasks_config["translate_pages"]["description"],
        expected_output=tasks_config["translate_pages"]["expected_output"],
        agent=translation_agent
    )
    
    store_task = Task(
        description=tasks_config["store_translations"]["description"],
        expected_output=tasks_config["store_translations"]["expected_output"],
        agent=translation_agent
    )
    
    report_task = Task(
        description=tasks_config["report_results"]["description"],
        expected_output=tasks_config["report_results"]["expected_output"],
        agent=translation_agent
    )
    
    # Create crew with sequential process
    crew = Crew(
        agents=[translation_agent],
        tasks=[query_task, translate_task, store_task, report_task],
        process=Process.sequential,
        verbose=True,
        memory=False  # No memory needed for simple translation
    )
    
    return crew