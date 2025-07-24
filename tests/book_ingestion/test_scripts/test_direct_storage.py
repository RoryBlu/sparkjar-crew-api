#!/usr/bin/env python
"""Direct test of book page storage."""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

from database.connection import get_db_session
from database.models import ClientUsers, ClientSecrets, BookIngestions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime

async def test_storage():
    """Test storing a page directly."""
    client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"
    
    # Get client database URL
    async with get_db_session() as session:
        # Get user's client_id
        result = await session.execute(
            select(ClientUsers).filter_by(id=client_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("User not found")
            return
        
        print(f"User: {user.full_name}, client_id: {user.clients_id}")
        
        # Get database URL
        secrets_result = await session.execute(
            select(ClientSecrets).filter_by(
                client_id=user.clients_id,
                secret_key="database_url"
            )
        )
        secret = secrets_result.scalar_one_or_none()
        
        if not secret:
            print("Database URL not found")
            return
        
        db_url = secret.secret_value
        print("Found client database URL")
    
    # Convert to async URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Connect to client database
    engine = create_async_engine(db_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Create test record
            page = BookIngestions(
                book_key="1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
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
            await session.commit()
            await session.refresh(page)
            
            print(f"Successfully stored page with ID: {page.id}")
            
            # Verify it's there
            result = await session.execute(
                select(BookIngestions).filter_by(book_key="1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO")
            )
            pages = result.scalars().all()
            print(f"Found {len(pages)} pages in database")
            
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_storage())