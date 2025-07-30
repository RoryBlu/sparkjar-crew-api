#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Debug script to query crew_job_event table for a specific job_id"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
database_url = os.getenv('DATABASE_URL_DIRECT') or os.getenv('DATABASE_URL')
if not database_url:
    logger.error('Error: No database URL found in environment')
    logger.info('Please make sure you have a .env file with DATABASE_URL_DIRECT or DATABASE_URL set')
    sys.exit(1)

# Replace asyncpg with psycopg2 for synchronous connection
if 'asyncpg' in database_url:
    database_url = database_url.replace('postgresql+asyncpg', 'postgresql')

# Create engine
engine = create_engine(database_url)

# Job ID to query
job_id = '5a168675-3352-40e4-917a-44fd955e31e7'

# First, let's check the table schema
schema_query = '''
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'crew_job_event'
ORDER BY ordinal_position;
'''

logger.info("Checking crew_job_event table schema...")
try:
    with engine.connect() as conn:
        result = conn.execute(text(schema_query))
        columns = result.fetchall()
        logger.info("\nTable columns:")
        for col in columns:
            logger.info(f"  - {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
except Exception as e:
    logger.error(f"Error checking schema: {e}")

logger.info("\n" + "=" * 100 + "\n")

# Query for the last 5 events based on actual schema
query = '''
SELECT 
    id,
    job_id,
    event_type,
    event_data,
    event_time
FROM crew_job_event
WHERE job_id = :job_id
ORDER BY event_time DESC
LIMIT 5
'''

try:
    with engine.connect() as conn:
        result = conn.execute(text(query), {'job_id': job_id})
        events = result.fetchall()
        
        if not events:
            logger.info(f'No events found for job_id: {job_id}')
        else:
            logger.info(f'Found {len(events)} events (showing last 5):')
            logger.info('=' * 100)
            
            for idx, event in enumerate(events):
                logger.info(f'\nEvent {idx + 1}:')
                logger.info(f'  ID: {event.id}')
                logger.info(f'  Job ID: {event.job_id}')
                logger.info(f'  Event Type: {event.event_type}')
                logger.info(f'  Event Time: {event.event_time}')
                
                # Pretty print event data
                try:
                    event_data = json.loads(event.event_data) if isinstance(event.event_data, str) else event.event_data
                    logger.info('  Event Data:')
                    logger.info(json.dumps(event_data, indent=4))
                except Exception as e:
                    logger.info(f'  Event Data (raw): {event.event_data}')
                    logger.error(f'  Error parsing JSON: {e}')
                
                logger.info('-' * 100)
                
except Exception as e:
    logger.error(f'Error querying database: {e}')
    import traceback
    traceback.print_exc()