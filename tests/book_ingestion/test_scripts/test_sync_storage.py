#!/usr/bin/env python
"""Test storage with synchronous connection."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from database.models import ClientUsers, ClientSecrets, BookIngestions
from datetime import datetime
import psycopg2

# First get the URL synchronously
from sqlalchemy import create_engine as sync_create_engine
from database.connection import DATABASE_URL_DIRECT

# Create sync engine for main database
sync_engine = sync_create_engine(DATABASE_URL_DIRECT.replace("+asyncpg", ""))
Session = sessionmaker(bind=sync_engine)

client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"

with Session() as session:
    # Get user
    user = session.query(ClientUsers).filter_by(id=client_user_id).first()
    print(f"User: {user.full_name}")
    
    # Get database URL
    secret = session.query(ClientSecrets).filter_by(
        client_id=user.clients_id,
        secret_key="database_url"
    ).first()
    
    client_db_url = secret.secret_value
    print(f"Got client database URL")
    # Parse URL safely to check components
    import urllib.parse
    parsed = urllib.parse.urlparse(client_db_url)
    print(f"URL host: {parsed.hostname}")
    print(f"URL user: {parsed.username}")
    print(f"URL has password: {'yes' if parsed.password else 'no'}")

# Now connect to client database synchronously
client_engine = create_engine(client_db_url, echo=True)
ClientSession = sessionmaker(bind=client_engine)

try:
    with ClientSession() as session:
        # Create test record
        page = BookIngestions(
            book_key="castor-gonzalez-book-1",
            page_number=1,
            file_name="baron001.png",
            language_code="es",
            version="original",
            page_text="que en la mayoría de las veces no alcanzaba para todos los que estaban en la cola...",
            ocr_metadata={
                "confidence": 0.95,
                "processing_date": datetime.now().isoformat(),
                "test": True
            }
        )
        
        session.add(page)
        session.commit()
        
        print(f"Successfully stored page with ID: {page.id}")
        
        # Verify
        pages = session.query(BookIngestions).filter_by(
            book_key="castor-gonzalez-book-1"
        ).all()
        print(f"Found {len(pages)} pages in database")
        
finally:
    client_engine.dispose()
    sync_engine.dispose()