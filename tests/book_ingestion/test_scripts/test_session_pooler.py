#!/usr/bin/env python
"""Test connection using session pooler URL."""
import psycopg2

# Session pooler URL (IPv4 compatible)
session_pooler_url = "postgresql://postgres.mtssbakpwbeizuybinsl:K6kTX6jGjGi1Nw6W@aws-0-us-east-2.pooler.supabase.com:5432/postgres"

print("Testing session pooler connection...")
print("Host: aws-0-us-east-2.pooler.supabase.com")
print("Port: 5432 (session mode)")

try:
    conn = psycopg2.connect(session_pooler_url)
    print("✅ Session pooler connection successful!")
    
    # Test query
    cur = conn.cursor()
    cur.execute("SELECT current_database(), version()")
    db, version = cur.fetchone()
    print(f"Connected to database: {db}")
    print(f"PostgreSQL version: {version[:50]}...")
    
    # Check if book_ingestions table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'book_ingestions'
        );
    """)
    exists = cur.fetchone()[0]
    print(f"book_ingestions table exists: {'✅ Yes' if exists else '❌ No'}")
    
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")