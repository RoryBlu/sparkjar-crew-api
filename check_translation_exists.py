#!/usr/bin/env python3
"""
Check if translation already exists in Vervelyn database.
"""
import psycopg2
import json

# Vervelyn database URL from VERVELYN_CLIENT_INFO.md
DATABASE_URL = "postgresql://postgres.gvfiezbiyfggwdlvqnsc:OUXQVlj4q6taAIZm@aws-0-us-east-2.pooler.supabase.com:5432/postgres"

def check_translation():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Query for translations
    query = """
    SELECT 
        page_number,
        page_content,
        version,
        created_at
    FROM book_ingestions
    WHERE book_name = 'Las Aventuras Completas del Reino Celestial'
    AND version = 'translation_en'
    ORDER BY page_number
    LIMIT 5;
    """
    
    print("Checking for existing translations...")
    cursor.execute(query)
    results = cursor.fetchall()
    
    if results:
        print(f"\n✅ Found {len(results)} translated pages!")
        for page_num, content, version, created in results:
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"\nPage {page_num} ({version}):")
            print(preview)
    else:
        print("❌ No translations found")
        
        # Check for original pages
        query2 = """
        SELECT COUNT(*), MIN(page_number), MAX(page_number)
        FROM book_ingestions
        WHERE book_name = 'Las Aventuras Completas del Reino Celestial'
        AND version = 'original';
        """
        cursor.execute(query2)
        count, min_page, max_page = cursor.fetchone()
        
        if count:
            print(f"\n📚 Found {count} original pages (pages {min_page}-{max_page})")
            print("Translation is needed!")
        else:
            print("\n❓ No book data found at all")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_translation()