#!/usr/bin/env python3
"""Test what the service account can actually access."""

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

print("🔍 Testing Service Account Access")
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

print("✅ Retrieved service account credentials")

# Try different authentication approaches
scopes_to_try = [
    ['https://www.googleapis.com/auth/drive'],
    ['https://www.googleapis.com/auth/drive.readonly'],
    ['https://www.googleapis.com/auth/drive.file'],
    ['https://www.googleapis.com/auth/drive.metadata'],
]

folder_id = "0AM0PEUhIEQFUUk9PVA"

for i, scopes in enumerate(scopes_to_try):
    print(f"\n🔧 Test {i+1}: Trying scopes: {scopes}")
    
    try:
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=scopes
        )
        service = build('drive', 'v3', credentials=credentials)
        
        # Test 1: Can we get folder info?
        try:
            folder_info = service.files().get(fileId=folder_id, fields='id,name,owners,permissions').execute()
            print(f"   ✅ Folder info: {folder_info.get('name')} (ID: {folder_info.get('id')})")
        except Exception as e:
            print(f"   ❌ Cannot get folder info: {e}")
            continue
        
        # Test 2: Can we list contents?
        try:
            query = f"'{folder_id}' in parents"
            results = service.files().list(
                q=query,
                fields='files(id, name, mimeType)',
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            print(f"   ✅ Found {len(files)} items in folder")
            
            for file in files[:5]:
                print(f"      - {file['name']} ({file['mimeType']})")
                
            if len(files) > 5:
                print(f"      ... and {len(files) - 5} more")
                
            # Success! Let's explore further
            if files:
                print(f"\n🎯 SUCCESS with scopes: {scopes}")
                
                # Look for Vervelyn folder
                for file in files:
                    if file['name'].lower() == 'vervelyn' and file['mimeType'] == 'application/vnd.google-apps.folder':
                        print(f"\n📁 Found Vervelyn folder: {file['id']}")
                        
                        # Explore Vervelyn folder
                        vervelyn_query = f"'{file['id']}' in parents"
                        vervelyn_results = service.files().list(
                            q=vervelyn_query,
                            fields='files(id, name, mimeType)',
                            pageSize=100
                        ).execute()
                        
                        vervelyn_files = vervelyn_results.get('files', [])
                        print(f"   📋 Vervelyn contains {len(vervelyn_files)} items:")
                        
                        for vf in vervelyn_files[:10]:
                            print(f"      - {vf['name']} ({vf['mimeType']})")
                            
                            # If it's a folder that might contain book pages, explore it
                            if (vf['mimeType'] == 'application/vnd.google-apps.folder' and 
                                any(keyword in vf['name'].lower() for keyword in ['castor', 'gonzalez', 'book'])):
                                
                                print(f"\n📖 Exploring book folder: {vf['name']}")
                                book_query = f"'{vf['id']}' in parents"
                                book_results = service.files().list(
                                    q=book_query,
                                    fields='files(id, name, mimeType)',
                                    pageSize=100
                                ).execute()
                                
                                book_files = book_results.get('files', [])
                                images = [bf for bf in book_files if 'image/' in bf['mimeType']]
                                
                                print(f"      📋 Book folder contains {len(book_files)} items, {len(images)} images")
                                
                                if images:
                                    print(f"      🖼️  First few images:")
                                    for img in images[:5]:
                                        print(f"         - {img['name']}")
                                    
                                    print(f"\n🎯 FOUND BOOK IMAGES!")
                                    print(f"      Folder ID for crew: {vf['id']}")
                                    print(f"      Image count: {len(images)}")
                                    break
                        break
                break
                
        except Exception as e:
            print(f"   ❌ Cannot list contents: {e}")
            
    except Exception as e:
        print(f"   ❌ Failed to initialize service: {e}")

print(f"\n🏁 Access testing completed")