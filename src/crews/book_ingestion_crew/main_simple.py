#!/usr/bin/env python
"""
Simple page processing - minimal test without complex tools
"""
import sys
import os
import logging
import argparse
import time

from crew_simple import kickoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Simple Page Processing Test')
    parser.add_argument('--client_user_id', type=str, required=True)
    parser.add_argument('--google_drive_folder_path', type=str, required=True)
    parser.add_argument('--language', type=str, default='es')
    
    args = parser.parse_args()
    
    inputs = {
        "client_user_id": args.client_user_id,
        "google_drive_folder_path": args.google_drive_folder_path,
        "language": args.language
    }
    
    logger.info("Starting SIMPLE page processing test")
    logger.info(f"Processing folder: {args.google_drive_folder_path}")
    
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