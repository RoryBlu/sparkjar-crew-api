#!/usr/bin/env python
"""Test main database with session pooler."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Check if our main DB also needs session pooler
print("Checking main database URLs in .env...")

# Get pooled URL from env
pooled_url = os.getenv("DATABASE_URL_POOLED")
if pooled_url:
    # Remove asyncpg
    pooled_url = pooled_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Extract components
    import urllib.parse
    parsed = urllib.parse.urlparse(pooled_url)
    print(f"Pooled URL host: {parsed.hostname}")
    print(f"Pooled URL port: {parsed.port}")
    
    # Check if it's already using pooler
    if "pooler.supabase.com" in parsed.hostname:
        print("✅ Main DB already uses session pooler")
        
        # Try connecting
        try:
            conn = psycopg2.connect(pooled_url)
            print("✅ Main pooled connection successful!")
            conn.close()
        except Exception as e:
            print(f"❌ Main pooled connection failed: {e}")
    else:
        print("❌ Main DB uses direct connection (IPv6 only)")
        print("This explains why we can't connect locally!")
        
        # Build session pooler URL for main DB
        # Pattern: postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
        print("\nMain DB needs session pooler URL too!")