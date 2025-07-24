#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Diagnose why book ingestion crew only uploads tracking files and not transcriptions."""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add the src directory to the Python path

from .database.connection import get_sync_session
from .database.models import CrewJobs, CrewJobEvent
from sqlalchemy import select, desc, and_
from .tools.google_drive_tool import GoogleDriveTool

def diagnose_book_ingestion_jobs():
    """Analyze recent book ingestion jobs to find why transcriptions aren't uploaded."""
    
    logger.info("DIAGNOSING BOOK INGESTION CREW ISSUES")
    logger.info("=" * 80)
    
    # Configuration
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    
    logger.info(f"Target folder: {folder_path}")
    logger.info(f"Client User ID: {client_user_id}")
    logger.info("\n")
    
    # 1. Check recent book_ingestion_crew jobs in database
    logger.info("1. RECENT BOOK INGESTION JOBS:")
    logger.info("-" * 80)
    
    with get_sync_session() as session:
        # Get recent book_ingestion_crew jobs
        recent_jobs = session.execute(
            select(CrewJobs).where(
                CrewJobs.job_key == "book_ingestion_crew"
            ).order_by(desc(CrewJobs.created_at)).limit(5)
        ).scalars().all()
        
        if not recent_jobs:
            logger.info("No book_ingestion_crew jobs found in database.")
            return
        
        for job in recent_jobs:
            logger.info(f"\nJob ID: {job.id}")
            logger.info(f"  Status: {job.status}")
            logger.info(f"  Queued at: {job.queued_at}")
            logger.info(f"  Started at: {job.started_at}")
            logger.info(f"  Finished at: {job.finished_at}")
            logger.info(f"  Payload: {json.dumps(job.payload, indent=2) if job.payload else 'None'}")
            
            # Check job notes which might contain result
            if job.notes:
                logger.info(f"  Notes: {job.notes[:200]}..." if len(job.notes) > 200 else f"  Notes: {job.notes}")
                # Check for transcription mentions in notes
                if "manuscript_transcriptions" in job.notes:
                    logger.info("  ✓ Notes mention manuscript_transcriptions")
                else:
                    logger.info("  ✗ Notes do NOT mention manuscript_transcriptions")
            else:
                logger.info(f"  Notes: None")
            
            if job.last_error:
                logger.error(f"  Last Error: {job.last_error}")
            
            # Check events for this job
            events = session.execute(
                select(CrewJobEvent).where(
                    CrewJobEvent.job_id == job.id
                ).order_by(CrewJobEvent.event_time)
            ).scalars().all()
            
            if events:
                logger.info(f"  Events ({len(events)} total):")
                # Look for specific events
                for event in events:
                    if "transcrib" in event.event_type.lower() or "save" in event.event_type.lower():
                        logger.info(f"    - {event.event_type}: {event.event_time}")
                        if event.event_data:
                            event_str = json.dumps(event.event_data)
                            if "manuscript_transcriptions" in event_str:
                                logger.info("      ✓ Event mentions manuscript_transcriptions")
                            if "error" in event_str.lower():
                                logger.error(f"      ✗ Event contains error: {event.event_data.get('error', 'Unknown')}")
                
                # Check for task-specific events
                task_events = [e for e in events if e.event_type == "TASK_EXECUTION"]
                if task_events:
                    logger.info(f"  Task Executions ({len(task_events)}):")
                    for te in task_events:
                        if te.event_data and 'task_name' in te.event_data:
                            logger.info(f"    - {te.event_data['task_name']}: {te.event_data.get('status', 'unknown')}")
            
            logger.info("-" * 40)
    
    # 2. Check what files are actually in Google Drive
    logger.info("\n2. FILES IN GOOGLE DRIVE:")
    logger.info("-" * 80)
    
    try:
        drive_tool = GoogleDriveTool()
        
        # List all .txt files
        result = drive_tool._run(
            folder_path=folder_path,
            client_user_id=client_user_id,
            file_types=["text/plain"],
            download=False
        )
        
        result_data = json.loads(result)
        if result_data["status"] == "success":
            files = result_data.get("files", [])
            
            tracking_files = []
            transcription_files = []
            
            for file in files:
                if "book_ingestion_crew_" in file['name'] and "manuscript_transcriptions_" not in file['name']:
                    tracking_files.append(file)
                elif "manuscript_transcriptions_" in file['name']:
                    transcription_files.append(file)
            
            logger.info(f"Total .txt files: {len(files)}")
            logger.info(f"Tracking files (book_ingestion_crew_*.txt): {len(tracking_files)}")
            logger.info(f"Transcription files (manuscript_transcriptions_*.txt): {len(transcription_files)}")
            
            if len(transcription_files) == 0:
                logger.info("\n⚠️  NO TRANSCRIPTION FILES FOUND!")
                logger.info("This confirms the issue - transcriptions are not being uploaded.")
            else:
                logger.info("\n✓ Some transcription files found:")
                for tf in transcription_files:
                    logger.info(f"  - {tf['name']} ({tf['size']} bytes)")
            
            # Match tracking files to jobs
            logger.info("\nMatching tracking files to jobs:")
            for tf in tracking_files:
                # Extract job ID from filename
                if "_crew_" in tf['name']:
                    parts = tf['name'].split('_crew_')
                    if len(parts) > 1:
                        job_id_part = parts[1].replace('.txt', '')
                        logger.info(f"  - {tf['name']} → Job ID: {job_id_part}")
                        
                        # Check if this job has a corresponding transcription file
                        matching_trans = [t for t in transcription_files if job_id_part in t['name']]
                        if matching_trans:
                            logger.info(f"    ✓ Has transcription file: {matching_trans[0]['name']}")
                        else:
                            logger.info(f"    ✗ NO transcription file found for this job")
        
    except Exception as e:
        logger.error(f"Error checking Google Drive: {e}")
    
    # 3. Diagnose the issue
    logger.info("\n3. DIAGNOSIS:")
    logger.info("-" * 80)
    
    logger.info("\nPOSSIBLE ISSUES:")
    logger.error("1. The 'transcribe_images' task may be failing or not producing proper JSON output")
    logger.info("2. The 'save_transcriptions' task may not be receiving the transcription data")
    logger.info("3. The context passing between tasks might be broken")
    logger.info("4. The o4-mini model might not be working correctly for multimodal transcription")
    logger.error("5. The simple_file_upload tool might be failing silently for large files")
    
    logger.info("\nRECOMMENDATIONS:")
    logger.error("1. Check crew execution logs for any errors in the transcribe_images task")
    logger.info("2. Verify that o4-mini model supports multimodal image viewing")
    logger.info("3. Add more detailed logging to the save_transcriptions task")
    logger.info("4. Test the simple_file_upload tool with larger content")
    logger.error("5. Consider adding error handling and retry logic")

if __name__ == "__main__":
    diagnose_book_ingestion_jobs()