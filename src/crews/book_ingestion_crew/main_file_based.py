#!/usr/bin/env python
"""
Main entry point for testing the File-Based Book Ingestion Crew locally.
This version processes files from a list instead of requiring page numbers.

Usage: python main_file_based.py google_drive --client_user_id <UUID> --google_drive_folder_path <PATH> --language <LANG>
"""

import sys
import os
import logging
import argparse
import time
from datetime import datetime

# Import the file-based crew
from crew_file_based import kickoff

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

# Get the main logger
logger = logging.getLogger('openai')

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test Book Ingestion Crew')
    parser.add_argument('mode', choices=['test', 'google_drive'], 
                       help='Test mode or Google Drive mode')
    parser.add_argument('--job_id', type=str, default=f"test-{int(time.time())}",
                       help='Job ID for tracking')
    parser.add_argument('--google_drive_folder_path', type=str,
                       help='Google Drive folder path or ID')
    parser.add_argument('--language', type=str, default='en',
                       choices=['en', 'es', 'fr', 'de', 'it'],
                       help='Language for OCR')
    parser.add_argument('--client_user_id', type=str,
                       help='Client user ID for Google Drive access')
    
    args = parser.parse_args()
    
    # Build test inputs
    if args.mode == 'test':
        test_inputs = {
            "job_id": args.job_id,
            "job_key": "book_ingestion_crew",
            "google_drive_folder_path": "test_folder",
            "language": "en",
            "client_user_id": "test-client-user",
            "actor_type": "user",
            "actor_id": "test-user",
            "book_metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "year": 2024,
                "description": "A test book for crew testing"
            },
            "confidence_threshold": 0.85
        }
    else:
        # Google Drive mode
        if not args.client_user_id or not args.google_drive_folder_path:
            parser.error("Google Drive mode requires --client_user_id and --google_drive_folder_path")
        
        test_inputs = {
            "job_id": args.job_id,
            "job_key": "book_ingestion_crew",
            "google_drive_folder_path": args.google_drive_folder_path,
            "language": args.language,
            "client_user_id": args.client_user_id,
            "actor_type": "user",
            "actor_id": "test-user",
            "book_metadata": {
                "title": "Castor Gonzalez - Book 1",
                "author": "Castor Gonzalez", 
                "year": 2006,
                "description": "Spanish manuscript written in 2006"
            },
            "confidence_threshold": 0.90
        }
    
    logger.info("\n" + "="*80)
    logger.info("FILE-BASED BOOK INGESTION CREW - LOCAL TEST")
    logger.info("="*80 + "\n")
    
    logger.info(f"Test inputs: {test_inputs}\n")
    
    logger.info("Starting crew execution...\n")
    
    try:
        # Run the crew
        start_time = time.time()
        result = kickoff(test_inputs)
        end_time = time.time()
        
        logger.info(f"\n{'='*80}")
        logger.info("CREW EXECUTION COMPLETED")
        logger.info(f"{'='*80}\n")
        
        logger.info(f"Execution time: {end_time - start_time:.2f} seconds")
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result: {result}")
        
        # Print summary if available
        if isinstance(result, dict):
            logger.info(f"\n📊 SUMMARY:")
            logger.info(f"  Total files: {result.get('total_files', 0)}")
            logger.info(f"  Processed successfully: {result.get('processed_successfully', 0)}")
            logger.info(f"  Failed: {result.get('failed', 0)}")
            logger.info(f"  Average confidence: {result.get('average_confidence', 0):.2%}")
        
    except Exception as e:
        logger.error(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()