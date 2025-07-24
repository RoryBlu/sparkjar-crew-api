#!/usr/bin/env python
"""Test Google Drive file listing."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

from tools.google_drive_tool import GoogleDriveTool
import json

def test_drive_listing():
    """Test listing files from Google Drive."""
    client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"
    folder_id = "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"
    
    print("📁 Testing Google Drive file listing...")
    print("=" * 60)
    
    drive_tool = GoogleDriveTool()
    
    # List files
    result = drive_tool._run(
        folder_path=folder_id,
        client_user_id=client_user_id
    )
    
    # Parse result
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            print(f"Raw result: {result}")
            return
    
    print(f"Result type: {type(result)}")
    print(f"Status: {result.get('status')}")
    
    if result.get("status") == "success":
        files = result.get("files", [])
        print(f"\n✅ Found {len(files)} files")
        
        # Show structure of first file
        if files:
            print(f"\nFirst file structure:")
            first_file = files[0]
            for key, value in first_file.items():
                print(f"  {key}: {value}")
            
            # Count PNG files
            png_files = [f for f in files if f.get('name', '').endswith('.png')]
            print(f"\n📄 PNG files: {len(png_files)}")
            
            # Show first 5 PNG files
            for i, f in enumerate(png_files[:5]):
                print(f"  {i+1}. {f.get('name', 'unknown')}")

if __name__ == "__main__":
    test_drive_listing()