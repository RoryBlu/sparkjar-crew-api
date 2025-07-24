#!/usr/bin/env python3
"""
Test script for book ingestion crew.
Tests the OCR processing of manuscript pages.
"""

import os
import sys
import requests
import time
import json
import jwt
from datetime import datetime, timedelta, UTC

# Test configuration
API_URL = "http://localhost:8000"
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "test-secret-key-for-development")

# Test values provided by user
TEST_DATA = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "google_drive_folder_path": "sparkjar/vervelyn/castor gonzalez/book 1/",
    "language": "es",
    "book_title": "Castor Gonzalez - Book 1",
    "book_author": "Castor Gonzalez",
    "book_description": "Spanish manuscript requiring OCR processing",
    "book_year": "2024",
    "confidence_threshold": 0.90,
    "max_retries": 3,
    "output_format": "json"
}


def generate_test_token():
    """Generate a JWT token for testing."""
    payload = {
        "sub": "test_user",
        "scopes": ["sparkjar_internal"],
        "exp": datetime.now(UTC) + timedelta(hours=1)
    }
    return jwt.encode(payload, API_SECRET_KEY, algorithm="HS256")


def test_api_connection(token):
    """Test if API is accessible."""
    print("Testing API connection...")
    try:
        response = requests.get(
            f"{API_URL}/health",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            print("✅ API is accessible")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?")
        return False


def create_book_ingestion_job(token):
    """Create a book ingestion job."""
    print("\n📚 Creating book ingestion job...")
    
    payload = {
        "job_key": "book_ingestion_crew",
        "request_data": TEST_DATA
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_URL}/crew_job",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            job_data = response.json()
            print(f"✅ Job created successfully!")
            print(f"   Job ID: {job_data['job_id']}")
            print(f"   Status: {job_data['status']}")
            return job_data['job_id']
        else:
            print(f"❌ Failed to create job: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating job: {str(e)}")
        return None


def poll_job_status(job_id, token, max_wait_minutes=10):
    """Poll job status until completion."""
    print(f"\n⏳ Monitoring job {job_id}...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while True:
        try:
            response = requests.get(
                f"{API_URL}/crew_job/{job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                job_data = response.json()
                status = job_data['status']
                
                # Calculate elapsed time
                elapsed = time.time() - start_time
                elapsed_str = f"{int(elapsed)}s"
                
                # Display status
                print(f"\r   Status: {status} (elapsed: {elapsed_str})", end="", flush=True)
                
                if status == "completed":
                    print("\n✅ Job completed successfully!")
                    return job_data
                elif status == "failed":
                    print("\n❌ Job failed!")
                    if job_data.get('error'):
                        print(f"   Error: {job_data['error']}")
                    return job_data
                
                # Check timeout
                if elapsed > max_wait_seconds:
                    print(f"\n⚠️  Job timed out after {max_wait_minutes} minutes")
                    return None
                    
            else:
                print(f"\n❌ Failed to get job status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"\n❌ Error polling job: {str(e)}")
            return None
            
        # Wait before next poll
        time.sleep(5)


def display_results(job_data):
    """Display job results in a readable format."""
    print("\n" + "="*60)
    print("📊 JOB RESULTS")
    print("="*60)
    
    # Job metadata
    print("\n📋 Job Information:")
    print(f"   ID: {job_data['job_id']}")
    print(f"   Status: {job_data['status']}")
    print(f"   Created: {job_data['created_at']}")
    if job_data.get('completed_at'):
        print(f"   Completed: {job_data['completed_at']}")
    
    # Results
    if job_data.get('result'):
        result = job_data['result']
        
        # Display book summary if available
        if result.get('book_key'):
            print(f"\n📖 Book Summary:")
            print(f"   Book Key: {result.get('book_key')}")
            print(f"   Total Pages: {result.get('total_pages', 'N/A')}")
            print(f"   Completed Pages: {result.get('completed_pages', 'N/A')}")
            print(f"   Average Confidence: {result.get('average_final_confidence', 'N/A')}")
        
        # Display individual page results if available
        if result.get('pages'):
            print(f"\n📄 Page Results ({len(result['pages'])} pages):")
            for page in result['pages'][:5]:  # Show first 5 pages
                print(f"\n   Page {page.get('page_number', 'N/A')}:")
                print(f"   - File: {page.get('file_name', 'N/A')}")
                print(f"   - Confidence: {page.get('confidence', 'N/A')}")
                if page.get('transcription'):
                    preview = page['transcription'][:100] + "..." if len(page['transcription']) > 100 else page['transcription']
                    print(f"   - Text Preview: {preview}")
            
            if len(result['pages']) > 5:
                print(f"\n   ... and {len(result['pages']) - 5} more pages")
    
    # Events
    if job_data.get('events'):
        print(f"\n📝 Processing Events ({len(job_data['events'])} total):")
        for event in job_data['events'][-5:]:  # Show last 5 events
            print(f"   - [{event['timestamp']}] {event['message']}")


def main():
    """Main test function."""
    print("🚀 Book Ingestion Crew Test")
    print("="*60)
    
    # Generate token
    token = generate_test_token()
    print(f"Generated test token: {token[:20]}...")
    
    # Test API connection
    if not test_api_connection(token):
        print("\n⚠️  Please make sure the API is running:")
        print("   .venv/bin/python services/crew-api/main.py")
        return
    
    # Create job
    job_id = create_book_ingestion_job(token)
    if not job_id:
        return
    
    # Poll for results
    job_data = poll_job_status(job_id, token)
    if not job_data:
        return
    
    # Display results
    display_results(job_data)
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    main()