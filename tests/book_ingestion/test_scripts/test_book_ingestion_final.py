#!/usr/bin/env python3
"""
Test book ingestion crew with proper environment setup.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add crew-api src to Python path
crew_api_src = os.path.join(os.getcwd(), "services", "crew-api", "src")
sys.path.insert(0, crew_api_src)

# Now we can import from the crew
from crews.book_ingestion_crew.crew import kickoff

# Load the request data
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)

request_data = request['request_data']

print("🚀 Testing Book Ingestion Crew")
print("=" * 70)
print(f"📋 Request Summary:")
print(f"  Client User ID: {request_data['client_user_id']}")
print(f"  Actor: {request_data['actor_type']} ({request_data['actor_id']})")
print(f"  Google Drive Path: {request_data['google_drive_folder_path']}")
print(f"  Language: {request_data['language']}")
print(f"  Book: {request_data['book_metadata']['title']} ({request_data['book_metadata']['year']})")
print(f"  Confidence Threshold: {request_data['confidence_threshold']}")
print("=" * 70)

try:
    print("\n📊 Starting crew execution...")
    print("Processing first 25 pages from Google Drive...\n")
    
    # Run the crew
    result = kickoff(request_data)
    
    print("\n✅ Crew execution completed!")
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()