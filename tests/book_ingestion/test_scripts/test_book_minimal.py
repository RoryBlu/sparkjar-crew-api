#!/usr/bin/env python3
"""Minimal test for book ingestion - bypass all import issues."""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Just test the Google Drive access first
print("🚀 Testing Google Drive Access")
print("=" * 70)

# Load request data
with open('book_ingestion_request.json', 'r') as f:
    request = json.load(f)
request_data = request['request_data']

client_user_id = request_data['client_user_id']
folder_path = request_data['google_drive_folder_path']

print(f"Client User ID: {client_user_id}")
print(f"Google Drive Path: {folder_path}")

# Direct database query to get credentials
import psycopg2
from uuid import UUID

database_url = os.getenv('DATABASE_URL_DIRECT')
if database_url:
    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')

try:
    print("\n📊 Checking Google credentials...")
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    # Get client_id from user_id
    cur.execute("""
        SELECT clients_id FROM client_users WHERE id = %s
    """, (client_user_id,))
    
    result = cur.fetchone()
    if result:
        client_id = result[0]
        print(f"✅ Found client_id: {client_id}")
        
        # Check for Google credentials
        cur.execute("""
            SELECT secret_key, 
                   CASE WHEN secrets_metadata IS NOT NULL THEN 'HAS CREDENTIALS' ELSE 'NO CREDENTIALS' END
            FROM client_secrets 
            WHERE client_id = %s AND secret_key = 'googleapis.service_account'
        """, (client_id,))
        
        cred_result = cur.fetchone()
        if cred_result:
            print(f"✅ Google credentials: {cred_result[1]}")
        else:
            print("❌ No Google credentials found")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database error: {e}")

# Now let's try a simple Google Drive API test
try:
    print("\n📊 Testing Google Drive API...")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    # Get credentials from database
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT cs.secrets_metadata
        FROM client_secrets cs
        JOIN client_users cu ON cu.clients_id = cs.client_id
        WHERE cu.id = %s AND cs.secret_key = 'googleapis.service_account'
    """, (client_user_id,))
    
    result = cur.fetchone()
    if result and result[0]:
        creds_data = result[0]
        print("✅ Retrieved Google credentials from database")
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Build service
        service = build('drive', 'v3', credentials=credentials)
        print("✅ Google Drive service initialized")
        
        # Test listing files
        print(f"\n📁 Checking folder: {folder_path}")
        
        # For now, just list some files from the root
        results = service.files().list(
            pageSize=10,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = results.get('files', [])
        print(f"\n📋 Found {len(files)} files in Drive:")
        for file in files[:5]:
            print(f"  - {file['name']} ({file['mimeType']})")
            
    else:
        print("❌ No Google credentials in database")
    
    cur.close()
    conn.close()
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Install with: pip install google-api-python-client google-auth")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()