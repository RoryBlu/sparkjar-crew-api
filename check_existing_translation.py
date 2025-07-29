#!/usr/bin/env python3
"""
Check if translation already exists in Vervelyn database.
Uses urllib to avoid dependency issues.
"""

import urllib.request
import urllib.parse
import json
import base64

# Supabase connection info from VERVELYN_CLIENT_INFO.md
SUPABASE_URL = "https://gvfiezbiyfggwdlvqnsc.supabase.co"
SUPABASE_ANON_KEY = "YOUR_ANON_KEY"  # You'll need to provide this
BOOK_KEY = "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"

def check_translation():
    """Check if translation exists using Supabase REST API."""
    
    # Query for translations
    query_params = {
        "book_key": f"eq.{BOOK_KEY}",
        "version": "eq.translation_en",
        "select": "page_number,created_at",
        "limit": "1"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/book_ingestions?" + urllib.parse.urlencode(query_params)
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        if data:
            print(f"✅ Translation exists! Found {len(data)} translated pages")
            print(f"Created at: {data[0]['created_at']}")
            return True
        else:
            print("❌ No translation found")
            return False
            
    except Exception as e:
        print(f"Error checking translation: {e}")
        print("\nTo check manually:")
        print("1. Use Railway deployment to run the translation")
        print("2. Or check Supabase dashboard directly")
        return False

if __name__ == "__main__":
    print("Checking for existing translation...")
    print(f"Book key: {BOOK_KEY}")
    print(f"Target version: translation_en\n")
    
    if SUPABASE_ANON_KEY == "YOUR_ANON_KEY":
        print("⚠️  Please update SUPABASE_ANON_KEY in this script")
        print("You can find it in your Supabase project settings")
    else:
        check_translation()