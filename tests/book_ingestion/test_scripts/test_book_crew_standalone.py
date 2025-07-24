#!/usr/bin/env python3
"""
Standalone test of book ingestion crew.
Runs the crew's main.py directly.
"""

import subprocess
import sys
import os
import json

# Test configuration
TEST_ARGS = [
    "google_drive",  # Mode: google_drive for real data
    "--client_user_id", "3a411a30-1653-4caf-acee-de257ff50e36",
    "--google_drive_folder_path", "sparkjar/vervelyn/castor gonzalez/book 1/",
    "--language", "es"
]

def run_crew_standalone():
    """Run the book ingestion crew standalone."""
    print("🚀 Book Ingestion Crew Standalone Test")
    print("="*60)
    
    crew_main = "services/crew-api/src/crews/book_ingestion_crew/main.py"
    
    if not os.path.exists(crew_main):
        print(f"❌ Error: {crew_main} not found")
        return
    
    print(f"\n📚 Running: python3 {crew_main} {' '.join(TEST_ARGS[:5])}...")
    print(f"   Additional args: {' '.join(TEST_ARGS[5:])}")
    
    try:
        # Run the crew directly
        cmd = ["python3", crew_main] + TEST_ARGS
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print("\n📊 Output:")
        print("-" * 60)
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  Errors/Warnings:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Crew execution completed successfully!")
        else:
            print(f"\n❌ Crew execution failed with code: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("\n⚠️  Execution timed out after 5 minutes")
    except Exception as e:
        print(f"\n❌ Error running crew: {str(e)}")

if __name__ == "__main__":
    run_crew_standalone()