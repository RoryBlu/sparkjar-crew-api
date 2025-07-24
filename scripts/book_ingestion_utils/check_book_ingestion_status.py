#!/usr/bin/env python3
"""
Utility to check book ingestion job status and database records.
Consolidates functionality from multiple check scripts.
"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_crew_jobs(job_key="book_ingestion_crew", limit=10):
    """Check recent crew jobs for book ingestion."""
    engine = create_engine(os.getenv('DATABASE_URL_DIRECT'))
    
    with engine.connect() as conn:
        # Get recent jobs
        result = conn.execute(text("""
            SELECT id, status, queued_at, started_at, finished_at, 
                   last_error, payload
            FROM crew_jobs
            WHERE job_key = :job_key
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"job_key": job_key, "limit": limit})
        
        jobs = []
        for row in result:
            job = {
                "id": str(row[0]),
                "status": row[1],
                "queued_at": row[2],
                "started_at": row[3],
                "finished_at": row[4],
                "error": row[5],
                "payload": row[6]
            }
            jobs.append(job)
        
        return jobs

def check_job_events(job_id):
    """Check events for a specific job."""
    engine = create_engine(os.getenv('DATABASE_URL_DIRECT'))
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT event_type, event_data, event_time
            FROM crew_job_event
            WHERE job_id = :job_id
            ORDER BY event_time
        """), {"job_id": job_id})
        
        events = []
        for row in result:
            events.append({
                "type": row[0],
                "data": row[1],
                "time": row[2]
            })
        
        return events

def check_ingested_pages(book_key=None, limit=10):
    """Check ingested pages in the database."""
    engine = create_engine(os.getenv('DATABASE_URL_DIRECT'))
    
    with engine.connect() as conn:
        query = """
            SELECT book_key, page_number, file_name, 
                   LENGTH(page_text) as text_length,
                   ocr_metadata->>'confidence' as confidence,
                   created_at
            FROM "BookIngestions"
        """
        params = {"limit": limit}
        
        if book_key:
            query += " WHERE book_key = :book_key"
            params["book_key"] = book_key
            
        query += " ORDER BY created_at DESC LIMIT :limit"
        
        result = conn.execute(text(query), params)
        
        pages = []
        for row in result:
            pages.append({
                "book_key": row[0],
                "page_number": row[1],
                "file_name": row[2],
                "text_length": row[3],
                "confidence": row[4],
                "created_at": row[5]
            })
        
        return pages

def check_book_summary(book_key):
    """Get summary statistics for a book."""
    engine = create_engine(os.getenv('DATABASE_URL_DIRECT'))
    
    with engine.connect() as conn:
        # Get page count and stats
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_pages,
                MIN(page_number) as first_page,
                MAX(page_number) as last_page,
                AVG(LENGTH(page_text)) as avg_text_length,
                AVG((ocr_metadata->>'confidence')::float) as avg_confidence
            FROM "BookIngestions"
            WHERE book_key = :book_key
        """), {"book_key": book_key})
        
        stats = result.fetchone()
        
        return {
            "book_key": book_key,
            "total_pages": stats[0],
            "first_page": stats[1],
            "last_page": stats[2],
            "avg_text_length": float(stats[3]) if stats[3] else 0,
            "avg_confidence": float(stats[4]) if stats[4] else 0
        }

def main():
    """Main function to run checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check book ingestion status")
    parser.add_argument("--jobs", action="store_true", help="List recent jobs")
    parser.add_argument("--job-id", help="Check specific job events")
    parser.add_argument("--pages", action="store_true", help="List recent pages")
    parser.add_argument("--book-key", help="Filter by book key")
    parser.add_argument("--summary", action="store_true", help="Get book summary")
    parser.add_argument("--limit", type=int, default=10, help="Number of records")
    
    args = parser.parse_args()
    
    if args.jobs:
        print("\n📚 Recent Book Ingestion Jobs:")
        print("=" * 80)
        jobs = check_crew_jobs(limit=args.limit)
        for job in jobs:
            print(f"Job ID: {job['id']}")
            print(f"Status: {job['status']}")
            print(f"Started: {job['started_at']}")
            if job['error']:
                print(f"Error: {job['error']}")
            print("-" * 40)
    
    if args.job_id:
        print(f"\n📊 Events for Job {args.job_id}:")
        print("=" * 80)
        events = check_job_events(args.job_id)
        for event in events:
            print(f"[{event['time']}] {event['type']}")
            if event['data'] and 'step_data' in event['data']:
                step = event['data']['step_data']
                if 'message' in step:
                    print(f"  Message: {step['message']}")
    
    if args.pages:
        print("\n📄 Recent Ingested Pages:")
        print("=" * 80)
        pages = check_ingested_pages(args.book_key, args.limit)
        for page in pages:
            print(f"Page {page['page_number']}: {page['file_name']}")
            print(f"  Text length: {page['text_length']}")
            print(f"  Confidence: {page['confidence']}")
            print(f"  Book: {page['book_key']}")
            print("-" * 40)
    
    if args.summary and args.book_key:
        print(f"\n📈 Summary for {args.book_key}:")
        print("=" * 80)
        summary = check_book_summary(args.book_key)
        print(f"Total pages: {summary['total_pages']}")
        print(f"Page range: {summary['first_page']} - {summary['last_page']}")
        print(f"Avg text length: {summary['avg_text_length']:.0f} chars")
        print(f"Avg confidence: {summary['avg_confidence']:.2f}")

if __name__ == "__main__":
    main()