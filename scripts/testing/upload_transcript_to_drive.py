#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Upload the transcript to Google Drive."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from .tools.google_drive_tool import GoogleDriveTool
import json

def main():
    """Upload transcript to Google Drive."""
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    # File to upload
    local_file = "castor_manuscript_final.txt"
    
    if not Path(local_file).exists():
        logger.info(f"File not found: {local_file}")
        return
    
    logger.info(f"Uploading {local_file} to Google Drive...")
    logger.info(f"Destination: {folder_path}")
    
    # Upload file
    drive_tool = GoogleDriveTool()
    result = drive_tool.upload_file(
        folder_path=folder_path,
        client_user_id=client_user_id,
        file_path=local_file,
        file_name="castor_book1_transcript.txt",
        mime_type="text/plain"
    )
    
    # Check result
    data = json.loads(result)
    if data.get('status') == 'success':
        logger.info(f"\n✅ Upload successful!")
        logger.info(f"   File ID: {data.get('file_id')}")
        logger.info(f"   File name: {data.get('file_name')}")
        logger.info(f"   Size: {data.get('size')} bytes")
        logger.info(f"\nThe transcript is now available in Google Drive!")
    else:
        logger.error(f"\n❌ Upload failed: {data.get('error')}")

if __name__ == "__main__":
    main()