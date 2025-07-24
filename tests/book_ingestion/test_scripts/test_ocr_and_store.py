#!/usr/bin/env python
"""Test OCR and database storage directly."""
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
from tools.google_drive_tool import GoogleDriveTool
from tools.image_viewer_tool import ImageViewerTool
import json

async def test_ocr_and_store():
    """Test OCR extraction and database storage."""
    client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"
    folder_id = "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"
    
    print("📚 Book Ingestion Test - Direct OCR and Storage")
    print("=" * 60)
    
    # Step 1: List files from Google Drive
    print("\n1️⃣ Listing files from Google Drive...")
    drive_tool = GoogleDriveTool()
    
    try:
        # List files
        files_result = drive_tool._run(
            folder_path=folder_id,
            client_user_id=client_user_id
        )
        
        # Parse result
        if isinstance(files_result, str):
            files_result = json.loads(files_result)
        
        if files_result.get("status") == "success":
            files = files_result.get("files", [])
            print(f"✅ Found {len(files)} files")
            
            # Get first 5 files
            test_files = [f for f in files if f['name'].endswith('.png')][:5]
            print(f"   Processing first {len(test_files)} PNG files")
        else:
            print(f"❌ Failed to list files: {files_result}")
            return
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return
    
    # Step 2: Get database connection
    print("\n2️⃣ Getting database connection...")
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
    
    # Connect to client database
    engine = create_async_engine(db_url, echo=False)
    ClientSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Step 3: Process each file
    print("\n3️⃣ Processing files...")
    ocr_tool = ImageViewerTool()
    successful = 0
    
    try:
        async with ClientSession() as session:
            for i, file_info in enumerate(test_files):
                print(f"\n   Processing page {i+1}/{len(test_files)}: {file_info['name']}")
                
                # Extract text using OCR
                local_path = file_info.get('local_path')
                if local_path:
                    try:
                        ocr_result = ocr_tool._run(local_path)
                        
                        # Parse OCR result
                        if isinstance(ocr_result, str):
                            # Extract text from result
                            text = ocr_result
                            confidence = 0.95  # Default confidence
                        else:
                            text = str(ocr_result)
                            confidence = 0.95
                        
                        # Store in database
                        page = BookIngestions(
                            book_key=folder_id,
                            page_number=i + 1,
                            file_name=file_info['name'],
                            language_code="es",
                            version="original",
                            page_text=text[:1000],  # Limit for testing
                            ocr_metadata={
                                "confidence": confidence,
                                "processing_date": datetime.now().isoformat(),
                                "full_length": len(text)
                            }
                        )
                        
                        session.add(page)
                        await session.commit()
                        
                        print(f"   ✅ Stored {len(text)} characters")
                        successful += 1
                        
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                else:
                    print(f"   ⚠️  No local path for file")
            
            # Check total stored
            result = await session.execute(
                select(BookIngestions).filter_by(book_key=folder_id)
            )
            total_pages = len(result.scalars().all())
            print(f"\n✅ Summary: {successful}/{len(test_files)} pages processed")
            print(f"   Total pages in database: {total_pages}")
            
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_ocr_and_store())