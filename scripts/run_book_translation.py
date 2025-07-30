#!/usr/bin/env python3
"""
Run book translation crew through the Crew API.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_db
from src.services.job_service import JobService
from src.database.models import CrewJob
from sqlalchemy.orm import Session


async def run_translation():
    """Run the book translation crew."""
    
    # Translation crew context
    context = {
        "book_title": "Las Aventuras Completas del Reino Celestial",
        "source_table": "vervelyn_books",
        "output_table": "translated_books",
        "client_id": 17  # Vervelyn client
    }
    
    job_service = JobService()
    
    # Create job
    print("Creating translation job...")
    job = await job_service.create_job(
        crew_name="book_translation_crew",
        context=context
    )
    
    print(f"Job created with ID: {job.id}")
    print(f"Job key: {job.job_key}")
    print(f"Status: {job.status}")
    
    # Poll for completion
    print("\nTranslating book...")
    while True:
        # Get fresh job status
        db: Session = next(get_db())
        current_job = db.query(CrewJob).filter(CrewJob.id == job.id).first()
        
        if current_job.status == "completed":
            print("\n✅ Translation completed!")
            if current_job.result:
                result = json.loads(current_job.result)
                print(f"\nResult: {json.dumps(result, indent=2)}")
            break
        elif current_job.status == "failed":
            print("\n❌ Translation failed!")
            if current_job.error:
                print(f"Error: {current_job.error}")
            break
        else:
            print(".", end="", flush=True)
            await asyncio.sleep(5)
        
        db.close()
    
    return job


if __name__ == "__main__":
    asyncio.run(run_translation())