#!/usr/bin/env python3
"""Upload OCR results to Google Drive."""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from .tools.google_drive_tool import GoogleDriveTool
import json

def main():
    """Upload OCR results to Google Drive."""
    client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"
    folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
    
    # File to upload
    local_file = "castor_ocr_tool_results.txt"
    
    if not Path(local_file).exists():
        print(f"File not found: {local_file}")
        return
    
    print(f"Uploading {local_file} to Google Drive...")
    print(f"Destination: {folder_path}")
    print(f"Client User ID: {client_user_id}")
    
    # Upload file
    drive_tool = GoogleDriveTool()
    result = drive_tool.upload_file(
        folder_path=folder_path,
        client_user_id=client_user_id,
        file_path=local_file,
        file_name="castor_ocr_tool_results.txt",
        mime_type="text/plain"
    )
    
    # Check result
    data = json.loads(result)
    if data.get('status') == 'success':
        print(f"\n✅ Upload successful!")
        print(f"   File ID: {data.get('file_id')}")
        print(f"   File name: {data.get('file_name')}")
        print(f"   Size: {data.get('size')} bytes")
        print(f"\nThe OCR results are now available in Google Drive!")
    else:
        print(f"\n❌ Upload failed: {data.get('error')}")

if __name__ == "__main__":
    main()