"""
Book Ingestion Crew
A crew for processing book ingestion from Google Drive using OCR and content extraction.
"""

import os
import logging
import yaml
from typing import Dict, Any
from crewai import Agent, Task, Crew, Process

logger = logging.getLogger(__name__)

def load_config():
    """Load agent and task configurations from YAML files."""
    config_dir = os.path.join(os.path.dirname(__file__), 'config')
    
    # Load agents config
    agents_file = os.path.join(config_dir, 'agents.yaml')
    with open(agents_file, 'r') as f:
        agents_config = yaml.safe_load(f)
    
    # Load tasks config  
    tasks_file = os.path.join(config_dir, 'tasks.yaml')
    with open(tasks_file, 'r') as f:
        tasks_config = yaml.safe_load(f)
    
    return agents_config, tasks_config

def kickoff(inputs: dict, logger=None):
    """
    Entry point for the book ingestion crew.
    Processes books from Google Drive using OCR and content extraction.
    
    Args:
        inputs: Dictionary containing the job context including:
            - google_drive_folder_path: Path to Google Drive folder with book images
            - language: Language for OCR processing (en, es, fr, de, it)
            - client_user_id: Client user ID for authentication
            - job_id: Job identifier
        logger: Optional enhanced logger instance
        
    Returns:
        Dictionary with execution results
    """
    # Use standard logger for logging
    standard_logger = logging.getLogger(__name__)
    
    standard_logger.info("=" * 80)
    standard_logger.info("BOOK INGESTION CREW - STARTING")
    standard_logger.info("=" * 80)
    standard_logger.info(f"Received inputs: {inputs}")
    
    try:
        # Load configurations
        agents_config, tasks_config = load_config()
        
        # Extract job metadata
        job_id = inputs.get('job_id', 'unknown')
        client_id = inputs.get('client_user_id', 'unknown')
        folder_path = inputs.get('google_drive_folder_path', '')
        language = inputs.get('language', 'en')
        
        if hasattr(logger, 'log_event'):
            logger.log_event("CREW_START", {
                "crew_type": "book_ingestion_crew",
                "job_id": job_id,
                "client_id": client_id,
                "folder_path": folder_path,
                "language": language
            })
        
        standard_logger.info("Creating agents from config...")
        
        # Import tools
        from .tools.simple_file_upload_tool import SimpleFileUploadTool
        from .tools.google_drive_tool import GoogleDriveTool
        from .tools.sj_sequential_thinking_tool import SJSequentialThinkingTool
        from .tools.image_viewer_tool import ImageViewerTool
        
        # Create tool instances
        tools_map = {
            'simple_file_upload': SimpleFileUploadTool(),
            'google_drive_tool': GoogleDriveTool(),
            'sj_sequential_thinking': SJSequentialThinkingTool(),
            'image_viewer': ImageViewerTool()
        }
        
        # Create agents from config
        agents = {}
        for agent_name, agent_config in agents_config.items():
            # Get tools for this agent
            agent_tools = []
            if 'tools' in agent_config:
                for tool_name in agent_config['tools']:
                    if tool_name in tools_map:
                        agent_tools.append(tools_map[tool_name])
                    else:
                        standard_logger.warning(f"Tool '{tool_name}' not found for agent '{agent_name}'")
            
            # Use model name directly - CrewAI handles the LLM instance
            model_name = agent_config.get('model', 'gpt-4o-mini')
            
            agents[agent_name] = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=agent_config['backstory'],
                verbose=True,
                allow_delegation=False,
                tools=agent_tools,
                llm=model_name,
                multimodal=agent_config.get('multimodal', False)
            )
            standard_logger.info(f"Created agent: {agent_name} with {len(agent_tools)} tools")
        
        standard_logger.info("Creating tasks from config...")
        
        # Create tasks from config
        tasks = []
        task_dict = {}  # Keep track of tasks by name for context references
        
        for task_name, task_config in tasks_config.items():
            # Format task description with actual input data
            formatted_description = task_config['description'].format(
                job_id=job_id,
                client_id=client_id,
                folder_path=folder_path,
                language=language,
                inputs=inputs
            )
            
            task = Task(
                description=formatted_description,
                expected_output=task_config['expected_output'],
                agent=agents[task_config['agent']]
            )
            tasks.append(task)
            task_dict[task_name] = task
            standard_logger.info(f"Created task: {task_name}")
        
        # Now set context for tasks that need it
        for task_name, task_config in tasks_config.items():
            if 'context' in task_config and task_config['context']:
                context_task_names = task_config['context']
                context_tasks = [task_dict[ctx_name] for ctx_name in context_task_names if ctx_name in task_dict]
                if context_tasks:
                    task_dict[task_name].context = context_tasks
                    standard_logger.info(f"Set context for task '{task_name}': {context_task_names}")
        
        standard_logger.info("Creating crew...")
        
        # Create the crew
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False  # Disable memory for this implementation
        )
        
        # Set up callbacks if logger provided (should be SimpleCrewLogger)
        if logger and hasattr(logger, 'create_step_callback'):
            crew.step_callback = logger.create_step_callback()
            crew.task_callback = logger.create_task_callback()
            standard_logger.info("Crew callbacks configured for simple logging")
        
        standard_logger.info("Crew created successfully")
        
        # Set logger callbacks if available
        if logger and hasattr(logger, 'get_callbacks'):
            standard_logger.info("Setting up logger callbacks...")
            callbacks = logger.get_callbacks()
            for callback in callbacks:
                crew.callbacks.append(callback)
        
        standard_logger.info("Executing crew kickoff...")
        
        # Execute the crew
        result = crew.kickoff()
        
        standard_logger.info(f"Crew execution completed. Result: {result}")
        
        # Build response
        response = {
            "status": "completed",
            "result": {
                "message": "Book ingestion processing completed successfully",
                "job_id": job_id,
                "client_id": client_id,
                "folder_path": folder_path,
                "language": language,
                "crew_output": str(result)
            }
        }
        
        if hasattr(logger, 'log_event'):
            logger.log_event("CREW_COMPLETE", {
                "success": True,
                "job_id": job_id
            })
        
        standard_logger.info("=" * 80)
        standard_logger.info("BOOK INGESTION CREW - COMPLETED")
        standard_logger.info("=" * 80)
        
        return response
        
    except Exception as e:
        error_msg = f"Book ingestion crew failed: {str(e)}"
        standard_logger.error(error_msg, exc_info=True)
        
        if hasattr(logger, 'log_event'):
            logger.log_event("ERROR_OCCURRED", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
        
        return {
            "status": "failed",
            "error": error_msg,
            "result": None
        }