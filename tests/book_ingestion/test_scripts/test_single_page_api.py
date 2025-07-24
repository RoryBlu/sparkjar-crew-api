#!/usr/bin/env python
"""Test book ingestion with a single page through the API."""
import requests
import time
import json
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXNlcnZpY2UiLCJzY29wZXMiOlsic3BhcmtqYXJfaW50ZXJuYWwiXSwiZXhwIjoxNzUzMjM0NTk3LCJpYXQiOjE3NTMxNDgxOTd9.AfyCqcRqMQbtnv9on_MEoNXoLO3zr-P9aT2us2_dEx4"

def create_job():
    """Create a single page test job."""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test with just 1 page
    job_data = {
        "job_key": "book_ingestion_crew",
        "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
        "google_drive_folder_path": "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
        "language": "es",
        "process_pages_limit": 1  # Just process 1 page
    }
    
    print("📤 Creating test job for 1 page...")
    
    response = requests.post(
        f"{API_URL}/crew_job",
        headers=headers,
        json=job_data
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to create job: {response.status_code}")
        print(response.text)
        return None
    
    job = response.json()
    job_id = job["id"]
    print(f"✅ Job created: {job_id}")
    
    return job_id

def monitor_job(job_id):
    """Monitor job progress."""
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    print(f"\n📊 Monitoring job: {job_id}")
    print("=" * 60)
    
    last_event_count = 0
    
    while True:
        response = requests.get(
            f"{API_URL}/crew_job/{job_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get job status: {response.status_code}")
            break
        
        job = response.json()
        status = job["status"]
        events = job.get("events", [])
        
        # Show new events
        new_events = events[last_event_count:]
        for event in new_events:
            event_type = event["event_type"]
            content = event.get("content", {})
            
            if event_type == "crew_message":
                if isinstance(content, dict):
                    agent = content.get("agent", "Unknown")
                    message = content.get("message", "")
                    if message and len(message) > 5:
                        print(f"[{event['timestamp']}] 🤖 {agent}: {message[:100]}...")
            elif event_type == "task_complete":
                task = content.get("task", "Unknown task") if isinstance(content, dict) else "Task"
                print(f"[{event['timestamp']}] ✅ Task complete: {task}")
            elif event_type == "agent_action":
                if isinstance(content, dict):
                    tool = content.get("tool", "Unknown")
                    print(f"[{event['timestamp']}] 🔧 Using tool: {tool}")
        
        last_event_count = len(events)
        
        print(f"\n📈 Status: {status} | Total events: {len(events)}")
        
        if status in ["completed", "failed", "cancelled"]:
            break
        
        time.sleep(2)
    
    # Final summary
    if status == "completed":
        result = job.get("result", {})
        print("\n✅ Job completed successfully!")
        print(f"Result: {json.dumps(result, indent=2)}")
    else:
        error = job.get("error_message", "Unknown error")
        print(f"\n❌ Job {status}: {error}")
    
    print(f"\nTotal events logged: {len(events)}")
    print(f"Check crew_job_event table for job_id: {job_id}")

def main():
    """Test single page processing."""
    print("🧪 Testing Book Ingestion API with 1 Page")
    print("=" * 60)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code != 200:
            print("❌ API is not running! Start it with:")
            print("   python3.12 services/crew-api/main.py")
            return
    except:
        print("❌ Cannot connect to API at", API_URL)
        return
    
    print("✅ API is running")
    
    # Create and monitor job
    job_id = create_job()
    if job_id:
        monitor_job(job_id)

if __name__ == "__main__":
    main()