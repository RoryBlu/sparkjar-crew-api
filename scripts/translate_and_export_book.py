#!/usr/bin/env python3
"""
Translate a book using the crew API and export it as a markdown file.
"""

import json
import requests
import time
import os
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8100"  # Adjust if running on different port
API_TOKEN = os.getenv("API_TOKEN", "your-api-token-here")  # Set your API token

# Vervelyn book information
VERVELYN_BOOK = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "actor_type": "client",
    "actor_id": "1d1c2154-242b-4f49-9ca8-e57129ddc823",  # Using clients_id as actor_id
    "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
    "target_language": "en"
}

def create_translation_job():
    """Create a book translation job via the API."""
    print("Creating translation job...")
    
    url = f"{API_BASE_URL}/crew_job"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "job_key": "book_translation_crew",
        "request_data": VERVELYN_BOOK
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        job_data = response.json()
        print(f"Job created successfully! Job ID: {job_data['job_id']}")
        return job_data['job_id']
    except Exception as e:
        print(f"Error creating job: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def check_job_status(job_id):
    """Check the status of a translation job."""
    url = f"{API_BASE_URL}/crew_job/{job_id}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error checking job status: {e}")
        return None

def wait_for_job_completion(job_id, max_wait=3600):
    """Wait for job to complete with progress updates."""
    print(f"Waiting for job {job_id} to complete...")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"Job timed out after {max_wait} seconds")
            return None
            
        job_data = check_job_status(job_id)
        if not job_data:
            return None
            
        status = job_data.get('status', 'unknown')
        print(f"[{elapsed:.0f}s] Job status: {status}")
        
        if status == "completed":
            print("Job completed successfully!")
            return job_data
        elif status == "failed":
            print(f"Job failed: {job_data.get('error', 'Unknown error')}")
            return None
            
        time.sleep(10)  # Check every 10 seconds

def extract_translation_results(job_data):
    """Extract translated pages from job results."""
    try:
        # Navigate through the nested result structure
        result = job_data.get('result', {})
        if isinstance(result, str):
            result = json.loads(result)
            
        # The result should contain the translated pages
        # This structure might vary based on how the crew returns data
        return result
    except Exception as e:
        print(f"Error extracting results: {e}")
        return None

def export_to_markdown(job_id, job_data):
    """Export translated book to markdown file."""
    print("\nExporting to markdown...")
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"vervelyn_book_translation_{timestamp}.md"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# Vervelyn Book Translation\n\n")
            f.write(f"**Translation Job ID**: {job_id}\n")
            f.write(f"**Translated on**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Target Language**: English\n")
            f.write(f"**Source Book**: {VERVELYN_BOOK['book_key']}\n\n")
            f.write("---\n\n")
            
            # Extract and write the translated content
            result = job_data.get('result', {})
            if isinstance(result, str):
                # If result is a string, it might be the crew's output
                f.write(result)
            elif isinstance(result, dict):
                # If it's structured data, format it nicely
                if 'pages' in result:
                    for page in result['pages']:
                        f.write(f"## Page {page.get('page_number', '?')}\n\n")
                        f.write(page.get('translated_text', 'No translation available'))
                        f.write("\n\n---\n\n")
                else:
                    # Write whatever structure we have
                    f.write(json.dumps(result, indent=2, ensure_ascii=False))
            
        print(f"Successfully exported to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error exporting to markdown: {e}")
        return None

def main():
    """Main function to orchestrate the translation and export process."""
    print("=== Vervelyn Book Translation and Export ===\n")
    
    # Check if we can reach the API
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code != 200:
            print("Error: Cannot reach the API. Make sure the crew API is running.")
            print("Start it with: python main.py")
            return
    except:
        print("Error: Cannot connect to API at", API_BASE_URL)
        print("Make sure the crew API is running with: python main.py")
        return
    
    # Create translation job
    job_id = create_translation_job()
    if not job_id:
        return
        
    # Wait for completion
    job_data = wait_for_job_completion(job_id)
    if not job_data:
        return
        
    # Export to markdown
    output_file = export_to_markdown(job_id, job_data)
    if output_file:
        print(f"\nTranslation complete! Book exported to: {output_file}")
        print(f"You can now open {output_file} to read the translated book.")

if __name__ == "__main__":
    main()