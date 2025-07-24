#!/usr/bin/env python3
"""Test Google Drive folder access."""

import os
import sys
import json
from pathlib import Path

# Load environment manually
import os
os.environ.setdefault('DATABASE_URL_DIRECT', 'postgresql://postgres:m7ubbG7dYsh9jn2v@db.mtssbakpwbeizuybinsl.supabase.co:5432/postgres')
os.environ.setdefault('OPENAI_API_KEY', open('.env').read().split('OPENAI_API_KEY=')[1].split('\n')[0])

import psycopg2
from google.oauth2 import service_account
from googleapiclient.discovery import build

print("🔍 Testing Google Drive Folder Access")
print("=" * 70)

# Load request data for client_user_id
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)
client_user_id = request['request_data']['client_user_id']

# Get database connection
database_url = os.getenv('DATABASE_URL_DIRECT')
if database_url:
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
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
service = build('drive', 'v3', credentials=credentials)

print("✅ Google Drive service initialized")

# Test different folder access methods
folder_id = "0AM0PEUhIEQFUUk9PVA"

print(f"\n📁 Testing folder: {folder_id}")

# Method 1: Direct folder access
try:
    folder_info = service.files().get(fileId=folder_id, fields='id,name,permissions').execute()
    print(f"✅ Folder exists: {folder_info.get('name')}")
    print(f"   ID: {folder_info.get('id')}")
    if 'permissions' in folder_info:
        print(f"   Permissions: {len(folder_info['permissions'])} entries")
except Exception as e:
    print(f"❌ Cannot access folder directly: {e}")

# Method 2: List contents 
try:
    query = f"'{folder_id}' in parents"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType, parents)',
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    print(f"\n📋 Contents: {len(files)} items")
    
    for file in files[:10]:
        print(f"   - {file['name']} ({file['mimeType']})")
        
except Exception as e:
    print(f"❌ Cannot list folder contents: {e}")

# Method 3: Try to find the folder by name or search
try:
    print(f"\n🔍 Searching for shared folders...")
    
    # Search for shared folders with "book" or similar
    query = "sharedWithMe = true and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, owners, sharingUser)',
        pageSize=50
    ).execute()
    
    shared_folders = results.get('files', [])
    print(f"📋 Found {len(shared_folders)} shared folders:")
    
    for folder in shared_folders:
        print(f"   - {folder['name']} (ID: {folder['id']})")
        if 'owners' in folder:
            for owner in folder['owners']:
                print(f"     Owner: {owner.get('displayName', 'Unknown')}")
                
except Exception as e:
    print(f"❌ Cannot search shared folders: {e}")

# Method 4: Try URL-based folder ID extraction
drive_url = "https://drive.google.com/drive/u/0/folders/0AM0PEUhIEQFUUk9PVA"
print(f"\n🔗 Original URL: {drive_url}")

# The ID looks correct, let me try different scopes
print(f"\n🔧 Testing with different scopes...")

try:
    # Try with full drive access
    credentials_full = service_account.Credentials.from_service_account_info(
        creds_data,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service_full = build('drive', 'v3', credentials=credentials_full)
    
    folder_info = service_full.files().get(fileId=folder_id, fields='id,name').execute()
    print(f"✅ With full scope - Folder: {folder_info.get('name')}")
    
    # Try listing contents
    query = f"'{folder_id}' in parents"
    results = service_full.files().list(
        q=query,
        fields='files(id, name, mimeType)',
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    print(f"✅ With full scope - Contents: {len(files)} items")
    
    for file in files[:10]:
        print(f"   - {file['name']} ({file['mimeType']})")
        
except Exception as e:
    print(f"❌ Full scope failed: {e}")

print(f"\n🏁 Test completed")