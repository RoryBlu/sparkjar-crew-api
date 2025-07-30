#!/usr/bin/env python

import logging
logger = logging.getLogger(__name__)

"""
Execute book_ingestion_crew via API with proper payload.

This script:
1. Loads the JSON payload from file
2. Generates a valid JWT token
3. Makes the API call to create the job
4. Polls for job completion
5. Displays the results
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

# Add the current directory to Python path for imports

from .api.auth import create_token

# Configuration
API_URL = "http://localhost:8000"
PAYLOAD_FILE = "test_payloads/book_ingestion_crew_payload.json"
POLL_INTERVAL = 2  # seconds
MAX_POLL_TIME = 60  # seconds

def load_payload():
    """Load the JSON payload from file."""
    payload_path = os.path.join(os.path.dirname(__file__), PAYLOAD_FILE)
    with open(payload_path, 'r') as f:
        return json.load(f)

def generate_token():
    """Generate a fresh JWT token with sparkjar_internal scope."""
    return create_token(
        user_id="test-user",
        scopes=["sparkjar_internal"],
        expires_in_hours=1  # Short expiry for testing
    )

def execute_crew():
    """Execute the book_ingestion_crew via API."""
    logger.info("=" * 80)
    logger.info("EXECUTING BOOK INGESTION CREW VIA API")
    logger.info("=" * 80)
    
    # Load payload
    logger.info("\n1. Loading payload...")
    payload = load_payload()
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Generate token
    logger.info("\n2. Generating JWT token...")
    token = generate_token()
    logger.info("Token generated successfully")
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Check API health
        logger.info("\n3. Checking API health...")
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        if health_response.status_code == 200:
            logger.info("✅ API is healthy")
        else:
            logger.info(f"⚠️  API health check returned: {health_response.status_code}")
        
        # Create the job
        logger.info("\n4. Creating crew job...")
        create_response = requests.post(
            f"{API_URL}/crew_job",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if create_response.status_code != 200:
            logger.error(f"❌ Failed to create job: {create_response.status_code}")
            logger.info(f"Response: {create_response.text}")
            return
        
        job_data = create_response.json()
        job_id = job_data.get("job_id")
        logger.info(f"✅ Job created successfully!")
        logger.info(f"Job ID: {job_id}")
        logger.info(f"Initial status: {job_data.get('status')}")
        
        # Poll for job completion
        logger.info(f"\n5. Polling for job status (max {MAX_POLL_TIME}s)...")
        start_time = time.time()
        
        while (time.time() - start_time) < MAX_POLL_TIME:
            time.sleep(POLL_INTERVAL)
            
            # Get job status
            status_response = requests.get(
                f"{API_URL}/crew_job/{job_id}",
                headers=headers,
                timeout=5
            )
            
            if status_response.status_code != 200:
                logger.error(f"❌ Failed to get job status: {status_response.status_code}")
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            elapsed = int(time.time() - start_time)
            
            logger.info(f"[{elapsed}s] Status: {status}")
            
            # Check if job is complete
            if status == "completed":
                logger.info("\n✅ JOB COMPLETED SUCCESSFULLY!")
                logger.info("\nResult:")
                logger.info(json.dumps(status_data.get("result"), indent=2))
                
                # Display events if available
                events = status_data.get("events", [])
                if events:
                    logger.info(f"\nJob Events ({len(events)} total):")
                    for event in events[-5:]:  # Show last 5 events
                        logger.info(f"  - {event.get('event_type')}: {event.get('created_at')}")
                break
                
            elif status == "failed":
                logger.error("\n❌ JOB FAILED!")
                logger.error(f"Error: {status_data.get('error_message')}")
                logger.info(f"Result: {status_data.get('result')}")
                break
        
        else:
            logger.info(f"\n⏱️  Timeout: Job did not complete within {MAX_POLL_TIME} seconds")
            
    except requests.exceptions.ConnectionError:
        logger.error("\n❌ ERROR: Could not connect to API. Is the server running?")
        logger.info(f"   URL: {API_URL}")
    except requests.exceptions.Timeout:
        logger.error("\n❌ ERROR: Request timed out")
    except Exception as e:
        logger.error(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    execute_crew()