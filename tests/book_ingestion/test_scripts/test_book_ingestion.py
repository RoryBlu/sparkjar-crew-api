#!/usr/bin/env python3
"""
Test script for the book ingestion crew.
Tests with provided sample values to verify OCR functionality.
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
import httpx
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import token generation function
from services.crew_api.src.api.auth import create_token

# Test configuration
TEST_CONFIG = {
    "api_base_url": "http://localhost:8000",  # Adjust if running on different port
    "timeout": 30,  # HTTP timeout in seconds
    "poll_interval": 5,  # How often to check job status
    "max_poll_time": 600,  # Maximum time to wait for job completion (10 minutes)
}

# Test values as specified
TEST_VALUES = {
    "job_key": "book_ingestion_crew",
    "client_id": "550e8400-e29b-41d4-a716-446655440000",  # Default test client ID
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "actor_type": "user",
    "actor_id": "770e8400-e29b-41d4-a716-446655440002",  # Default test actor ID
    "google_drive_folder_path": "sparkjar/vervelyn/castor gonzalez/book 1/",
    "language": "es",
    "book_title": "Castor Gonzalez - Book 1",
    "book_author": "Castor Gonzalez",
    "confidence_threshold": 0.90,
    "max_retries": 2,
    "version": "original",
    "output_format": "txt"
}


def generate_auth_token() -> str:
    """Generate a JWT token for authentication."""
    print("🔑 Generating authentication token...")
    try:
        token = create_token(
            user_id="test_user",
            scopes=["sparkjar_internal"]
        )
        print("✅ Token generated successfully")
        return token
    except Exception as e:
        print(f"❌ Failed to generate token: {e}")
        sys.exit(1)


async def create_job(client: httpx.AsyncClient, token: str) -> Optional[str]:
    """Create a book ingestion job."""
    print("\n📚 Creating book ingestion job...")
    
    # Prepare request data
    request_data = {
        "data": {
            "job_id": f"test_{int(time.time())}",  # Unique job ID
            **TEST_VALUES
        }
    }
    
    print(f"Request data: {json.dumps(request_data['data'], indent=2)}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = await client.post(
            f"{TEST_CONFIG['api_base_url']}/crew_job",
            json=request_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result["job_id"]
            print(f"✅ Job created successfully! Job ID: {job_id}")
            return job_id
        else:
            print(f"❌ Failed to create job. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating job: {e}")
        return None


async def get_job_status(client: httpx.AsyncClient, token: str, job_id: str) -> Dict[str, Any]:
    """Get the status of a job."""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = await client.get(
            f"{TEST_CONFIG['api_base_url']}/crew_job/{job_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get job status. Status: {response.status_code}")
            return {"status": "error", "error": response.text}
            
    except Exception as e:
        print(f"❌ Error getting job status: {e}")
        return {"status": "error", "error": str(e)}


async def poll_job_status(client: httpx.AsyncClient, token: str, job_id: str):
    """Poll job status until completion."""
    print(f"\n⏳ Polling job status (checking every {TEST_CONFIG['poll_interval']} seconds)...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < TEST_CONFIG['max_poll_time']:
        job_info = await get_job_status(client, token, job_id)
        status = job_info.get("status", "unknown")
        
        # Only print if status changed
        if status != last_status:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Status: {status}")
            last_status = status
        
        if status == "completed":
            print("\n✅ Job completed successfully!")
            return job_info
        elif status == "failed":
            print("\n❌ Job failed!")
            print(f"Error: {job_info.get('error', 'Unknown error')}")
            return job_info
        
        await asyncio.sleep(TEST_CONFIG['poll_interval'])
    
    print("\n⏱️  Job timed out after {:.0f} seconds".format(time.time() - start_time))
    return {"status": "timeout"}


def display_results(job_info: Dict[str, Any]):
    """Display the job results in a formatted way."""
    print("\n" + "="*80)
    print("📊 JOB RESULTS")
    print("="*80)
    
    # Basic job info
    print(f"\nJob ID: {job_info.get('job_id', 'N/A')}")
    print(f"Status: {job_info.get('status', 'N/A')}")
    print(f"Created: {job_info.get('created_at', 'N/A')}")
    print(f"Completed: {job_info.get('completed_at', 'N/A')}")
    
    # Results
    if "result" in job_info and job_info["result"]:
        result = job_info["result"]
        print("\n📄 OCR RESULTS:")
        print("-" * 40)
        
        # Handle different result formats
        if isinstance(result, dict):
            # Check for transcript file
            if "transcript_file" in result:
                print(f"Transcript saved to: {result['transcript_file']}")
                
            # Check for pages processed
            if "pages_processed" in result:
                print(f"Total pages processed: {result['pages_processed']}")
                
            # Check for pages in result
            if "pages" in result:
                pages = result["pages"]
                print(f"Total pages in results: {len(pages)}")
                
                # Show first few pages as examples
                for i, page in enumerate(pages[:3]):
                    print(f"\n📄 Page {page.get('page_number', i+1)}:")
                    print(f"   File: {page.get('filename', 'N/A')}")
                    print(f"   Confidence: {page.get('confidence', 0):.2%}")
                    text = page.get('text', '')
                    if text:
                        preview = text[:200] + "..." if len(text) > 200 else text
                        print(f"   Text preview: {preview}")
                    
                if len(pages) > 3:
                    print(f"\n... and {len(pages) - 3} more pages")
                    
            # Check for summary stats
            if "summary" in result:
                summary = result["summary"]
                print(f"\n📊 SUMMARY:")
                print(f"Total pages: {summary.get('total_pages', 0)}")
                print(f"Average confidence: {summary.get('average_confidence', 0):.2%}")
                print(f"Pages above threshold ({TEST_VALUES['confidence_threshold']:.0%}): {summary.get('pages_above_threshold', 0)}")
                print(f"Processing time: {summary.get('processing_time', 'N/A')}")
                
            # Display any other result data
            elif not any(k in result for k in ["transcript_file", "pages_processed", "pages", "summary"]):
                print("\nRaw result data:")
                print(json.dumps(result, indent=2)[:1000])  # Limit output
        else:
            print(f"Result: {result}")
    
    # Errors
    if "error" in job_info:
        print(f"\n❌ ERROR: {job_info['error']}")
    
    # Events (if available)
    if "events" in job_info and job_info["events"]:
        print(f"\n📝 PROCESSING EVENTS ({len(job_info['events'])} total):")
        print("-" * 40)
        
        # Group events by type
        event_types = {}
        for event in job_info["events"]:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print("Event summary:")
        for event_type, count in event_types.items():
            print(f"  {event_type}: {count}")
        
        # Show last 10 events
        print("\nRecent events:")
        for event in job_info["events"][-10:]:
            timestamp = event.get("timestamp", "N/A")
            event_type = event.get("event_type", "N/A")
            message = event.get("message", "")
            print(f"[{timestamp}] {event_type}: {message[:100]}...")


async def main():
    """Main test function."""
    print("🚀 SparkJAR Book Ingestion Crew Test")
    print("="*80)
    
    # Generate token
    token = generate_auth_token()
    
    # Create HTTP client
    async with httpx.AsyncClient(timeout=TEST_CONFIG["timeout"]) as client:
        # Test API connectivity
        print("\n🔌 Testing API connectivity...")
        try:
            response = await client.get(f"{TEST_CONFIG['api_base_url']}/health")
            if response.status_code == 200:
                print("✅ API is healthy")
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print(f"Make sure the API is running at {TEST_CONFIG['api_base_url']}")
            return
        
        # Create job
        job_id = await create_job(client, token)
        if not job_id:
            print("❌ Failed to create job. Exiting.")
            return
        
        # Poll for results
        job_info = await poll_job_status(client, token, job_id)
        
        # Display results
        display_results(job_info)
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)