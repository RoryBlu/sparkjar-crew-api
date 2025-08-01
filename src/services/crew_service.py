"""
Vanilla CrewAI service for agent and task management.
Uses CrewAI's native OpenAI integration with no custom LLM providers.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import asyncio
import uuid

from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, FileReadTool, DirectorySearchTool

from config import OPENAI_API_KEY, ENVIRONMENT
from sparkjar_shared.utils.chroma_client import ChromaClient
from services.mcp_service import MCPService
from sparkjar_shared.utils.crew_logger import CrewExecutionLogger

logger = logging.getLogger(__name__)

class CrewService:
    """
    Vanilla CrewAI service for managing agents, tasks, and crew execution.
    Uses CrewAI's built-in OpenAI integration.
    """
    
    def __init__(self):
        """Initialize the CrewAI service with OpenAI configuration."""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for CrewAI operation")
        
        self.chroma_client = ChromaClient()
        self.mcp_service = MCPService()
        self._setup_default_tools()
        
        logger.info("CrewService initialized with vanilla CrewAI and OpenAI")
    
    def _setup_default_tools(self):
        """Setup default tools available to all agents."""
        self.default_tools = [
            SerperDevTool(),  # Web search
            FileReadTool(),   # File operations
            DirectorySearchTool(),  # Directory operations
        ]
        
        # Add MCP tools
        mcp_tools = self.mcp_service.get_available_tools()
        self.default_tools.extend(mcp_tools)
        
        logger.info(f"Loaded {len(self.default_tools)} default tools")
    
    def create_agent(self, 
                    role: str,
                    goal: str,
                    backstory: str,
                    tools: Optional[List[Any]] = None,
                    model: str = "gpt-4o",
                    temperature: float = 0.7,
                    max_tokens: Optional[int] = None,
                    **kwargs) -> Agent:
        """
        Create a CrewAI agent with vanilla OpenAI configuration.
        
        Args:
            role: The agent's role
            goal: The agent's goal
            backstory: The agent's backstory
            tools: List of tools (defaults to default_tools)
            model: OpenAI model to use (default: gpt-4o)
            temperature: Model temperature (default: 0.7)
            max_tokens: Maximum tokens for responses
            **kwargs: Additional agent parameters
        
        Returns:
            CrewAI Agent instance
        """
        if tools is None:
            tools = self.default_tools.copy()
        
        # CrewAI will automatically use OpenAI when OPENAI_API_KEY is set
        agent_config = {
            "role": role,
            "goal": goal,
            "backstory": backstory,
            "tools": tools,
            "verbose": ENVIRONMENT == "development",
            "allow_delegation": kwargs.get("allow_delegation", False),
            "max_iter": kwargs.get("max_iter", 5),
            "memory": kwargs.get("memory", True),
            **kwargs
        }
        
        # Add model configuration if specified
        if model != "gpt-4o" or temperature != 0.7 or max_tokens:
            llm_config = {
                "model": model,
                "temperature": temperature
            }
            if max_tokens:
                llm_config["max_tokens"] = max_tokens
            
            agent_config["llm"] = llm_config
        
        agent = Agent(**agent_config)
        logger.info(f"Created agent with role: {role}, model: {model}")
        
        return agent
    
    def create_task(self,
                   description: str,
                   agent: Agent,
                   expected_output: str,
                   context: Optional[List[Task]] = None,
                   tools: Optional[List[Any]] = None,
                   **kwargs) -> Task:
        """
        Create a CrewAI task.
        
        Args:
            description: Task description
            agent: Agent to execute the task
            expected_output: Expected output format
            context: List of prerequisite tasks
            tools: Additional tools for this task
            **kwargs: Additional task parameters
        
        Returns:
            CrewAI Task instance
        """
        task_config = {
            "description": description,
            "agent": agent,
            "expected_output": expected_output,
            **kwargs
        }
        
        if context:
            task_config["context"] = context
        
        if tools:
            task_config["tools"] = tools
        
        task = Task(**task_config)
        logger.info(f"Created task: {description[:50]}...")
        
        return task
    
    def create_crew(self,
                   agents: List[Agent],
                   tasks: List[Task],
                   process: Process = Process.sequential,
                   verbose: Optional[bool] = None,
                   memory: bool = True,
                   **kwargs) -> Crew:
        """
        Create a CrewAI crew.
        
        Args:
            agents: List of agents
            tasks: List of tasks
            process: Execution process (sequential/hierarchical)
            verbose: Verbose output (defaults to development mode)
            memory: Enable crew memory
            **kwargs: Additional crew parameters
        
        Returns:
            CrewAI Crew instance
        """
        if verbose is None:
            verbose = ENVIRONMENT == "development"
        
        crew_config = {
            "agents": agents,
            "tasks": tasks,
            "process": process,
            "verbose": verbose,
            "memory": memory,
            **kwargs
        }
        
        crew = Crew(**crew_config)
        logger.info(f"Created crew with {len(agents)} agents and {len(tasks)} tasks")
        
        return crew
    
    async def execute_crew(self,
                          crew: Crew,
                          inputs: Optional[Dict[str, Any]] = None,
                          job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a crew asynchronously with full logging to crew_job_event table.
        
        Args:
            crew: CrewAI crew to execute
            inputs: Input parameters for the crew
            job_id: Optional job ID for tracking
        
        Returns:
            Execution result with metadata
        """
        start_time = datetime.utcnow()
        execution_id = job_id or str(uuid.uuid4())
        
        logger.info(f"Starting crew execution {execution_id}")
        
        # Initialize crew execution logger
        crew_logger = CrewExecutionLogger(execution_id)
        
        try:
            # Execute crew with full logging capture
            async with crew_logger.capture_crew_logs(log_level="INFO"):
                # Log crew configuration
                await crew_logger.log_crew_step("crew_config", {
                    "agent_count": len(crew.agents),
                    "task_count": len(crew.tasks),
                    "agent_roles": [agent.role for agent in crew.agents],
                    "crew_process": str(crew.process),
                    "verbose": crew.verbose,
                    "memory_enabled": crew.memory
                })
                
                # Execute crew in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                
                # Create a wrapper function that sets the job context
                def execute_with_context():
                    import threading
                    # Set job ID in thread-local storage for callbacks
                    current_thread = threading.current_thread()
                    current_thread.crew_job_id = execution_id
                    
                    try:
                        return crew.kickoff(inputs=inputs or {})
                    finally:
                        # Clean up thread-local data
                        if hasattr(current_thread, 'crew_job_id'):
                            delattr(current_thread, 'crew_job_id')
                
                result = await loop.run_in_executor(None, execute_with_context)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            execution_result = {
                "execution_id": execution_id,
                "status": "completed",
                "result": result,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "agent_count": len(crew.agents),
                "task_count": len(crew.tasks),
                "success": True
            }
            
            logger.info(f"Crew execution {execution_id} completed in {duration:.2f}s")
            return execution_result
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Log the error with full context
            await crew_logger.log_crew_error(e, {
                "execution_id": execution_id,
                "duration_seconds": duration,
                "agent_count": len(crew.agents),
                "task_count": len(crew.tasks),
                "inputs": inputs
            })
            
            execution_result = {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "agent_count": len(crew.agents),
                "task_count": len(crew.tasks),
                "success": False
            }
            
            logger.error(f"Crew execution {execution_id} failed after {duration:.2f}s: {e}")
            return execution_result
    
    def get_crew_builder_crew(self, crew_name: str, crew_purpose: str) -> Crew:
        """
        Create the crew_builder crew for generating new crews.
        
        Args:
            crew_name: Name of the crew to build
            crew_purpose: Purpose of the crew to build
        
        Returns:
            Configured crew_builder crew
        """
        # Architect agent
        architect = self.create_agent(
            role="Crew Architect",
            goal="Design optimal crew structures for specific business purposes",
            backstory="""You are an expert in CrewAI architecture and business process automation. 
            You understand how to break down complex business objectives into discrete agent roles 
            and task workflows. You design crews that are efficient, maintainable, and aligned 
            with business goals.""",
            model="gpt-4o",
            temperature=0.3
        )
        
        # Developer agent
        developer = self.create_agent(
            role="Crew Developer",
            goal="Implement crew configurations with proper technical specifications",
            backstory="""You are a skilled developer who translates crew designs into working 
            CrewAI configurations. You know the technical details of agent configuration, 
            task dependencies, and tool integration. You write clean, maintainable crew code.""",
            model="gpt-4o",
            temperature=0.2
        )
        
        # Validator agent
        validator = self.create_agent(
            role="Crew Validator",
            goal="Ensure crew configurations meet quality and performance standards",
            backstory="""You are a quality assurance expert who validates crew configurations 
            for correctness, performance, and best practices. You catch potential issues before 
            deployment and ensure crews will execute successfully.""",
            model="gpt-4o",
            temperature=0.1
        )
        
        # Design task
        design_task = self.create_task(
            description=f"""Design a crew architecture for: {crew_name}
            Purpose: {crew_purpose}
            
            Analyze the purpose and determine:
            1. Required agent roles and their responsibilities
            2. Task breakdown and dependencies
            3. Tool requirements
            4. Process flow (sequential/hierarchical)
            5. Performance considerations
            
            Output a detailed crew design specification.""",
            agent=architect,
            expected_output="A comprehensive crew design document with agent roles, tasks, and process flow"
        )
        
        # Implementation task
        implement_task = self.create_task(
            description=f"""Implement the crew configuration for: {crew_name}
            
            Based on the design specification, create:
            1. Agent configurations with roles, goals, and backstories
            2. Task definitions with proper dependencies
            3. Tool assignments
            4. Crew configuration
            
            Provide working CrewAI Python code.""",
            agent=developer,
            expected_output="Complete Python code for the crew configuration using CrewAI framework",
            context=[design_task]
        )
        
        # Validation task
        validate_task = self.create_task(
            description=f"""Validate the crew implementation for: {crew_name}
            
            Review the implementation for:
            1. Technical correctness
            2. Best practices compliance
            3. Performance optimization
            4. Error handling
            5. Documentation quality
            
            Provide validation report and any necessary corrections.""",
            agent=validator,
            expected_output="Validation report with approval or required corrections",
            context=[design_task, implement_task]
        )
        
        # Create and return crew
        crew = self.create_crew(
            agents=[architect, developer, validator],
            tasks=[design_task, implement_task, validate_task],
            process=Process.sequential,
            memory=True
        )
        
        return crew
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of CrewAI service.
        
        Returns:
            Health status information
        """
        try:
            # Test basic agent creation
            test_agent = self.create_agent(
                role="Test Agent",
                goal="Validate service health",
                backstory="I am a test agent for health checks."
            )
            
            health_info = {
                "status": "healthy",
                "service": "crew_service",
                "openai_configured": bool(OPENAI_API_KEY),
                "default_tools_count": len(self.default_tools),
                "mcp_tools_available": len(self.mcp_service.get_available_tools()),
                "chroma_connected": await self.chroma_client.health_check(),
                "test_agent_created": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("CrewService health check passed")
            return health_info
            
        except Exception as e:
            logger.error(f"CrewService health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "crew_service",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global service instance
_crew_service = None

def get_crew_service() -> CrewService:
    """Get the global CrewService instance."""
    global _crew_service
    if _crew_service is None:
        _crew_service = CrewService()
    return _crew_service
