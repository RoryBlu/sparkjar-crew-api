#!/usr/bin/env python
"""Test connection to main database."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Get the main database URL from env
main_db_url = os.getenv("DATABASE_URL_DIRECT")
# Convert from asyncpg to regular psycopg2
main_db_url = main_db_url.replace("postgresql+asyncpg://", "postgresql://")

print(f"Testing connection to main database...")
print(f"Host: {main_db_url.split('@')[1].split(':')[0]}")

try:
    conn = psycopg2.connect(main_db_url)
    print("✅ Main database connection successful!")
    
    # Test a simple query
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM client_users")
    count = cur.fetchone()[0]
    print(f"Found {count} users in client_users table")
    
    conn.close()
except Exception as e:
    print(f"❌ Main database connection failed: {e}")

# Now test the client database URL format
client_db_url = "postgresql://postgres:K6kTX6jGjGi1Nw6W@db.mtssbakpwbeizuybinsl.supabase.co:5432/postgres"
print(f"\nTesting client database connection...")
print(f"Host: {client_db_url.split('@')[1].split(':')[0]}")

try:
    conn = psycopg2.connect(client_db_url)
    print("✅ Client database connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Client database connection failed: {e}")