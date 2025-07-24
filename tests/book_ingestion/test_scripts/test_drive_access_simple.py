#!/usr/bin/env python3
"""Simple test of Google Drive access."""

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

print("🔍 Testing Google Drive Access")
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

print("✅ Retrieved service account credentials")

# Initialize Google Drive
credentials = service_account.Credentials.from_service_account_info(
    creds_data,
    scopes=['https://www.googleapis.com/auth/drive']
)
service = build('drive', 'v3', credentials=credentials)

print("✅ Google Drive service initialized")

# Try to access the book 1 folder directly by ID (from screenshot)
folder_id = "1H4gFPBaauNXs-LQmivtSZq_zwAL5XIXJ"

try:
    # Test 1: Get folder info
    print(f"\n🔍 Testing folder access: {folder_id}")
    folder_info = service.files().get(fileId=folder_id, fields='id,name,owners,permissions').execute()
    print(f"✅ Folder info: {folder_info.get('name')} (ID: {folder_info.get('id')})")
    
    # Test 2: List contents
    print(f"\n📁 Listing folder contents...")
    query = f"'{folder_id}' in parents"
    results = service.files().list(
        q=query,
        fields='files(id, name, mimeType)',
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    print(f"✅ Found {len(files)} items in folder")
    
    for file in files:
        print(f"  - {file['name']} ({file['mimeType']})")
        
        # If this is the Vervelyn folder, explore it
        if file['name'].lower() == 'vervelyn' and file['mimeType'] == 'application/vnd.google-apps.folder':
            print(f"\n📂 Exploring Vervelyn folder: {file['id']}")
            
            vervelyn_query = f"'{file['id']}' in parents"
            vervelyn_results = service.files().list(
                q=vervelyn_query,
                fields='files(id, name, mimeType)',
                pageSize=100
            ).execute()
            
            vervelyn_files = vervelyn_results.get('files', [])
            print(f"   Found {len(vervelyn_files)} items in Vervelyn:")
            
            for vf in vervelyn_files[:10]:
                print(f"     - {vf['name']} ({vf['mimeType']})")
    
    if files:
        print(f"\n🎯 SUCCESS! Can access Google Drive folder")
        print(f"   Total items: {len(files)}")
    else:
        print(f"\n⚠️  Folder is accessible but empty")
        
except Exception as e:
    print(f"\n❌ Cannot access folder: {e}")

print(f"\n🏁 Drive access test completed")