#!/usr/bin/env python3
"""
Real-time monitor for book ingestion jobs.
Consolidates monitoring functionality.
"""

import os
import sys
import time
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def monitor_job(job_id, interval=2):
    """Monitor a job in real-time."""
    engine = create_engine(os.getenv('DATABASE_URL_DIRECT'))
    
    print(f"\n📊 Monitoring job {job_id}...")
    print("=" * 80)
    
    last_event_count = 0
    start_time = time.time()
    
    while True:
        with engine.connect() as conn:
            # Get job status
            job_result = conn.execute(text("""
                SELECT status, started_at, finished_at, last_error
                FROM crew_jobs
                WHERE id = :job_id
            """), {"job_id": job_id}).fetchone()
            
            if not job_result:
                print("❌ Job not found")
                break
            
            status, started_at, finished_at, error = job_result
            
            # Get events
            event_result = conn.execute(text("""
                SELECT event_type, event_data, event_time
                FROM crew_job_event
                WHERE job_id = :job_id
                ORDER BY event_time
            """), {"job_id": job_id}).fetchall()
            
            # Show new events
            if len(event_result) > last_event_count:
                for event in event_result[last_event_count:]:
                    event_type, event_data, event_time = event
                    print(f"[{event_time}] {event_type}")
                    
                    if event_data and 'step_data' in event_data:
                        step = event_data['step_data']
                        if 'message' in step:
                            print(f"  {step['message']}")
                        if 'error' in step:
                            print(f"  ❌ Error: {step['error']}")
                        if 'task' in step:
                            print(f"  Task: {step['task']}")
                
                last_event_count = len(event_result)
            
            # Update status line
            elapsed = time.time() - start_time
            status_line = f"\rStatus: {status} | Events: {len(event_result)} | Elapsed: {elapsed:.0f}s"
            print(status_line, end='', flush=True)
            
            # Check if complete
            if status in ['completed', 'failed']:
                print("\n" + "=" * 80)
                
                if status == 'completed':
                    print("✅ Job completed successfully!")
                    # Get ingested pages count
                    pages_result = conn.execute(text("""
                        SELECT COUNT(*) FROM "BookIngestions"
                        WHERE created_at >= :started_at
                    """), {"started_at": started_at}).scalar()
                    print(f"📄 Pages ingested: {pages_result}")
                else:
                    print(f"❌ Job failed: {error}")
                
                break
            
            time.sleep(interval)

def monitor_ingestion_progress(book_key, interval=5):
    """Monitor ongoing ingestion progress for a book."""
    engine = create_engine(os.getenv('DATABASE_URL_DIRECT'))
    
    print(f"\n📚 Monitoring ingestion for {book_key}...")
    print("=" * 80)
    
    last_page_count = 0
    
    while True:
        with engine.connect() as conn:
            # Get current stats
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_pages,
                    MAX(page_number) as last_page,
                    MAX(created_at) as last_update
                FROM "BookIngestions"
                WHERE book_key = :book_key
            """), {"book_key": book_key}).fetchone()
            
            total_pages, last_page, last_update = result
            
            if total_pages > last_page_count:
                # Get recent pages
                recent = conn.execute(text("""
                    SELECT page_number, file_name, 
                           LENGTH(page_text) as text_length
                    FROM "BookIngestions"
                    WHERE book_key = :book_key
                    ORDER BY created_at DESC
                    LIMIT :limit
                """), {"book_key": book_key, "limit": total_pages - last_page_count})
                
                for page in recent:
                    print(f"✅ Page {page[0]}: {page[1]} ({page[2]} chars)")
                
                last_page_count = total_pages
            
            # Status line
            status_line = f"\rTotal pages: {total_pages} | Last page: {last_page} | Last update: {last_update}"
            print(status_line, end='', flush=True)
            
            # Check if no updates for 30 seconds
            if last_update:
                seconds_since_update = (datetime.utcnow() - last_update).total_seconds()
                if seconds_since_update > 30:
                    print("\n⏸️  No updates for 30 seconds, monitoring stopped")
                    break
            
            time.sleep(interval)

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor book ingestion")
    parser.add_argument("--job-id", help="Monitor specific job")
    parser.add_argument("--book-key", help="Monitor book ingestion progress")
    parser.add_argument("--interval", type=int, default=2, help="Update interval")
    
    args = parser.parse_args()
    
    if args.job_id:
        monitor_job(args.job_id, args.interval)
    elif args.book_key:
        monitor_ingestion_progress(args.book_key, args.interval)
    else:
        print("Please specify --job-id or --book-key")

if __name__ == "__main__":
    main()