#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Upload the nano chunked final results to Google Drive."""
import sys
from pathlib import Path

from .tools.google_drive_tool import GoogleDriveTool
import json

def main():
    drive_tool = GoogleDriveTool()
    
    # Upload the nano chunked final results
    file_path = "castor_nano_chunked_final.txt"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    
    logger.info(f"Uploading {file_path} to Google Drive...")
    
    result = drive_tool._run(
        action="upload",
        file_path=file_path,
        folder_path=folder_path,
        client_user_id=client_user_id
    )
    
    result_data = json.loads(result)
    
    if result_data.get('status') == 'success':
        logger.info(f"✅ Successfully uploaded!")
        logger.info(f"File ID: {result_data.get('file_id')}")
        logger.info(f"File name: {result_data.get('file_name')}")
        logger.info(f"File size: {result_data.get('file_size')} bytes")
    else:
        logger.error(f"❌ Upload failed: {result_data.get('error')}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()