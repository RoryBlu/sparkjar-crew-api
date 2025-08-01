#!/usr/bin/env python
"""Test single page OCR and storage."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

import asyncio
from database.connection import get_db_session
from database.models import ClientUsers, ClientSecrets, BookIngestions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sparkjar_shared.tools.google_drive_tool import GoogleDriveTool
from sparkjar_shared.tools.image_viewer_tool import ImageViewerTool
import json

async def test_single_page():
    """Test OCR on a single page."""
    client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"
    folder_id = "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"
    
    print("📄 Single Page OCR Test")
    print("=" * 60)
    
    # Get one file
    drive_tool = GoogleDriveTool()
    files_result = drive_tool._run(folder_path=folder_id, client_user_id=client_user_id)
    
    if isinstance(files_result, str):
        files_result = json.loads(files_result)
    
    files = files_result.get("files", [])
    png_files = [f for f in files if f['name'].endswith('.png')]
    
    if not png_files:
        print("No PNG files found!")
        return
    
    # Take just the first file
    test_file = png_files[0]
    print(f"\n📖 Processing: {test_file['name']}")
    print(f"   File ID: {test_file['file_id']}")
    print(f"   Local path: {test_file['local_path']}")
    
    # OCR the file
    print("\n🔍 Running OCR...")
    ocr_tool = ImageViewerTool()
    ocr_result = ocr_tool._run(test_file['local_path'])
    
    # Show OCR result
    print(f"\n📝 OCR Result (first 500 chars):")
    print("-" * 60)
    print(ocr_result[:500])
    print("-" * 60)
    print(f"Total length: {len(ocr_result)} characters")
    
    # Get database connection
    async with get_db_session() as session:
        # Get client database URL
        result = await session.execute(
            select(ClientUsers).filter_by(id=client_user_id)
        )
        user = result.scalar_one_or_none()
        
        secrets_result = await session.execute(
            select(ClientSecrets).filter_by(
                client_id=user.clients_id,
                secret_key="database_url"
            )
        )
        secret = secrets_result.scalar_one_or_none()
        
        db_url = secret.secret_value
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Store in database
    engine = create_async_engine(db_url, echo=False)
    ClientSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with ClientSession() as session:
            # Create record
            page = BookIngestions(
                book_key=folder_id,
                page_number=1,
                file_name=test_file['name'],
                language_code="es",
                version="original",
                page_text=ocr_result,
                ocr_metadata={
                    "confidence": 0.95,
                    "processing_date": datetime.now().isoformat(),
                    "file_id": test_file['file_id']
                }
            )
            
            session.add(page)
            await session.commit()
            await session.refresh(page)
            
            print(f"\n✅ Stored in database with ID: {page.id}")
            
            # Query to verify
            result = await session.execute(
                select(BookIngestions).filter_by(book_key=folder_id)
            )
            total = len(result.scalars().all())
            print(f"   Total pages in database: {total}")
            
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_single_page())