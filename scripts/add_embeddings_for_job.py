#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Simple script to add embeddings for a specific job
Can be run on Railway where database connections work
"""

import os
import sys
from datetime import datetime

# Add the parent directory to Python path

def main():
    """Add embeddings for the Railway job"""
    # Import after path is set
    from scripts.migrate_to_pgvector import (
        create_pgvector_extension,
        add_vector_column,
        embed_job_events,
        test_vector_search
    )
    import psycopg2
    
    # Job ID from Railway
    job_id = "111c213e-a1a2-445a-bcb5-8ee11822a80f"
    
    logger.info(f"🚀 Adding embeddings for job: {job_id}")
    logger.info("="*60)
    
    # Get database URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("ERROR: DATABASE_URL not found in environment")
        return
    
    # Remove asyncpg for psycopg2
    db_url = DATABASE_URL.replace("+asyncpg", "")
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(db_url)
        logger.info("✅ Connected to PostgreSQL")
        
        # Run the embedding process
        embed_job_events(conn, job_id)
        
        # Test with some queries
        test_queries = [
            "Michael Williams entrepreneur",
            "tool execution",
            "memory observation",
            "email sent"
        ]
        
        for query in test_queries:
            test_vector_search(conn, job_id, query)
        
        logger.info("\n✅ Embeddings added successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()