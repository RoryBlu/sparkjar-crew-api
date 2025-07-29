#!/usr/bin/env python3
"""
Direct query of Vervelyn database and export to markdown.
Uses basic libraries to avoid dependency issues.
"""

import psycopg2
import json
from datetime import datetime

# Vervelyn database connection (from VERVELYN_CLIENT_INFO.md)
DB_URL = "postgresql://postgres.gvfiezbiyfggwdlvqnsc:OUXQVlj4q6taAIZm@aws-0-us-east-2.pooler.supabase.com:5432/postgres"
BOOK_KEY = "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"

def query_book_pages():
    """Query all pages from the book."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # First, see what versions exist
        cur.execute("""
            SELECT DISTINCT version, language_code, COUNT(*) as page_count
            FROM vervelyn.book_ingestions
            WHERE book_key = %s
            GROUP BY version, language_code
            ORDER BY version
        """, (BOOK_KEY,))
        
        versions = cur.fetchall()
        print(f"Found {len(versions)} versions:")
        for v in versions:
            print(f"  - Version: {v[0]}, Language: {v[1]}, Pages: {v[2]}")
        
        # Get all pages (both original and translated if exists)
        pages_by_version = {}
        
        for version, lang, _ in versions:
            cur.execute("""
                SELECT page_number, page_text, file_name, language_code
                FROM vervelyn.book_ingestions
                WHERE book_key = %s AND version = %s
                ORDER BY page_number
            """, (BOOK_KEY, version))
            
            pages = cur.fetchall()
            pages_by_version[version] = pages
            print(f"\nLoaded {len(pages)} pages for version: {version}")
        
        return pages_by_version
        
    finally:
        cur.close()
        conn.close()

def export_to_markdown(pages_by_version):
    """Export book to markdown file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Check if we have translations
    has_translation = any('translation' in v for v in pages_by_version.keys())
    
    if has_translation:
        # Export translated version
        for version in pages_by_version:
            if 'translation' in version:
                filename = f"vervelyn_book_{version}_{timestamp}.md"
                pages = pages_by_version[version]
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("# Vervelyn Book - English Translation\n\n")
                    f.write(f"**Source**: {BOOK_KEY}\n")
                    f.write(f"**Version**: {version}\n")
                    f.write(f"**Total Pages**: {len(pages)}\n")
                    f.write(f"**Exported**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    
                    for page_num, page_text, file_name, lang in pages:
                        f.write(f"## Page {page_num}\n\n")
                        f.write(f"*File: {file_name}*\n\n")
                        f.write(page_text)
                        f.write("\n\n---\n\n")
                
                print(f"\n✅ Exported translated book to: {filename}")
    
    # Always export original too
    if 'original' in pages_by_version:
        filename = f"vervelyn_book_original_{timestamp}.md"
        pages = pages_by_version['original']
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Vervelyn Book - Original Spanish\n\n")
            f.write(f"**Source**: {BOOK_KEY}\n")
            f.write(f"**Version**: original\n")
            f.write(f"**Total Pages**: {len(pages)}\n")
            f.write(f"**Exported**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            for page_num, page_text, file_name, lang in pages:
                f.write(f"## Page {page_num}\n\n")
                f.write(f"*File: {file_name}*\n\n")
                f.write(page_text)
                f.write("\n\n---\n\n")
        
        print(f"✅ Exported original book to: {filename}")

def main():
    print("=== Vervelyn Book Query and Export ===\n")
    
    print("Connecting to Vervelyn database...")
    pages_by_version = query_book_pages()
    
    if not pages_by_version:
        print("No pages found!")
        return
    
    print("\nExporting to markdown...")
    export_to_markdown(pages_by_version)
    
    print("\n✨ Done! Check the generated .md files")

if __name__ == "__main__":
    main()