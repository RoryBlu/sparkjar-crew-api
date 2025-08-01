from pathlib import Path
import logging

import yaml
from crewai import Agent, Crew, Process, Task

logger = logging.getLogger(__name__)

from sparkjar_shared.utils.enhanced_crew_logger import EnhancedCrewLogger
# Import tools
from sparkjar_shared.tools.memory.sj_memory_tool import SJMemoryTool
from sparkjar_shared.tools.memory.sj_sequential_thinking_tool import SJSequentialThinkingTool
from sparkjar_shared.tools.document.sj_document_tool import SJDocumentTool
from sparkjar_shared.tools.gmail_api_sender_tool import GmailAPISenderTool
# Import custom tools
from sparkjar_shared.tools.search.google_search_tool import GoogleSearchTool

CONFIG_DIR = Path(__file__).parent / "config"

def _load_yaml(file_name: str):
    path = CONFIG_DIR / file_name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_crew() -> Crew:
    """Build the Entity Research Crew from YAML configs."""
    try:
        agents_cfg = _load_yaml("agents.yaml")
        tasks_cfg = _load_yaml("tasks.yaml")
    except Exception as e:
        logger.error(f"Failed to load crew configuration: {e}")
        raise ValueError(f"Crew configuration error: {e}")

    # Initialize tools
    memory_tool = SJMemoryTool()
    thinking_tool = SJSequentialThinkingTool()
    document_tool = SJDocumentTool()
    email_tool = GmailAPISenderTool()
    
    # Initialize custom tools
    google_search_tool = GoogleSearchTool()

    # Create agents with appropriate tools based on their tasks
    agents = {}
    for name, params in agents_cfg.items():
        # Assign tools based on agent role
        if name == "lead_researcher":
            # Lead researcher needs memory and sequential thinking for strategy
            params["tools"] = [memory_tool, thinking_tool]
        elif name == "web_intelligence_analyst":
            # Web analyst needs search tool
            params["tools"] = [google_search_tool, memory_tool]
        elif name == "document_analyst":
            # Document analyst needs memory and document tools
            params["tools"] = [memory_tool, document_tool]
        elif name == "relationship_mapper":
            # Relationship mapper needs memory and thinking tools
            params["tools"] = [memory_tool, thinking_tool]
        elif name == "report_compiler":
            # Report compiler needs memory tool and email for notification
            params["tools"] = [memory_tool, email_tool]
        elif name == "document_archivist":
            # Document archivist needs document service and email tools
            params["tools"] = [document_tool, memory_tool, email_tool]
        
        agents[name] = Agent(**params)

    tasks = []
    for task_name, cfg in tasks_cfg.items():
        agent = agents[cfg["agent"]]
        description = cfg.get("description", "")
        expected_output = cfg.get("expected_output")
        task = Task(
            description=description,
            expected_output=expected_output,
            agent=agent,
        )
        tasks.append(task)

    # Validate crew has agents and tasks
    if not agents:
        raise ValueError("No agents configured for crew")
    if not tasks:
        raise ValueError("No tasks configured for crew")
    
    logger.info(f"Built crew with {len(agents)} agents and {len(tasks)} tasks")
    
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=True,
    )
    return crew

def kickoff(inputs: dict, logger=None):
    """Build the crew and execute it with the provided inputs."""
    # Validate required inputs
    if not inputs:
        raise ValueError("No inputs provided to crew")
    
    if 'entity_name' not in inputs:
        raise ValueError("Required input 'entity_name' not provided")
    # Look up recipient email if not provided
    if 'recipient_email' not in inputs:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import sessionmaker
        from .database.models import ClientUsers
        import os
        
        # Get client_user_id from the job context
        client_user_id = inputs.get('client_user_id')
        if client_user_id:
            # Use sync database connection
            database_url = os.getenv('DATABASE_URL_DIRECT')
            if database_url:
                # Convert asyncpg URL to psycopg2 for sync
                sync_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
                engine = create_engine(sync_url)
                Session = sessionmaker(bind=engine)
                
                with Session() as session:
                    result = session.execute(
                        select(ClientUsers.email).where(ClientUsers.id == client_user_id)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        inputs['recipient_email'] = user
                    else:
                        inputs['recipient_email'] = 'no-reply@sparkjar.com'
                engine.dispose()
            else:
                inputs['recipient_email'] = 'no-reply@sparkjar.com'
        else:
            inputs['recipient_email'] = 'no-reply@sparkjar.com'
    
    crew = build_crew()

    if logger:
        # Configure callbacks so agent and tool activity is captured
        crew.step_callback = logger.create_step_callback()
        crew.task_callback = logger.create_task_callback()

        # Log the crew start event
        logger.log_event(
            EnhancedCrewLogger.CREW_START,
            {"inputs": inputs},
        )

        with logger.capture_logs():
            result = crew.kickoff(inputs=inputs)

        # Mark completion and flush remaining events
        logger.log_event(
            EnhancedCrewLogger.CREW_COMPLETE,
            {"result_type": type(result).__name__},
        )
        logger.stop()
    else:
        result = crew.kickoff(inputs=inputs)

    # Convert CrewOutput to serializable format
    if hasattr(result, 'raw'):
        # This is a CrewOutput object
        serializable_result = {
            "status": "completed",
            "crew_name": "entity_research_crew",
            "job_key": "entity_research_crew",
            "raw_output": result.raw,
            "tasks_output": []
        }
        
        # Extract individual task outputs
        if hasattr(result, 'tasks_output') and result.tasks_output:
            for idx, task_output in enumerate(result.tasks_output):
                task_data = {
                    "task_index": idx,
                    "output": str(task_output.raw) if hasattr(task_output, 'raw') else str(task_output),
                }
                if hasattr(task_output, 'agent'):
                    task_data["agent"] = str(task_output.agent)
                if hasattr(task_output, 'description'):
                    task_data["description"] = str(task_output.description)
                serializable_result["tasks_output"].append(task_data)
        
        # Include JSON output if available
        if hasattr(result, 'json_dict') and result.json_dict:
            serializable_result["json_output"] = result.json_dict
        
        # Include token usage if available
        if hasattr(result, 'token_usage') and result.token_usage:
            serializable_result["token_usage"] = dict(result.token_usage)
        
        return serializable_result
    else:
        # Fallback for unexpected result format
        return {
            "status": "completed",
            "crew_name": "entity_research_crew",
            "job_key": "entity_research_crew",
            "raw_output": str(result)
        }
