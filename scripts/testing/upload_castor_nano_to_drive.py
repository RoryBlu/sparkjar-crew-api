#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Upload the castor nano chunked final results to Google Drive."""
import sys
from pathlib import Path

from .tools.google_drive_tool import GoogleDriveTool
import json

def main():
    drive_tool = GoogleDriveTool()
    
    # Upload parameters
    file_path = "/Users/r.t.rawlings/sparkjar-crew/services/crew-api/castor_nano_chunked_final.txt"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    file_name = "castor_nano_chunked_final.txt"
    
    logger.info(f"Uploading {file_name} to Google Drive...")
    logger.info(f"Folder path: {folder_path}")
    logger.info(f"Client user ID: {client_user_id}")
    
    # Use the upload_file method
    result = drive_tool.upload_file(
        folder_path=folder_path,
        client_user_id=client_user_id,
        file_path=file_path,
        file_name=file_name,
        mime_type="text/plain"
    )
    
    result_data = json.loads(result)
    
    if result_data.get('status') == 'success':
        logger.info(f"\n✅ Successfully uploaded!")
        logger.info(f"File ID: {result_data.get('file_id')}")
        logger.info(f"File name: {result_data.get('file_name')}")
        logger.info(f"File size: {result_data.get('size')} bytes")
        logger.info(f"Folder path: {result_data.get('folder_path')}")
    else:
        logger.error(f"\n❌ Upload failed: {result_data.get('error')}")
    
    drive_tool.cleanup()

if __name__ == "__main__":
    main()