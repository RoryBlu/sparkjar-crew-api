#!/usr/bin/env python3
"""Test book ingestion using the crew handler directly."""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add crew-api src to Python path
crew_api_src = os.path.join(os.getcwd(), "services", "crew-api", "src")
sys.path.insert(0, crew_api_src)

# Import the handler
from crews.book_ingestion_crew.book_ingestion_crew_handler import BookIngestionCrewHandler

# Load request data
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)

request_data = request['request_data']

print("🚀 Testing Book Ingestion Crew Handler")
print("=" * 70)
print(f"📋 Request Summary:")
print(f"  Client User ID: {request_data['client_user_id']}")
print(f"  Google Drive Path: {request_data['google_drive_folder_path']}")
print(f"  Language: {request_data['language']}")
print(f"  Book Year: {request_data['book_metadata']['year']}")
print("=" * 70)

async def run_test():
    """Run the crew handler test."""
    try:
        print("\n📊 Initializing crew handler...")
        handler = BookIngestionCrewHandler()
        
        print("🔧 Executing crew...")
        result = await handler.execute(
            job_id=f"test-{int(time.time())}",
            job_input=request_data
        )
        
        print("\n✅ Crew execution completed!")
        print(f"Result: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

# Run the async function
import time
if __name__ == "__main__":
    asyncio.run(run_test())