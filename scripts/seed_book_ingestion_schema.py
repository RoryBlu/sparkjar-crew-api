#!/usr/bin/env python3
"""
Seed book ingestion crew schema into object_schemas table.
"""

import os
import sys
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.database.connection import get_db_engine
from src.utils.crew_logger import setup_logging

logger = setup_logging(__name__)

# Book ingestion request schema
BOOK_INGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "job_id": {
            "type": "string",
            "description": "Unique job identifier"
        },
        "job_key": {
            "type": "string",
            "const": "book_ingestion_crew",
            "description": "Must be 'book_ingestion_crew'"
        },
        "client_id": {
            "type": "string",
            "format": "uuid",
            "description": "Client ID (e.g., Vervelyn Publishing)"
        },
        "client_user_id": {
            "type": "string",
            "format": "uuid",
            "description": "User within the client organization"
        },
        "actor_type": {
            "type": "string",
            "enum": ["user", "synth"],
            "description": "Actor type: 'user' or 'synth'"
        },
        "actor_id": {
            "type": "string",
            "format": "uuid",
            "description": "Must exist in actors table"
        },
        "google_drive_folder_path": {
            "type": "string",
            "description": "Path to Google Drive folder with images"
        },
        "language": {
            "type": "string",
            "enum": ["en", "es", "fr", "de", "it", "pt", "nl", "pl", "ru", "ja", "zh"],
            "description": "ISO language code"
        },
        "version": {
            "type": "string",
            "default": "original",
            "description": "Book version identifier"
        },
        "page_naming_pattern": {
            "type": "string",
            "description": "Pattern for extracting page numbers from filenames",
            "nullable": true
        },
        "book_title": {
            "type": "string",
            "description": "Title of the book",
            "nullable": true
        },
        "book_author": {
            "type": "string",
            "description": "Author of the book",
            "nullable": true
        },
        "book_genre": {
            "type": "string",
            "description": "Genre (fiction, non-fiction, etc.)",
            "nullable": true
        },
        "book_time_period": {
            "type": "string",
            "description": "Time period of the story",
            "nullable": true
        },
        "book_location": {
            "type": "string",
            "description": "Setting/location of the story",
            "nullable": true
        }
    },
    "required": [
        "job_id",
        "job_key",
        "client_id",
        "client_user_id",
        "actor_type",
        "actor_id",
        "google_drive_folder_path",
        "language"
    ],
    "additionalProperties": false
}


def seed_schema():
    """Seed the book ingestion schema."""
    try:
        engine = get_db_engine()
        
        with engine.begin() as conn:
            # Check if schema already exists
            check_query = text("""
                SELECT id, version, created_at 
                FROM object_schemas 
                WHERE name = :name 
                AND object_type = :object_type
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = conn.execute(check_query, {
                "name": "book_ingestion_crew",
                "object_type": "crew_context"
            }).fetchone()
            
            if result:
                logger.info(f"Schema already exists: ID={result[0]}, Version={result[1]}, Created={result[2]}")
                
                # Update existing schema
                update_query = text("""
                    UPDATE object_schemas 
                    SET schema = :schema,
                        version = :version,
                        is_active = true
                    WHERE id = :id
                """)
                
                conn.execute(update_query, {
                    "id": result[0],
                    "schema": json.dumps(BOOK_INGESTION_SCHEMA),
                    "version": "2.0.0"  # Enhanced version
                })
                
                logger.info("Updated existing schema to version 2.0.0")
            else:
                # Insert new schema
                insert_query = text("""
                    INSERT INTO object_schemas 
                    (name, object_type, schema, version, is_active, created_at)
                    VALUES (:name, :object_type, :schema, :version, true, :created_at)
                    RETURNING id
                """)
                
                result = conn.execute(insert_query, {
                    "name": "book_ingestion_crew",
                    "object_type": "crew_context",
                    "schema": json.dumps(BOOK_INGESTION_SCHEMA),
                    "version": "2.0.0",
                    "created_at": datetime.utcnow()
                }).fetchone()
                
                logger.info(f"Created new schema with ID: {result[0]}")
            
            # Verify the schema
            verify_query = text("""
                SELECT name, object_type, version, is_active
                FROM object_schemas
                WHERE name = :name
            """)
            
            result = conn.execute(verify_query, {"name": "book_ingestion_crew"}).fetchone()
            
            if result:
                logger.info(f"Verified schema: {result}")
                logger.info("✅ Book ingestion crew schema seeded successfully!")
                
                # Show sample request
                logger.info("\nSample request structure:")
                sample = {
                    "job_id": "job_123456",
                    "job_key": "book_ingestion_crew",
                    "client_id": "550e8400-e29b-41d4-a716-446655440000",
                    "client_user_id": "660e8400-e29b-41d4-a716-446655440001",
                    "actor_type": "user",
                    "actor_id": "770e8400-e29b-41d4-a716-446655440002",
                    "google_drive_folder_path": "/Manuscripts/BookTitle",
                    "language": "es",
                    "version": "original",
                    "page_naming_pattern": "page_###.jpg",
                    "book_title": "El Jardín de los Senderos que se Bifurcan",
                    "book_author": "Jorge Luis Borges",
                    "book_genre": "Fiction",
                    "book_time_period": "1940s",
                    "book_location": "Argentina"
                }
                logger.info(json.dumps(sample, indent=2))
            else:
                logger.error("Failed to verify schema after seeding")
                
    except Exception as e:
        logger.error(f"Error seeding schema: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    logger.info("Starting book ingestion schema seeding...")
    seed_schema()