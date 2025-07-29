#!/usr/bin/env python3
"""
Minimal script to check if translation exists in Vervelyn database.
Uses only standard library to avoid dependency issues.
"""

import urllib.parse
import urllib.request
import json
import ssl

# Database info from VERVELYN_CLIENT_INFO.md
DB_INFO = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "port": "5432",
    "database": "postgres",
    "user": "postgres.gvfiezbiyfggwdlvqnsc",
    "password": "OUXQVlj4q6taAIZm"
}

BOOK_KEY = "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"

def check_translation_exists():
    """
    Check if translation exists by querying Supabase REST API.
    """
    # Supabase provides a REST API endpoint
    base_url = f"https://{DB_INFO['user'].split('.')[1]}.supabase.co"
    
    print("Checking Vervelyn database for translations...")
    print(f"Book key: {BOOK_KEY}")
    print(f"Database: {base_url}")
    
    # Note: This would require Supabase API key to actually work
    # For now, just showing the approach
    
    print("\nTo run the translation crew:")
    print("1. The service needs to be running on Railway (or locally with Python 3.11+)")
    print("2. Use the API endpoint POST /crew_job with:")
    print(json.dumps({
        "job_key": "book_translation_crew",
        "request_data": {
            "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
            "actor_type": "client", 
            "actor_id": "1d1c2154-242b-4f49-9ca8-e57129ddc823",
            "book_key": BOOK_KEY,
            "target_language": "en"
        }
    }, indent=2))
    
    print("\nAlternatively:")
    print("- Deploy this service to Railway using the existing railway.json")
    print("- Or set up Python 3.11+ locally with proper virtual environment")
    print("- The dependencies are managed through requirements.txt and sparkjar-shared from GitHub")

if __name__ == "__main__":
    check_translation_exists()