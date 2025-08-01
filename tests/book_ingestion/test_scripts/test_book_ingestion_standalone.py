#!/usr/bin/env python3
"""
Standalone test for book ingestion crew.
This bypasses the complex import structure and runs the crew directly.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task

# Load environment variables
load_dotenv()

# Add crew-api src to Python path
crew_api_src = os.path.join(os.getcwd(), "services", "crew-api", "src")
sys.path.insert(0, crew_api_src)

# Import tools
from sparkjar_shared.tools.google_drive_tool import GoogleDriveTool
from sparkjar_shared.tools.image_viewer_tool import ImageViewerTool
from sparkjar_shared.tools.memory.sj_sequential_thinking_tool import SJSequentialThinkingTool
from sparkjar_shared.tools.database.database_storage_tool import DatabaseStorageTool

# Load configurations
config_dir = Path("services/crew-api/src/crews/book_ingestion_crew/config")
with open(config_dir / "agents_enhanced.yaml", "r") as f:
    agents_cfg = yaml.safe_load(f)
with open(config_dir / "tasks_enhanced.yaml", "r") as f:
    tasks_cfg = yaml.safe_load(f)

# Load request data
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)
request_data = request['request_data']

print("🚀 Testing Book Ingestion Crew (Standalone)")
print("=" * 70)
print(f"📋 Request Summary:")
print(f"  Client User ID: {request_data['client_user_id']}")
print(f"  Google Drive Path: {request_data['google_drive_folder_path']}")
print(f"  Language: {request_data['language']}")
print(f"  Book Year: {request_data['book_metadata']['year']}")
print("=" * 70)

try:
    # Initialize tools
    print("\n🔧 Initializing tools...")
    google_drive = GoogleDriveTool()
    image_viewer = ImageViewerTool()
    thinking_tool = SJSequentialThinkingTool()
    storage_tool = DatabaseStorageTool(client_user_id=request_data['client_user_id'])
    print("✅ Tools initialized")
    
    # Create agents
    print("\n🤖 Creating agents...")
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
            params["tools"] = []
            
        # Use model instead of llm
        if "model" in params:
            params["llm"] = params.pop("model")
            
        agents[name] = Agent(**params)
    print(f"✅ Created {len(agents)} agents")
    
    # Create tasks
    print("\n📝 Creating tasks...")
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
    print(f"✅ Created {len(tasks)} tasks")
    
    # Set up task context (dependencies)
    for task_name, cfg in tasks_cfg.items():
        if "context" in cfg and cfg["context"]:
            context_tasks = [task_dict[ctx] for ctx in cfg["context"] if ctx in task_dict]
            if context_tasks:
                task_dict[task_name].context = context_tasks
    
    # Create crew
    print("\n🚢 Creating crew...")
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False  # Disable CrewAI memory - we use our own
    )
    print("✅ Crew created")
    
    # Execute crew
    print("\n📊 Starting crew execution...")
    print("Processing first 25 pages from Google Drive...\n")
    
    result = crew.kickoff(request_data)
    
    print("\n✅ Crew execution completed!")
    print(f"Result: {result}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()