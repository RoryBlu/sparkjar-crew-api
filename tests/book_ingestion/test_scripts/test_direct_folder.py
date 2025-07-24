#!/usr/bin/env python3
"""Test direct access to the book folder with 25 pages."""

import os
import json
import psycopg2
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment from .env file
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ.setdefault(key, value)

print("🔍 Testing Direct Access to Book Folder with 25 Pages")
print("=" * 70)

# Load request data for client_user_id
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)
client_user_id = request['request_data']['client_user_id']

# Get database connection
database_url = os.getenv('DATABASE_URL_DIRECT')
if database_url and 'postgresql+asyncpg://' in database_url:
    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')

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
creds_data = result[0]
cur.close()
conn.close()

# Initialize Google Drive
credentials = service_account.Credentials.from_service_account_info(
    creds_data,
    scopes=['https://www.googleapis.com/auth/drive']
)
service = build('drive', 'v3', credentials=credentials)

print("✅ Google Drive service initialized")

# Test the specific folder ID from the URL
folder_id = "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"

try:
    print(f"\n🔍 Testing direct access to folder: {folder_id}")
    
    # Get folder info (with shared drive support)
    folder_info = service.files().get(
        fileId=folder_id, 
        fields='id,name',
        supportsAllDrives=True
    ).execute()
    print(f"✅ Folder accessed: {folder_info.get('name')} (ID: {folder_info.get('id')})")
    
    # List all contents (with shared drive support)
    print(f"\n📁 Listing folder contents...")
    query = f"'{folder_id}' in parents"
    results = service.files().list(
        q=query,
        fields='files(id, name, mimeType, size)',
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    files = results.get('files', [])
    images = [f for f in files if 'image/' in f['mimeType']]
    other_files = [f for f in files if 'image/' not in f['mimeType']]
    
    print(f"✅ Found {len(files)} total items:")
    print(f"   🖼️  {len(images)} images")
    print(f"   📄 {len(other_files)} other files")
    
    if images:
        print(f"\n📋 Image files (expecting 25 pages):")
        for i, img in enumerate(images, 1):
            size = img.get('size', 'unknown')
            print(f"  {i:2d}. {img['name']} ({size} bytes)")
        
        if len(images) == 25:
            print(f"\n🎯 PERFECT! Found exactly 25 images as expected!")
        elif len(images) > 0:
            print(f"\n⚠️  Found {len(images)} images (expected 25)")
        
        print(f"\n✅ SUCCESS! Ready to run the book ingestion crew!")
        print(f"   📁 Folder ID: {folder_id}")
        print(f"   📖 Image count: {len(images)}")
        
        # Test command to run the crew
        print(f"\n🚀 Run the crew with:")
        print(f"   PYTHONPATH=/Users/r.t.rawlings/sparkjar-crew:/Users/r.t.rawlings/sparkjar-crew/services/crew-api/src python3.12 services/crew-api/src/crews/book_ingestion_crew/main.py google_drive --client_user_id 3a411a30-1653-4caf-acee-de257ff50e36 --google_drive_folder_path \"{folder_id}\" --language es")
    
    if other_files:
        print(f"\n📄 Other files:")
        for f in other_files:
            size = f.get('size', 'unknown')
            print(f"   - {f['name']} ({size} bytes)")
    
except Exception as e:
    print(f"\n❌ Cannot access folder: {e}")

print(f"\n🏁 Direct folder test completed")