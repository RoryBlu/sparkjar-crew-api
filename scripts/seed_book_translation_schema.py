#!/usr/bin/env python3
"""
Seed book translation crew schema into object_schemas table.
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
from sparkjar_shared.utils.crew_logger import setup_logging

logger = setup_logging(__name__)

# Book translation crew request schema
BOOK_TRANSLATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Book Translation Crew Input Schema",
    "type": "object",
    "description": "Input parameters for translating previously ingested books",
    "properties": {
        "client_user_id": {
            "type": "string",
            "format": "uuid",
            "description": "User within the client organization"
        },
        "actor_type": {
            "type": "string",
            "enum": ["client", "synth_class", "skill_module", "synth"],
            "description": "Actor type: client, synth_class, skill_module, or synth"
        },
        "actor_id": {
            "type": "string",
            "format": "uuid",
            "description": "Must exist in actors table"
        },
        "book_key": {
            "type": "string",
            "description": "Book identifier from ingestion (Google Drive path)",
            "examples": [
                "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"
            ]
        },
        "target_language": {
            "type": "string",
            "enum": ["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"],
            "default": "en",
            "description": "Target language code for translation"
        }
    },
    "required": ["client_user_id", "actor_type", "actor_id", "book_key"],
    "additionalProperties": false
}

def main():
    """Seed the book translation crew schema."""
    try:
        logger.info("=== Seeding Book Translation Crew Schema ===")
        
        # Get database connection
        engine = get_db_engine()
        
        with engine.connect() as conn:
            # Check if schema already exists
            check_query = text("""
                SELECT id, version, is_active 
                FROM object_schemas 
                WHERE name = :name
                AND object_type = :object_type
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            existing = conn.execute(check_query, {
                "name": "book_translation_crew",
                "object_type": "crew_context"
            }).fetchone()
            
            if existing:
                logger.info(f"Schema already exists: ID={existing[0]}, version={existing[1]}, active={existing[2]}")
                
                # Optionally update if schema has changed
                if not existing[2]:  # If not active
                    logger.info("Activating existing schema...")
                    update_query = text("""
                        UPDATE object_schemas 
                        SET is_active = true, updated_at = :updated_at
                        WHERE id = :id
                    """)
                    conn.execute(update_query, {
                        "id": existing[0],
                        "updated_at": datetime.utcnow()
                    })
                    conn.commit()
                    logger.info("Schema activated")
                else:
                    logger.info("Schema is already active - no changes needed")
            else:
                # Insert new schema
                insert_query = text("""
                    INSERT INTO object_schemas 
                    (name, object_type, schema, version, is_active, created_at)
                    VALUES (:name, :object_type, :schema, :version, true, :created_at)
                    RETURNING id
                """)
                
                result = conn.execute(insert_query, {
                    "name": "book_translation_crew",
                    "object_type": "crew_context",
                    "schema": json.dumps(BOOK_TRANSLATION_SCHEMA),
                    "version": "1.0.0",
                    "created_at": datetime.utcnow()
                }).fetchone()
                
                logger.info(f"Created new schema with ID: {result[0]}")
            
            conn.commit()
            
        logger.info("=== Schema Seeding Complete ===")
        
    except Exception as e:
        logger.error(f"Error seeding schema: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()