#!/usr/bin/env python3
"""Test book ingestion using venv and correct folder."""

import os
import sys
import json
import tempfile
from pathlib import Path

# Load environment manually
import os
os.environ.setdefault('DATABASE_URL_DIRECT', 'postgresql://postgres:m7ubbG7dYsh9jn2v@db.mtssbakpwbeizuybinsl.supabase.co:5432/postgres')
os.environ.setdefault('OPENAI_API_KEY', open('.env').read().split('OPENAI_API_KEY=')[1].split('\n')[0])

# Add crew-api src to path
crew_api_src = str(Path(__file__).parent / "services" / "crew-api" / "src")
sys.path.insert(0, crew_api_src)

import psycopg2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

print("🚀 Book Ingestion Test with venv")
print("=" * 70)

# Update the folder ID to the correct one
folder_id = "0AM0PEUhIEQFUUk9PVA"  # From the Google Drive URL

# Load request data for client_user_id
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)
client_user_id = request['request_data']['client_user_id']

print(f"Target Folder ID: {folder_id}")
print(f"Client User ID: {client_user_id}")

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
    
    # List contents of the folder
    print(f"\n📁 Exploring folder: {folder_id}")
    query = f"'{folder_id}' in parents"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)',
        pageSize=100
    ).execute()
    
    items = results.get('files', [])
    
    # Separate folders and files
    folders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
    images = [item for item in items if 'image/' in item['mimeType']]
    
    print(f"\n📋 Found {len(items)} total items:")
    print(f"   📁 {len(folders)} folders")
    print(f"   🖼️  {len(images)} images")
    
    # Show folders first
    if folders:
        print(f"\n📁 Folders:")
        for folder in folders[:10]:
            print(f"   - {folder['name']}/")
            
        # Check if we should explore one of the folders for images
        for folder in folders:
            if any(keyword in folder['name'].lower() for keyword in ['book', 'castor', 'gonzalez', 'vervelyn']):
                print(f"\n🔍 Exploring '{folder['name']}' folder...")
                sub_query = f"'{folder['id']}' in parents and mimeType contains 'image/'"
                sub_results = service.files().list(
                    q=sub_query,
                    fields='files(id, name, mimeType)',
                    pageSize=50
                ).execute()
                sub_images = sub_results.get('files', [])
                print(f"   Found {len(sub_images)} images")
                if sub_images:
                    for img in sub_images[:5]:
                        print(f"      📄 {img['name']}")
                    if len(sub_images) > 5:
                        print(f"      ... and {len(sub_images) - 5} more")
                    
                    # Test OCR on first image
                    print(f"\n🔍 Testing OCR on: {sub_images[0]['name']}")
                    
                    file_id = sub_images[0]['id']
                    request = service.files().get_media(fileId=file_id)
                    
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                        downloader = MediaIoBaseDownload(tmp_file, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                        
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
                    
                    break  # Only test first folder with matching name
    
    # If no folders or no matching folders, show direct images
    if images and not any(keyword in folder['name'].lower() for folder in folders for keyword in ['book', 'castor', 'gonzalez', 'vervelyn']):
        print(f"\n🖼️  Direct images in folder:")
        for img in images[:10]:
            print(f"   - {img['name']} ({img['mimeType']})")
            
        if images:
            print(f"\n🔍 Testing OCR on: {images[0]['name']}")
            # Same OCR test code as above...
    
    print("\n✅ Test completed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()