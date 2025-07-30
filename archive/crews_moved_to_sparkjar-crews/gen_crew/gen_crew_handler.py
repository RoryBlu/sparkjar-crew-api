"""
Gen Crew Handler - Database-driven crew for general content generation.
Loads configuration from crew_cfgs table and handles most crew types dynamically.
Contains all crew loading logic internally.
"""
import importlib
import logging
from typing import Dict, Any, List, Optional, cast
import uuid

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from sqlalchemy import select
from pydantic import BaseModel

from crews.base import BaseCrewHandler
from database.connection import get_direct_session
from database.models import CrewCfgs, CrewJobs

from api.models import JobStatus

logger = logging.getLogger(__name__)

class GenCrewHandler(BaseCrewHandler):
    """
    Gen Crew Handler that loads configurations from database.
    Handles MOST crews (not all) through dynamic JSON configuration.
    Contains integrated crew loading functionality.
    """
    
    def __init__(self):
        super().__init__()
        self._tool_registry = {}
    
    def _safe_serialize(self, obj):
        """Safely serialize an object to JSON-compatible format."""
        import json
        try:
            # Try direct serialization first
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # Fall back to string representation
            if obj is None:
                return None
            elif hasattr(obj, 'dict'):
                try:
                    return obj.dict()
                except:
                    return str(obj)
            else:
                return str(obj)
    
    async def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the gen crew with database-loaded configuration, context validation, and full logging.
        
        Args:
            request_data: Job request data including crew parameters (must include job_id for proper logging)
            
        Returns:
            Dictionary containing execution results
        """
        self.log_execution_start(request_data)
        
        # Extract job_id for proper database logging
        job_id = request_data.get("job_id")
        if not job_id:
            # If no job_id provided, this is a direct execution - create a minimal job record for logging
            job_id = await self._create_execution_job_record(request_data)
        
        # Ensure enhanced logger is initialized for this job
        if not self.enhanced_logger or str(self.job_id) != str(job_id):
            self.set_job_id(uuid.UUID(job_id))

        enhanced_logger = self.enhanced_logger
        
        try:
            # Extract crew identifier from request (job_key or crew_name)
            job_key = request_data.get("job_key")
            crew_name = request_data.get("crew_name", "gen_crew")
            
            if not job_key and not crew_name:
                raise ValueError("Either job_key or crew_name is required for GenCrewHandler")

            # Load crew configuration from database
            logger.info(f"Loading crew configuration: {job_key or crew_name}")
            crew_config = await self._load_config(job_key or crew_name, "crew")
            if not crew_config:
                raise ValueError(f"No crew configuration found for: {job_key or crew_name}")

            # Validate request data against crew's context model (Pydantic)
            context_model_config = crew_config.get("context_model")
            if context_model_config:
                validated_context = await self._load_and_validate_context_model(request_data, context_model_config)
                # Extract class name from the string representation for logging
                context_type = context_model_config.split('(')[0] if isinstance(context_model_config, str) else "unknown"
                if enhanced_logger:
                    enhanced_logger.log_event(
                        "context_validated",
                        {
                            "context_model_type": context_type,
                            "validated_fields": list(validated_context.dict().keys())
                            if hasattr(validated_context, "dict")
                            else [],
                        },
                    )
            else:
                # Fallback to old JSON schema validation if context_model not found
                context_schema = crew_config.get("context_schema")
                if context_schema:
                    validated_context = await self.validate_crew_context(request_data, context_schema)
                    if enhanced_logger:
                        enhanced_logger.log_event(
                            "context_validated",
                            {
                                "schema_fields": list(
                                    context_schema.get("properties", {}).keys()
                                ),
                                "validated_fields": list(validated_context.keys()),
                            },
                        )
                else:
                    validated_context = request_data
                    if enhanced_logger:
                        enhanced_logger.log_event(
                            "context_validation_skipped",
                            {
                                "reason": "No context_model or context_schema in crew config"
                            },
                        )

            # Load and instantiate crew from configuration  
            crew = await self._load_crew_from_config_data(crew_config)
            
            # Prepare inputs for crew execution using validated context
            crew_inputs = self._prepare_crew_inputs(validated_context)
            
            # Execute the crew with full logging
            logger.info(f"Executing crew: {job_key or crew_name}")
            if enhanced_logger:
                crew.step_callback = enhanced_logger.create_step_callback()
                crew.task_callback = enhanced_logger.create_task_callback()
                with enhanced_logger.capture_logs():
                    enhanced_logger.log_event(
                        "crew_execution_start",
                        {
                            "crew_name": crew_name,
                            "job_key": job_key,
                            "agent_count": len(crew.agents),
                            "task_count": len(crew.tasks),
                            "input_keys": list(crew_inputs.keys()),
                        },
                    )

                    result = crew.kickoff(inputs=crew_inputs)

                    enhanced_logger.log_event(
                        "crew_execution_complete",
                        {"result_type": type(result).__name__},
                    )
            else:
                result = crew.kickoff(inputs=crew_inputs)
            
            # Write output file if specified in crew config
            await self._write_output_file(crew_config, result, crew_name, job_key)
            
            # Serialize CrewOutput for JSON storage
            from crewai import CrewOutput
            
            if isinstance(result, CrewOutput):
                # Extract serializable data from CrewOutput
                try:
                    # Try to get JSON dict first (most structured)
                    json_dict = getattr(result, 'json_dict', None)
                    if json_dict and isinstance(json_dict, dict):
                        serializable_result = json_dict
                        logger.info(f"Using CrewOutput.json_dict: {len(str(json_dict))} characters")
                    else:
                        # Fall back to raw output
                        raw_output = result.raw if hasattr(result, 'raw') else str(result)
                        serializable_result = {
                            "raw": raw_output,
                            "type": "crew_output",
                            "token_usage": self._safe_serialize(getattr(result, 'token_usage', None)),
                            "tasks_count": len(getattr(result, 'tasks_output', [])),
                            "tasks_summary": [
                                {
                                    "description": getattr(task, 'description', '')[:200] + "..." if len(getattr(task, 'description', '')) > 200 else getattr(task, 'description', ''),
                                    "output_length": len(task.raw) if hasattr(task, 'raw') else len(str(task))
                                } for task in getattr(result, 'tasks_output', [])
                            ]
                        }
                        logger.info(f"Using CrewOutput.raw: {len(raw_output)} characters")
                    
                    # Validate JSON serializability
                    import json
                    json.dumps(serializable_result, default=str)
                    
                except Exception as e:
                    logger.warning(f"CrewOutput serialization failed: {e}")
                    # Ultimate fallback - just use raw string
                    serializable_result = {
                        "raw": str(result),
                        "type": "crew_output_fallback",
                        "serialization_error": str(e)
                    }
            else:
                serializable_result = result
            
            # Format response
            response = {
                "status": "completed",
                "crew_name": crew_name,
                "job_key": job_key,
                "result": serializable_result,
                "inputs": crew_inputs,
                "job_id": job_id
            }
            
            self.log_execution_complete(response)
            return response
            
        except Exception as e:
            # Get safe values for error logging
            safe_crew_name = request_data.get("crew_name", "gen_crew")
            safe_job_key = request_data.get("job_key")
            
            # Log error with full context
            if enhanced_logger:
                enhanced_logger.log_event(
                    "crew_execution_error",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "crew_name": safe_crew_name,
                        "job_key": safe_job_key,
                        "job_id": job_id,
                    },
                )
            
            self.log_execution_error(e)
            return {
                "status": "failed",
                "error": str(e),
                "crew_name": safe_crew_name,
                "job_key": safe_job_key,
                "job_id": job_id
            }

    async def _load_crew(self, crew_name: str) -> Crew:
        """
        Load a crew by name from database configuration.
        
        Args:
            crew_name: Name of the crew to load
            
        Returns:
            Instantiated Crew object ready for execution
            
        Raises:
            ValueError: If crew configuration not found or invalid
        """
        logger.info(f"Loading crew: {crew_name}")
        
        # Load crew configuration
        crew_config = await self._load_config(crew_name, "crew")
        if not crew_config:
            raise ValueError(f"Crew configuration '{crew_name}' not found")
        
        # Load referenced agents and tasks
        agent_names = crew_config.get("agents", [])
        agents = await self._load_agents(agent_names)
        tasks = await self._load_tasks(crew_config.get("tasks", []), agents, agent_names)
        
        # Create crew instance - handle manager_agent vs manager_llm
        crew_settings = crew_config.get("crew_settings", {})
        manager_agent_name = crew_settings.get("manager_agent")
        manager_agent = None
        
        if manager_agent_name:
            # Find the manager agent from the loaded agents by matching agent names
            for i, agent_name in enumerate(agent_names):
                if agent_name == manager_agent_name:
                    manager_agent = agents[i]
                    logger.info(f"Found manager agent: {manager_agent_name}")
                    break
                    
        return Crew(
            agents=agents,
            tasks=tasks,
            process=self._get_process_type(crew_settings.get("process", "sequential")),
            verbose=crew_settings.get("verbose", True),
            memory=crew_settings.get("memory", True),
            manager_llm=crew_settings.get("manager_llm"),
            manager_agent=manager_agent,
            embedder=self._validate_and_get_embedder_config(crew_settings),
            max_iter=crew_settings.get("max_iter", 3),
            max_execution_time=crew_settings.get("max_execution_time", 300)
        )

    async def _load_config(self, schema_name: str, config_type: str) -> Optional[Dict[str, Any]]:
        """Load a single configuration by schema_name and config_type from crew_cfgs table."""
        async with get_direct_session() as session:
            result = await session.execute(
                select(CrewCfgs)
                .where(CrewCfgs.schema_name == schema_name)
                .where(CrewCfgs.config_type == config_type)
            )
            config = result.scalar_one_or_none()
            if config:
                return cast(Optional[Dict[str, Any]], config.config_data)
            return None

    async def _create_execution_job_record(self, request_data: Dict[str, Any]) -> str:
        """
        Create a minimal job record for direct crew execution to ensure proper logging FK constraints.
        
        Args:
            request_data: The execution request data
            
        Returns:
            Created job ID as string
        """
        from datetime import datetime
        
        job_id = str(uuid.uuid4())
        
        async with get_direct_session() as session:
            job_record = CrewJobs(
                id=job_id,
                job_key=request_data.get("job_key", "direct_execution"),
                client_user_id=request_data.get("client_user_id", str(uuid.uuid4())),
                actor_type=request_data.get("actor_type", "system"),
                actor_id=request_data.get("actor_id", str(uuid.uuid4())),
                status=JobStatus.RUNNING,
                started_at=datetime.utcnow(),
                attempts=1,
                payload=request_data
            )
            session.add(job_record)
            await session.commit()
            
        logger.info(f"Created execution job record: {job_id}")
        return job_id

    async def _load_agents(self, agent_names: List[str]) -> List[Agent]:
        """Load and instantiate agents from configuration."""
        agents = []
        
        for agent_name in agent_names:
            # Map agent name to actual schema name in database
            schema_name = self._map_agent_name_to_schema(agent_name)
            agent_config = await self._load_config(schema_name, "agent")
            if not agent_config:
                raise ValueError(f"Agent configuration '{agent_name}' (schema: '{schema_name}') not found")
            
            # Autoload tools for this agent
            tools = await self._autoload_tools(agent_config.get("tools", []))
            
            # Create agent instance
            agent = Agent(
                role=agent_config.get("role", agent_name),
                goal=agent_config.get("goal", ""),
                backstory=agent_config.get("backstory", ""),
                verbose=agent_config.get("verbose", True),
                allow_delegation=agent_config.get("allow_delegation", False),
                max_iter=agent_config.get("max_iter", 2),
                tools=tools
            )
            
            agents.append(agent)
            logger.info(f"Loaded agent: {agent_name}")
        
        return agents

    async def _load_tasks(self, task_names: List[str], agents: List[Agent], agent_names: List[str]) -> List[Task]:
        """Load and instantiate tasks from configuration."""
        tasks = []
        
        # Create agent mapping for task assignment using agent names (schema_name)
        agent_map = {}
        for i, agent_name in enumerate(agent_names):
            agent_map[agent_name] = agents[i]
        
        for task_name in task_names:
            task_config = await self._load_config(task_name, "task")
            if not task_config:
                raise ValueError(f"Task configuration '{task_name}' not found")
            
            # Find assigned agent
            agent_role = task_config.get("agent")
            agent = agent_map.get(agent_role) if agent_role else agents[0]
            
            if not agent:
                raise ValueError(f"Agent '{agent_role}' not found for task '{task_name}'")
            
            # Autoload tools for this task
            tools = await self._autoload_tools(task_config.get("tools", []))
            
            # Create task instance
            task = Task(
                description=task_config.get("description", ""),
                expected_output=task_config.get("expected_output", ""),
                agent=agent,
                tools=tools
            )
            
            tasks.append(task)
            logger.info(f"Loaded task: {task_name}")
        
        return tasks

    async def _autoload_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """
        Dynamically import and instantiate tools by name.
        
        Args:
            tool_names: List of tool class names to import
            
        Returns:
            List of instantiated tool objects
        """
        tools = []
        
        for tool_name in tool_names:
            if tool_name in self._tool_registry:
                # Use cached tool class
                tool_class = self._tool_registry[tool_name]
            else:
                # Try to import the tool
                tool_class = await self._import_tool(tool_name)
                if tool_class:
                    self._tool_registry[tool_name] = tool_class
                else:
                    logger.warning(f"Could not import tool: {tool_name}")
                    continue
            
            # Instantiate the tool
            try:
                tool_instance = tool_class()
                tools.append(tool_instance)
                logger.info(f"Loaded tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to instantiate tool {tool_name}: {e}")
        
        return tools

    async def _import_tool(self, tool_name: str) -> Optional[type]:
        """
        Import a tool class by name using common import paths.
        
        Args:
            tool_name: Name of the tool class to import
            
        Returns:
            Tool class if found, None otherwise
        """
        # Map tool names to actual class names
        tool_class_mapping = {
            "context_query": "ContextQueryTool"
        }
        
        # Get the actual class name
        class_name = tool_class_mapping.get(tool_name, tool_name)
        
        # Common tool import paths to try
        import_paths = [
            f"crewai_tools",
            f"crewai.tools", 
            f"src.tools.{tool_name}_tool",
            f"src.tools.{tool_name}",
            f"src.crews.tools.{tool_name}",
            f"tools.{tool_name}"
        ]
        
        for import_path in import_paths:
            try:
                # Try to import the module
                module = importlib.import_module(import_path)
                
                # Get the tool class from the module
                if hasattr(module, class_name):
                    tool_class = getattr(module, class_name)
                    if issubclass(tool_class, BaseTool):
                        logger.info(f"Successfully imported {class_name} from {import_path}")
                        return tool_class
                        
            except ImportError:
                continue
            except Exception as e:
                logger.warning(f"Error importing {class_name} from {import_path}: {e}")
                continue
        
        logger.error(f"Could not import tool: {tool_name} (class: {class_name})")
        return None

    def _get_process_type(self, process_name: str) -> Process:
        """Convert process name to CrewAI Process enum."""
        process_map = {
            "sequential": Process.sequential,
            "hierarchical": Process.hierarchical
        }
        return process_map.get(process_name.lower(), Process.sequential)

    async def _load_and_validate_context_model(self, request_data: Dict[str, Any], context_model_config: Any) -> BaseModel:
        """
        Load and validate request data against a Pydantic context model.
        
        Args:
            request_data: The incoming request data
            context_model_config: Context model configuration (dict or string)
            
        Returns:
            Instantiated and validated Pydantic model
            
        Raises:
            ValueError: If model loading or validation fails
        """
        try:
            # Handle different context_model formats
            if isinstance(context_model_config, dict):
                # Old format: {"type": "ContentIdeatorContext", "attributes": {...}}
                model_type = context_model_config.get("type")
                default_attributes = context_model_config.get("attributes", {})
            elif isinstance(context_model_config, str):
                # New format: "ContentIdeatorContext(field1=value1, field2=value2, ...)"
                model_type, default_attributes = self._parse_pydantic_string(context_model_config)
            else:
                raise ValueError(f"Unsupported context_model format: {type(context_model_config)}")
            
            if not model_type:
                raise ValueError("Context model config missing model type")
            
            # Import the Pydantic model class dynamically
            model_class = await self._import_context_model(model_type)
            if not model_class:
                raise ValueError(f"Could not import context model: {model_type}")
            
            # Merge request data with defaults (request data takes priority)
            model_data = {}
            model_data.update(default_attributes)  # Start with defaults
            
            # Map important request fields to model fields
            field_mappings = {
                "prompt": "user_prompt",
                "user_prompt": "user_prompt",
                "client_user_id": "client_user_id",
                "actor_type": "actor_type", 
                "actor_id": "actor_id",
                "job_key": "job_key"
            }
            
            for request_field, model_field in field_mappings.items():
                if request_field in request_data:
                    model_data[model_field] = request_data[request_field]
            
            # Add any other fields that exist in both request and model
            for field_name, field_value in request_data.items():
                if field_name not in field_mappings and field_name in default_attributes:
                    model_data[field_name] = field_value
            
            # Instantiate and validate the Pydantic model
            logger.info(f"Creating {model_type} with data: {list(model_data.keys())}")
            context_model = model_class(**model_data)
            
            logger.info(f"✅ Successfully created and validated {model_type}")
            return context_model
            
        except Exception as e:
            logger.error(f"❌ Context model validation failed: {e}")
            raise ValueError(f"Context model validation failed: {str(e)}")

    def _parse_pydantic_string(self, pydantic_string: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse a Pydantic string representation into model type and default attributes.
        
        Example: "ContentIdeatorContext(field1=None, field2=[], field3={})"
        Returns: ("ContentIdeatorContext", {"field1": None, "field2": [], "field3": {}})
        """
        try:
            # Extract class name
            if '(' not in pydantic_string:
                raise ValueError("Invalid Pydantic string format")
            
            class_name = pydantic_string.split('(')[0].strip()
            
            # Extract the content inside parentheses
            content = pydantic_string[pydantic_string.find('(')+1:pydantic_string.rfind(')')]
            
            # Parse field=value pairs
            attributes = {}
            if content.strip():
                # Split by commas, but be careful of nested structures
                parts = []
                current_part = ""
                paren_depth = 0
                bracket_depth = 0
                brace_depth = 0
                
                for char in content:
                    if char == '(':
                        paren_depth += 1
                    elif char == ')':
                        paren_depth -= 1
                    elif char == '[':
                        bracket_depth += 1
                    elif char == ']':
                        bracket_depth -= 1
                    elif char == '{':
                        brace_depth += 1
                    elif char == '}':
                        brace_depth -= 1
                    elif char == ',' and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                        parts.append(current_part.strip())
                        current_part = ""
                        continue
                    
                    current_part += char
                
                if current_part.strip():
                    parts.append(current_part.strip())
                
                # Parse each field=value pair
                for part in parts:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Convert string representations to actual values
                        if value == 'None':
                            attributes[key] = None
                        elif value == '[]':
                            attributes[key] = []
                        elif value == '{}':
                            attributes[key] = {}
                        elif value.startswith("'") and value.endswith("'"):
                            attributes[key] = value[1:-1]  # Remove quotes
                        elif value.startswith('"') and value.endswith('"'):
                            attributes[key] = value[1:-1]  # Remove quotes
                        else:
                            # Try to evaluate safely for basic types
                            try:
                                # Only allow safe literals
                                import ast
                                attributes[key] = ast.literal_eval(value)
                            except:
                                # If evaluation fails, store as string
                                attributes[key] = value
            
            logger.info(f"Parsed Pydantic string: {class_name} with {len(attributes)} attributes")
            return class_name, attributes
            
        except Exception as e:
            logger.error(f"Failed to parse Pydantic string: {e}")
            raise ValueError(f"Could not parse Pydantic string: {pydantic_string}")

    async def _import_context_model(self, model_type: str) -> Optional[type]:
        """
        Import a Pydantic context model class by name.
        
        Args:
            model_type: Name of the Pydantic model class to import
            
        Returns:
            Model class if found, None otherwise
        """
        # Common import paths for context models
        import_paths = [
            f"src.models.context",
            f"src.models.context_models", 
            f"src.crews.models.context",
            f"src.api.models",
            f"models.context",
            f"models"
        ]
        
        for import_path in import_paths:
            try:
                # Try to import the module
                module = importlib.import_module(import_path)
                
                # Get the model class from the module
                if hasattr(module, model_type):
                    model_class = getattr(module, model_type)
                    if issubclass(model_class, BaseModel):
                        logger.info(f"Successfully imported {model_type} from {import_path}")
                        return model_class
                        
            except ImportError:
                continue
            except Exception as e:
                logger.warning(f"Error importing {model_type} from {import_path}: {e}")
                continue
        
        logger.error(f"Could not import context model: {model_type}")
        return None

    def _prepare_crew_inputs(self, validated_context: Any) -> Dict[str, Any]:
        """
        Prepare inputs for crew execution from validated context.
        Handles both Pydantic model instances and dictionary data.
        
        Args:
            validated_context: Validated context (Pydantic model or dict)
            
        Returns:
            Formatted inputs for crew execution
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Handle Pydantic model instances
        if isinstance(validated_context, BaseModel):
            logger.info(f"Processing Pydantic context model: {type(validated_context).__name__}")
            
            # Serialize Pydantic model to dictionary
            context_dict = validated_context.model_dump()
            
            # Extract the model data for crew inputs
            inputs = {}
            
            # Add all model fields as crew inputs
            for field_name, field_value in context_dict.items():
                if field_value is not None:  # Only add non-None values
                    inputs[field_name] = field_value
            
            # Ensure critical fields are present for database tools
            required_db_fields = ["client_user_id", "actor_type", "actor_id"]
            for field in required_db_fields:
                if field not in inputs or not inputs[field]:
                    if hasattr(validated_context, field):
                        inputs[field] = getattr(validated_context, field)
            
            logger.info(f"✅ Pydantic model serialized to crew inputs: {list(inputs.keys())}")
            return inputs
        
        # Handle dictionary data (fallback for legacy JSON schema validation)
        elif isinstance(validated_context, dict):
            logger.info("Processing dictionary context data (legacy mode)")
            return self._prepare_crew_inputs_legacy(validated_context)
        
        else:
            raise ValueError(f"Unsupported context type: {type(validated_context)}")

    def _prepare_crew_inputs_legacy(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method to prepare inputs for crew execution from request data.
        Validates all required parameters before crew execution.
        
        Args:
            request_data: Raw request data
            
        Returns:
            Formatted inputs for crew execution
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Request data received and will be processed
        
        # CRITICAL VALIDATION: Check required parameters
        required_fields = ["client_user_id", "actor_type", "actor_id", "job_key", "prompt"]
        missing_fields = []
        
        for field in required_fields:
            if not request_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required fields for crew execution: {missing_fields}")
        
        # CRITICAL VALIDATION: Validate actor_type
        actor_type = request_data.get("actor_type")
        if actor_type not in ["human", "synth"]:
            raise ValueError(f"Invalid actor_type '{actor_type}'. Must be 'human' or 'synth'")
        
        # CRITICAL VALIDATION: Validate UUIDs (basic format check)
        import uuid
        uuid_fields = ["client_user_id", "actor_id"]
        for field in uuid_fields:
            value = request_data.get(field)
            if value:
                try:
                    uuid.UUID(value)
                except ValueError:
                    raise ValueError(f"Invalid UUID format for {field}: {value}")
        
        # Extract common parameters
        inputs = {}
        
        # Map request fields to crew input fields
        field_mappings = {
            "topic": "topic",
            "query": "query", 
            "content": "content",
            "text": "text",
            "url": "url",
            "search_query": "search_query",
            "instructions": "instructions",
            "prompt": "prompt",  # Keep original prompt field name
            "job_key": "job_key"  # Ensure job_key is passed through
        }
        
        for request_field, crew_field in field_mappings.items():
            if request_field in request_data:
                inputs[crew_field] = request_data[request_field]
        
        # Add any additional custom inputs
        if "inputs" in request_data:
            inputs.update(request_data["inputs"])
        
        # CRITICAL: Add validated context parameters for database tools
        # These are the exact parameters the context_query tool needs
        inputs["client_user_id"] = request_data["client_user_id"]
        inputs["actor_type"] = request_data["actor_type"]
        inputs["actor_id"] = request_data["actor_id"]
        
        # Context params validated and added successfully
        
        # Crew inputs prepared successfully
        return inputs

    def get_job_metadata(self) -> Dict[str, Any]:
        """Get metadata about this job type."""
        return {
            "handler_class": self.__class__.__name__,
            "description": "Database-driven crew for general content generation (handles MOST crews)",
            "configuration_source": "crew_cfgs database table",
            "supports_dynamic_loading": True,
            "crew_types_supported": [
                "content_generation",
                "research_and_analysis", 
                "writing_and_editing",
                "data_processing",
                "report_generation"
            ]
        }

    async def _load_crew_from_config_data(self, crew_config: Dict[str, Any]) -> Crew:
        """
        Load a crew from provided configuration data.
        
        Args:
            crew_config: Complete crew configuration dictionary
            
        Returns:
            Instantiated Crew object ready for execution
            
        Raises:
            ValueError: If crew configuration is invalid
        """
        logger.info("Loading crew from provided config data")
        
        # Load referenced agents and tasks
        agent_names = crew_config.get("agents", [])
        agents = await self._load_agents(agent_names)
        tasks = await self._load_tasks(crew_config.get("tasks", []), agents, agent_names)
        
        # Create crew instance - handle manager_agent vs manager_llm
        crew_settings = crew_config.get("crew_settings", {})
        manager_agent_name = crew_settings.get("manager_agent")
        manager_agent = None
        
        if manager_agent_name:
            # Find the manager agent from the loaded agents by matching agent names
            for i, agent_name in enumerate(agent_names):
                if agent_name == manager_agent_name:
                    manager_agent = agents[i]
                    logger.info(f"Found manager agent: {manager_agent_name}")
                    break
        
        return Crew(
            agents=agents,
            tasks=tasks,
            process=self._get_process_type(crew_settings.get("process", "sequential")),
            verbose=crew_settings.get("verbose", True),
            memory=crew_settings.get("memory", True),
            manager_llm=crew_settings.get("manager_llm"),
            manager_agent=manager_agent,
            embedder=self._validate_and_get_embedder_config(crew_settings),
            max_iter=crew_settings.get("max_iter", 3),
            max_execution_time=crew_settings.get("max_execution_time", 300)
        )

    def _map_agent_name_to_schema(self, agent_name: str) -> str:
        """Map agent names used in crew configs to actual schema_names in database."""
        agent_mapping = {
            "writer": "content_writer",
            "quality_assurance_editor": "qa_content_editor",
            # Add other mappings as needed
            # Names that match exactly don't need mapping
        }
        return agent_mapping.get(agent_name, agent_name)

    def _validate_and_get_embedder_config(self, crew_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and return proper embedder configuration.
        Fails fast if embedder config is missing or invalid - NO FALLBACKS!
        """
        embedder_config = crew_settings.get("embedder")
        
        if not embedder_config:
            raise ValueError(
                "Missing embedder configuration in crew settings. "
                "Embedder config is required and must specify provider and model. "
                "Expected format: {'provider': 'huggingface', 'config': {'model': 'Alibaba-NLP/gte-multilingual-base'}}"
            )
        
        # Validate required fields
        if not isinstance(embedder_config, dict):
            raise ValueError(f"Embedder config must be a dictionary, got: {type(embedder_config)}")
            
        provider = embedder_config.get("provider")
        if not provider:
            raise ValueError("Embedder config missing required 'provider' field")
            
        # Only support Railway embeddings service - NO OPENAI BULLSHIT!
        if provider != "huggingface":
            raise ValueError(f"Unsupported embedder provider: {provider}. Only 'huggingface' is supported for Railway embeddings service.")
            
        config = embedder_config.get("config", {})
        if not config.get("model"):
            raise ValueError("Railway embeddings requires 'config.model' field (should be 'Alibaba-NLP/gte-multilingual-base')")
            
        # Validate the correct model for Railway service
        expected_model = "Alibaba-NLP/gte-multilingual-base"
        if config.get("model") != expected_model:
            logger.warning(f"Model '{config.get('model')}' may not work with Railway embeddings. Expected: {expected_model}")
        
        logger.info(f"Using Railway embedder config: {embedder_config}")
        return embedder_config

    async def _write_output_file(self, crew_config: Dict[str, Any], result: Any, crew_name: str, job_key: Optional[str]) -> None:
        """
        Write crew execution results to the output file specified in crew config.
        
        Args:
            crew_config: Crew configuration containing output_file path
            result: Crew execution result
            crew_name: Name of the crew
            job_key: Job key for the execution
        """
        output_file = crew_config.get("output_file")
        if not output_file:
            logger.debug("No output_file specified in crew config, skipping file output")
            return
        
        try:
            import os
            from datetime import datetime
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Prepare content to write
            timestamp = datetime.now().isoformat()
            content = f"""# {crew_config.get('crew_name', crew_name)} - Execution Report

**Generated:** {timestamp}
**Job Key:** {job_key or 'N/A'}
**Crew:** {crew_name}

## Results

"""
            
            # Add the actual result content
            if hasattr(result, 'raw'):
                content += result.raw
            elif hasattr(result, '__str__'):
                content += str(result)
            else:
                content += f"Result: {result}"
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ Report saved to: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to write output file {output_file}: {e}")
