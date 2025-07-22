#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Fixed test runner for Book Ingestion Crew with correct paths."""
import sys
from pathlib import Path
import json

# Add project root to path
crew_api_root = Path(__file__).parent / "services" / "crew-api" / "src"

from dotenv import load_dotenv
load_dotenv()

# Import the crew
from crews.book_ingestion_crew.crew import kickoff

def main():
    """Run the book ingestion pipeline with correct paths."""
    
    # FIXED: Use the correct Google Drive path that we know works
    inputs = {
        # This is the exact path that worked in our tests
        "google_drive_folder_path": "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
        "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
        "job_id": "test-nano-chunked-ocr",
        "confidence_threshold": 0.85,
        "max_retries": 2,
        "language": "es"  # Spanish
    }
    
    logger.info("Book Ingestion Crew - Fixed Configuration")
    logger.info("=" * 50)
    logger.info(f"Folder path: {inputs['google_drive_folder_path']}")
    logger.info(f"Client user: {inputs['client_user_id']}")
    logger.info(f"Output file: {inputs['job_id']}.txt")
    logger.info(f"Language: {inputs['language']}")
    logger.info("\nStarting with CORRECT path...\n")
    
    try:
        result = kickoff(inputs)
        
        # Pretty print result
        if isinstance(result, dict):
            logger.info("\n✅ Result:")
            logger.info(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("status") == "success":
                logger.info(f"\n✓ Success! Text saved to: {result.get('output_file')}")
                logger.info(f"Google File ID: {result.get('google_file_id')}")
                logger.info(f"Text length: {result.get('text_length')} characters")
            else:
                logger.info(f"\n⚠ Issue: {result.get('message')}")
    
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()