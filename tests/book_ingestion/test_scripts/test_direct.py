#!/usr/bin/env python
"""
Test book ingestion crew directly without API.
This bypasses the API layer to test the crew implementation.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services/crew-api'))

import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_direct():
    """Test the book ingestion crew directly."""
    print("=" * 60)
    print("🧪 Direct Book Ingestion Crew Test")
    print("=" * 60)
    
    # Test payload
    payload = {
        "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",  # Vervelyn client
        "actor_type": "synth",
        "actor_id": "e30fc9f3-57da-4cf0-84e7-ea9188dd5fba",
        "job_key": "book_ingestion_crew",
        "book_id": "1QYg-OuNdXTJcBJYpQlUJcz5oWoN_aF-q",  # Castor Gonzalez - Book 1
        "book_title": "Castor Gonzalez - Book 1",
        "book_author": "Castor Gonzalez",
        "book_description": "Spanish manuscript",
        "book_year": 2006,
        "process_pages_limit": 2  # Start with just 2 pages for testing
    }
    
    try:
        # Import the crew
        print("\n📚 Importing book ingestion crew...")
        from src.crews.book_ingestion_crew.crew import kickoff
        print("✅ Import successful!")
        
        # Execute the crew
        print(f"\n🚀 Executing crew with {payload['process_pages_limit']} pages limit...")
        result = kickoff(inputs=payload)
        
        print("\n✅ Crew execution completed!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct())