#!/usr/bin/env python3
"""Direct test of book OCR functionality."""

import os
import sys
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Load environment
load_dotenv()

print("🚀 Direct Book OCR Test")
print("=" * 70)

# Load request data
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)
request_data = request['request_data']

client_user_id = request_data['client_user_id']
folder_path = request_data['google_drive_folder_path']

# Get database connection
database_url = os.getenv('DATABASE_URL_DIRECT')
if database_url:
    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')

try:
    # Get Google credentials
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT cs.secrets_metadata
        FROM client_secrets cs
        JOIN client_users cu ON cu.clients_id = cs.client_id
        WHERE cu.id = %s AND cs.secret_key = 'googleapis.service_account'
    """, (client_user_id,))
    
    result = cur.fetchone()
    if not result or not result[0]:
        print("❌ No Google credentials found")
        exit(1)
    
    creds_data = result[0]
    cur.close()
    conn.close()
    
    # Initialize Google Drive
    credentials = service_account.Credentials.from_service_account_info(
        creds_data,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    service = build('drive', 'v3', credentials=credentials)
    print("✅ Google Drive service initialized")
    
    # Find the folder by navigating the path
    print(f"\n📁 Looking for folder: {folder_path}")
    
    # Start from root and navigate the path
    path_parts = [p for p in folder_path.strip('/').split('/') if p]
    current_parent = 'root'
    folder_id = None
    
    for part in path_parts:
        print(f"   Searching for: {part}")
        query = f"name = '{part}' and mimeType = 'application/vnd.google-apps.folder' and '{current_parent}' in parents"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        if not folders:
            print(f"❌ Folder '{part}' not found under parent {current_parent}")
            # Try without parent restriction
            query = f"name = '{part}' and mimeType = 'application/vnd.google-apps.folder'"
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, parents)'
            ).execute()
            folders = results.get('files', [])
            if folders:
                print(f"   Found {len(folders)} folders named '{part}'")
                folder_id = folders[0]['id']
                current_parent = folder_id
            else:
                exit(1)
        else:
            folder_id = folders[0]['id']
            current_parent = folder_id
            print(f"   ✅ Found: {folders[0]['name']} (ID: {folder_id})")
    
    if not folder_id:
        print("❌ Could not find target folder")
        exit(1)
    
    # List images in the folder
    query = f"'{folder_id}' in parents and (mimeType contains 'image/')"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)',
        orderBy='name'
    ).execute()
    
    files = results.get('files', [])
    print(f"\n📋 Found {len(files)} images:")
    for i, file in enumerate(files[:5]):
        print(f"  {i+1}. {file['name']} ({file['mimeType']})")
    
    if files:
        # Download first image for testing
        print(f"\n📥 Downloading first image: {files[0]['name']}")
        
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            downloader = MediaIoBaseDownload(tmp_file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"   Download {int(status.progress() * 100)}%")
            
            tmp_path = tmp_file.name
            print(f"✅ Downloaded to: {tmp_path}")
        
        # Test OCR with OpenAI
        print("\n🔍 Testing OCR with GPT-4o...")
        import base64
        import openai
        
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Read and encode image
        with open(tmp_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Create OCR request
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please transcribe the handwritten Spanish text in this image. Return ONLY the transcribed text, preserving line breaks and formatting."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }],
            temperature=0.1,
            max_tokens=1000
        )
        
        transcription = response.choices[0].message.content
        print("\n📝 Transcription:")
        print("-" * 50)
        print(transcription)
        print("-" * 50)
        
        # Clean up
        os.unlink(tmp_path)
        print("\n✅ Test completed successfully!")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()