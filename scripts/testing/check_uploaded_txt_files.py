#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Download and examine the content of uploaded .txt files from Google Drive."""

import json
import sys
import os
from pathlib import Path

# Add the src directory to the Python path

from .tools.google_drive_tool import GoogleDriveTool

def check_uploaded_txt_files():
    """Download and examine all .txt files to see their actual content."""
    
    # Configuration
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    
    logger.info(f"Downloading and examining .txt files from Google Drive:")
    logger.info(f"  Folder: {folder_path}")
    logger.info(f"  Client User ID: {client_user_id}")
    logger.info("=" * 80)
    
    try:
        # Initialize the tool
        tool = GoogleDriveTool()
        
        # List and download .txt files
        result = tool._run(
            folder_path=folder_path,
            client_user_id=client_user_id,
            file_types=["text/plain"],  # MIME type for .txt files
            download=True  # Download the files
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        if result_data["status"] == "success":
            files = result_data.get("files", [])
            
            if files:
                logger.info(f"\nFound and downloaded {len(files)} .txt file(s):")
                logger.info("=" * 80)
                
                for idx, file in enumerate(files, 1):
                    logger.info(f"\n{idx}. FILE: {file['name']}")
                    logger.info(f"   Size: {file['size']:,} bytes")
                    logger.info(f"   Created: {file['created']}")
                    logger.info(f"   Modified: {file['modified']}")
                    
                    # Check if download was successful
                    if file.get('download_status') == 'success' and 'local_path' in file:
                        local_path = file['local_path']
                        logger.info(f"   Local path: {local_path}")
                        
                        # Read and display file content
                        try:
                            with open(local_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            logger.info(f"\n   CONTENT ({len(content)} characters):")
                            logger.info("   " + "-" * 76)
                            
                            # Show the content (limit to first 1000 chars if too long)
                            if len(content) > 1000:
                                logger.info(f"   {content[:1000]}...")
                                logger.info(f"   ... (truncated, showing first 1000 of {len(content)} characters)")
                            else:
                                # Show full content with indentation
                                for line in content.split('\n'):
                                    logger.info(f"   {line}")
                            
                            logger.info("   " + "-" * 76)
                            
                            # Analyze what type of file this is
                            logger.info("\n   ANALYSIS:")
                            if "book_ingestion_crew_" in file['name']:
                                if "manuscript_transcriptions_" in content:
                                    logger.info("   ✓ This is a TRACKING file (references manuscript transcriptions)")
                                elif len(content) > 1000:
                                    logger.info("   ✓ This could be a TRANSCRIPTION file (large content)")
                                else:
                                    logger.info("   ? This appears to be a TRACKING file (small size)")
                                    
                                # Check if it mentions manuscript_transcriptions file
                                if "manuscript_transcriptions_" in content:
                                    import re
                                    pattern = r'manuscript_transcriptions_[a-f0-9\-]+\.txt'
                                    matches = re.findall(pattern, content)
                                    if matches:
                                        logger.info(f"   → References transcription file: {matches[0]}")
                                    
                        except Exception as e:
                            logger.error(f"   ERROR reading file: {e}")
                    else:
                        logger.error(f"   Download failed: {file.get('download_error', 'Unknown error')}")
                    
                    logger.info("=" * 80)
                
                # Summary
                logger.info("\nSUMMARY:")
                logger.info("-" * 80)
                tracking_files = [f for f in files if f['size'] < 500]
                possible_transcriptions = [f for f in files if f['size'] > 1000]
                
                logger.info(f"Total .txt files found: {len(files)}")
                logger.info(f"Small files (likely tracking): {len(tracking_files)}")
                logger.info(f"Large files (possible transcriptions): {len(possible_transcriptions)}")
                
                if len(tracking_files) > 0 and len(possible_transcriptions) == 0:
                    logger.warning("\n⚠️  WARNING: Only tracking files found, no transcription files!")
                    logger.info("The manuscript transcriptions may not have been uploaded.")
                
            else:
                logger.info("\nNo .txt files found in the folder.")
                
        else:
            logger.error(f"\nError: {result_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temporary files
        if hasattr(tool, 'cleanup'):
            tool.cleanup()

if __name__ == "__main__":
    check_uploaded_txt_files()