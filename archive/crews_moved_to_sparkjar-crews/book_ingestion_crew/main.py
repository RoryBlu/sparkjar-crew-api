#!/usr/bin/env python
"""
Main entry point for testing the Book Ingestion Crew locally.
Usage: python main.py
"""

import sys
import os
import logging
import argparse
import time
from datetime import datetime

# Add the parent directory to the path so we can import from src

from crew import kickoff

# Configure logging to be VERY verbose
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set all loggers to DEBUG level
for logger_name in ['__main__', 'crew', 'crewai', 'openai']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

def main():
    """Run the book ingestion crew with test data."""
    parser = argparse.ArgumentParser(description='Test Book Ingestion Crew')
    parser.add_argument('mode', choices=['test', 'google_drive'], 
                        help='Run mode: test (dummy data) or google_drive (real data)')
    parser.add_argument('--job_id', help='Job ID', default=f'test-{int(time.time())}')
    parser.add_argument('--google_drive_folder_path', help='Google Drive folder path')
    parser.add_argument('--language', help='Language for OCR', default='en')
    parser.add_argument('--client_user_id', help='Client user ID')
    
    args = parser.parse_args()
    
    logger.info("\n" + "=" * 80)
    logger.info("BOOK INGESTION CREW - LOCAL TEST")
    logger.info("=" * 80 + "\n")
    
    if args.mode == 'google_drive':
        # Use real Google Drive data
        test_inputs = {
            "job_id": args.job_id,
            "job_key": "book_ingestion_crew",
            "google_drive_folder_path": args.google_drive_folder_path,
            "language": args.language,
            "client_user_id": args.client_user_id,
            "actor_type": "user",
            "actor_id": "test-user"
        }
    else:
        # Use test data
        test_inputs = {
            "job_id": "test-job-123",
            "job_key": "book_ingestion_crew",
            "client_user_id": "test-client",
            "actor_type": "user",
            "actor_id": "test-user",
            "book_title": "Test Book",
            "book_content": "This is a test book content for ingestion.",
            "metadata": {
                "source": "local_test",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    logger.info(f"Test inputs: {test_inputs}\n")
    
    try:
        logger.info("Starting crew execution...\n")
        result = kickoff(test_inputs)
        
        logger.info("\n" + "=" * 80)
        logger.info("EXECUTION RESULT:")
        logger.info("=" * 80)
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Result: {result.get('result')}")
        if result.get('error'):
            logger.error(f"Error: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()