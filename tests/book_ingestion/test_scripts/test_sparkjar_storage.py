#!/usr/bin/env python3
"""Test access to sparkjar-storage folder."""

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

print("🔍 Testing sparkjar-storage Access")
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

# Search for sparkjar-storage folder
print(f"\n🔍 Searching for 'sparkjar-storage' folder...")

try:
    # Search for folders named "sparkjar-storage"
    query = "name = 'sparkjar-storage' and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(
        q=query,
        fields='files(id, name, owners, permissions)',
        pageSize=10
    ).execute()
    
    files = results.get('files', [])
    
    if files:
        for folder in files:
            folder_id = folder['id']
            print(f"✅ Found sparkjar-storage folder: {folder_id}")
            print(f"   Name: {folder['name']}")
            
            # Try to access this folder
            try:
                print(f"\n📁 Listing contents of sparkjar-storage...")
                contents_query = f"'{folder_id}' in parents"
                contents_results = service.files().list(
                    q=contents_query,
                    fields='files(id, name, mimeType)',
                    pageSize=100
                ).execute()
                
                contents = contents_results.get('files', [])
                print(f"✅ Found {len(contents)} items in sparkjar-storage:")
                
                for item in contents[:10]:  # Show first 10 items
                    print(f"  - {item['name']} ({item['mimeType']})")
                    
                    # If this is a folder that might contain book pages, explore it
                    if (item['mimeType'] == 'application/vnd.google-apps.folder' and 
                        any(keyword in item['name'].lower() for keyword in ['castor', 'gonzalez', 'book', 'vervelyn'])):
                        
                        print(f"\n📖 Exploring book-related folder: {item['name']}")
                        book_query = f"'{item['id']}' in parents"
                        book_results = service.files().list(
                            q=book_query,
                            fields='files(id, name, mimeType)',
                            pageSize=100
                        ).execute()
                        
                        book_files = book_results.get('files', [])
                        images = [bf for bf in book_files if 'image/' in bf['mimeType']]
                        
                        print(f"      📋 Folder contains {len(book_files)} items, {len(images)} images")
                        
                        if images:
                            print(f"      🖼️  First few images:")
                            for img in images[:5]:
                                print(f"         - {img['name']}")
                            
                            print(f"\n🎯 FOUND BOOK IMAGES!")
                            print(f"      Folder ID for crew: {item['id']}")
                            print(f"      Image count: {len(images)}")
                            
                if len(contents) > 10:
                    print(f"  ... and {len(contents) - 10} more items")
                    
            except Exception as e:
                print(f"❌ Cannot access sparkjar-storage contents: {e}")
    else:
        print("❌ No sparkjar-storage folder found")
        
        # Fallback: search for any accessible folders
        print("\n🔍 Searching for any accessible folders...")
        try:
            all_folders_query = "mimeType = 'application/vnd.google-apps.folder'"
            all_results = service.files().list(
                q=all_folders_query,
                fields='files(id, name)',
                pageSize=20
            ).execute()
            
            all_folders = all_results.get('files', [])
            print(f"✅ Found {len(all_folders)} accessible folders:")
            
            for folder in all_folders:
                print(f"  - {folder['name']} (ID: {folder['id']})")
                
        except Exception as e:
            print(f"❌ Cannot search for folders: {e}")
        
except Exception as e:
    print(f"\n❌ Search failed: {e}")

print(f"\n🏁 sparkjar-storage access test completed")