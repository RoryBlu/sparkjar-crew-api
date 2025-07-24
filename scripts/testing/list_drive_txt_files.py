#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""List all .txt files in a specific Google Drive folder."""

import json
import sys
import os
from pathlib import Path

# Add the src directory to the Python path

from .tools.google_drive_tool import GoogleDriveTool

def list_txt_files_in_folder():
    """List all .txt files in the specified Google Drive folder."""
    
    # Configuration
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    
    logger.info(f"Listing .txt files in Google Drive folder:")
    logger.info(f"  Folder: {folder_path}")
    logger.info(f"  Client User ID: {client_user_id}")
    logger.info("-" * 80)
    
    try:
        # Initialize the tool
        tool = GoogleDriveTool()
        
        # List .txt files only (don't download)
        result = tool._run(
            folder_path=folder_path,
            client_user_id=client_user_id,
            file_types=["text/plain"],  # MIME type for .txt files
            download=False  # Just list, don't download
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        if result_data["status"] == "success":
            files = result_data.get("files", [])
            
            if files:
                logger.info(f"\nFound {len(files)} .txt file(s):")
                logger.info("-" * 80)
                
                for idx, file in enumerate(files, 1):
                    logger.info(f"\n{idx}. {file['name']}")
                    logger.info(f"   File ID: {file['file_id']}")
                    logger.info(f"   Size: {file['size']:,} bytes")
                    logger.info(f"   Created: {file['created']}")
                    logger.info(f"   Modified: {file['modified']}")
                    logger.info(f"   MIME Type: {file['mime_type']}")
            else:
                logger.info("\nNo .txt files found in the folder.")
                
                # Let's also check for all files to see what's there
                logger.info("\nListing ALL files in the folder to see what's available...")
                all_files_result = tool._run(
                    folder_path=folder_path,
                    client_user_id=client_user_id,
                    file_types=[],  # No filter - get all files
                    download=False
                )
                
                all_data = json.loads(all_files_result)
                if all_data["status"] == "success" and all_data.get("files"):
                    logger.info(f"\nFound {len(all_data['files'])} total files:")
                    for idx, file in enumerate(all_data['files'][:10], 1):  # Show first 10
                        logger.info(f"{idx}. {file['name']} ({file['mime_type']})")
                    if len(all_data['files']) > 10:
                        logger.info(f"... and {len(all_data['files']) - 10} more files")
        else:
            logger.error(f"\nError: {result_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up if needed
        if hasattr(tool, 'cleanup'):
            tool.cleanup()

if __name__ == "__main__":
    list_txt_files_in_folder()