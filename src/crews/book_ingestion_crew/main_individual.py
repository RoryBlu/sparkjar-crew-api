#!/usr/bin/env python
"""
Individual page processing main - Process pages one by one using kickoff_for_each
"""
import sys
import os
import logging
import argparse
import time

from crew_individual import kickoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Individual Page Book Ingestion')
    parser.add_argument('--client_user_id', type=str, required=True)
    parser.add_argument('--google_drive_folder_path', type=str, required=True)
    parser.add_argument('--language', type=str, default='es')
    parser.add_argument('--confidence_threshold', type=float, default=0.85)
    
    args = parser.parse_args()
    
    inputs = {
        "job_id": f"individual-test-{int(time.time())}",
        "job_key": "book_ingestion_crew",
        "client_user_id": args.client_user_id,
        "google_drive_folder_path": args.google_drive_folder_path,
        "language": args.language,
        "confidence_threshold": args.confidence_threshold,
        "actor_type": "user",
        "actor_id": "test-user",
        "book_metadata": {
            "title": "Castor Gonzalez - Book 1",
            "author": "Castor Gonzalez",
            "year": 2006,
            "description": "Spanish manuscript written in 2006"
        }
    }
    
    logger.info("Starting INDIVIDUAL page processing book ingestion crew")
    logger.info(f"Processing folder: {args.google_drive_folder_path}")
    logger.info("Using kickoff_for_each to process pages one at a time")
    
    try:
        start_time = time.time()
        result = kickoff(inputs)
        end_time = time.time()
        
        logger.info(f"\nExecution time: {end_time - start_time:.2f} seconds")
        logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()