#!/usr/bin/env python3
"""
Create book ingestion database tables for any client.

This script creates the necessary tables in a client's database:
- book_ingestions: Stores transcribed page text
- object_embeddings: Stores text embeddings for semantic search

Usage:
    python scripts/create_book_ingestion_tables.py --client-id vervelyn_publishing

Requires:
    Client database URL stored in client_secrets table
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQL for creating tables
CREATE_BOOK_INGESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS book_ingestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_key TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    language_code TEXT NOT NULL,
    version TEXT NOT NULL,
    page_text TEXT NOT NULL,
    ocr_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint for preventing duplicates
    CONSTRAINT uq_book_page_version UNIQUE(book_key, page_number, version)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_book_key ON book_ingestions(book_key);
CREATE INDEX IF NOT EXISTS idx_language ON book_ingestions(language_code);
CREATE INDEX IF NOT EXISTS idx_version ON book_ingestions(version);
CREATE INDEX IF NOT EXISTS idx_created_at ON book_ingestions(created_at);
"""

CREATE_OBJECT_EMBEDDINGS_TABLE = """
-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS object_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES book_ingestions(id) ON DELETE CASCADE,
    embedding vector(1536),
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    embeddings_metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate chunks
    CONSTRAINT uq_source_chunk UNIQUE(source_id, chunk_index)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_source_id ON object_embeddings(source_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON object_embeddings USING ivfflat (embedding vector_cosine_ops);
"""

# Add update trigger for updated_at
CREATE_UPDATE_TRIGGER = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_book_ingestions_updated_at BEFORE UPDATE
    ON book_ingestions FOR EACH ROW EXECUTE PROCEDURE 
    update_updated_at_column();
"""


def get_database_url(client_id: str):
    """Get client database URL from secrets table."""
    from src.utils.secret_manager import SecretManager
    
    # Get from database secrets
    db_url = SecretManager.get_client_secret(client_id, "database_url")
    
    if not db_url:
        logger.error(f"Database URL not found for client {client_id}")
        logger.info(f"Please store database URL in client_secrets table for client {client_id}")
        sys.exit(1)
    
    return db_url


def create_tables(client_id: str = "vervelyn_publishing"):
    """Create client database tables."""
    try:
        # Get database URL
        db_url = get_database_url(client_id)
        logger.info(f"Connecting to {client_id} database...")
        
        # Create engine
        engine = create_engine(db_url)
        
        with engine.begin() as conn:
            # Create book_ingestions table
            logger.info("Creating book_ingestions table...")
            conn.execute(text(CREATE_BOOK_INGESTIONS_TABLE))
            
            # Create object_embeddings table
            logger.info("Creating object_embeddings table...")
            conn.execute(text(CREATE_OBJECT_EMBEDDINGS_TABLE))
            
            # Create update trigger
            logger.info("Creating update trigger...")
            conn.execute(text(CREATE_UPDATE_TRIGGER))
            
            # Verify tables were created
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('book_ingestions', 'object_embeddings')
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result]
            logger.info(f"Tables created successfully: {tables}")
            
            # Show table structures
            for table in tables:
                logger.info(f"\nTable structure for {table}:")
                result = conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """))
                for row in result:
                    logger.info(f"  - {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        
        logger.info("\n✅ All tables created successfully!")
        logger.info("Next steps:")
        logger.info("1. Store VERVELYN_DB_URL as Railway secret")
        logger.info("2. Implement multi-pass OCR tool")
        logger.info("3. Create database storage tool")
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create book ingestion tables for a client")
    parser.add_argument("--client-id", required=True, help="Client ID to create tables for")
    
    args = parser.parse_args()
    
    logger.info(f"Creating book ingestion tables for client: {args.client_id}")
    create_tables(args.client_id)