#!/usr/bin/env python3
"""
Query Vervelyn database to see what books are available.
"""

import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import get_db_session
from src.database.models import ClientUsers, ClientSecrets

async def get_vervelyn_books():
    """Query Vervelyn database for available books."""
    
    # First, get Vervelyn's client_user_id and database URL
    async with get_db_session() as session:
        # Find Vervelyn user
        result = await session.execute(
            select(ClientUsers).filter_by(id="3a411a30-1653-4caf-acee-de257ff50e36")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("Vervelyn user not found!")
            return
            
        print(f"Found Vervelyn user: {user.name}")
        print(f"Client ID: {user.clients_id}")
        
        # Get database URL
        secrets_result = await session.execute(
            select(ClientSecrets).filter_by(
                client_id=user.clients_id,
                secret_key="database_url"
            )
        )
        secret = secrets_result.scalar_one_or_none()
        
        if not secret:
            print("Database URL not found!")
            return
            
        db_url = secret.secret_value
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Connect to Vervelyn database
    print(f"\nConnecting to Vervelyn database...")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Query distinct books
            query = text("""
                SELECT DISTINCT 
                    book_key,
                    version,
                    language_code,
                    COUNT(*) as page_count,
                    MIN(page_number) as first_page,
                    MAX(page_number) as last_page,
                    MIN(created_at) as created_at
                FROM vervelyn.book_ingestions
                GROUP BY book_key, version, language_code
                ORDER BY created_at DESC
            """)
            
            result = await session.execute(query)
            books = result.fetchall()
            
            print(f"\nFound {len(books)} book versions in Vervelyn database:\n")
            print(f"{'Book Key':<80} {'Version':<20} {'Lang':<6} {'Pages':<8} {'Created'}")
            print("-" * 130)
            
            for book in books:
                book_key_short = book.book_key[:77] + "..." if len(book.book_key) > 80 else book.book_key
                print(f"{book_key_short:<80} {book.version:<20} {book.language_code:<6} {book.page_count:<8} {book.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Get sample text from first book
            if books:
                print(f"\n\nSample from first book (first 3 pages):")
                print("-" * 80)
                
                first_book = books[0]
                sample_query = text("""
                    SELECT page_number, page_text, file_name
                    FROM vervelyn.book_ingestions
                    WHERE book_key = :book_key 
                    AND version = :version
                    ORDER BY page_number
                    LIMIT 3
                """)
                
                pages = await session.execute(
                    sample_query,
                    {
                        "book_key": first_book.book_key,
                        "version": first_book.version
                    }
                )
                
                for page in pages:
                    print(f"\nPage {page.page_number} ({page.file_name}):")
                    print(page.page_text[:200] + "..." if len(page.page_text) > 200 else page.page_text)
                    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(get_vervelyn_books())