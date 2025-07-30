"""Memory Import Crew implementation.

This crew parses raw input, disambiguates names against the memory
service and then writes entities and relationships before verifying the
import results.

import logging
logger = logging.getLogger(__name__)
"""
from pathlib import Path
from typing import Any, Dict, List
import yaml
from crewai import Agent, Crew, Process, Task

from tools.sj_memory_tool import SJMemoryTool

CONFIG_DIR = Path(__file__).resolve().parent / "config"

def _load_yaml(file_name: str) -> Dict[str, Any]:
    """Load a YAML configuration file from ``CONFIG_DIR``."""
    path = CONFIG_DIR / file_name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_crew() -> Crew:
    """Build the Memory Import Crew based on YAML configs."""
    agents_cfg = _load_yaml("agents.yaml")
    tasks_cfg = _load_yaml("tasks.yaml")

    memory_tool = SJMemoryTool()

    # Create agents. Each one uses the memory tool.
    agents: Dict[str, Agent] = {}
    for name, params in agents_cfg.items():
        params = dict(params)
        params["tools"] = [memory_tool]
        agents[name] = Agent(**params)

    # Create tasks sequentially so each task depends on the previous one.
    tasks: List[Task] = []
    last_task: Task | None = None
    for task_name, cfg in tasks_cfg.items():
        agent = agents[cfg["agent"]]
        task = Task(
            description=cfg.get("description", ""),
            expected_output=cfg.get("expected_output"),
            agent=agent,
            context=[last_task] if last_task else [],
        )
        tasks.append(task)
        last_task = task

    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=True,
    )

def kickoff(inputs: Dict[str, Any], logger=None) -> Any:
    """Run the Memory Import Crew.
    
    Args:
        inputs: Input dictionary containing the data to process
        logger: Optional logger instance (used by SparkJAR job system)
    
    Returns:
        The crew execution result
    """
    crew = build_crew()
    # Pass the entire inputs dict as raw_input to maintain compatibility
    return crew.kickoff(inputs={"raw_input": inputs})