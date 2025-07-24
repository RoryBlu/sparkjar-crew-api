#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Vectorize job events using OpenAI embeddings
"""
import os
import sys
import json
import openai
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time

# Add parent directory to path

from dotenv import load_dotenv
load_dotenv()

class OpenAIVectorizer:
    """Vectorize job events using OpenAI embeddings"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        openai.api_key = self.openai_api_key
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimension = 1536  # OpenAI text-embedding-3-small dimension
        self.max_chunk_size = 2000
        self.chunk_overlap = 200
        
        # Database connection
        db_url = os.getenv("DATABASE_URL_POOLED", os.getenv("DATABASE_URL"))
        if not db_url:
            raise ValueError("DATABASE_URL not found")
        
        db_url = db_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_job_events(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all events for a job"""
        with self.Session() as session:
            result = session.execute(
                text("""
                    SELECT id, event_type, event_data, event_time
                    FROM crew_job_event
                    WHERE job_id = :job_id
                    ORDER BY event_time, id
                """),
                {"job_id": job_id}
            )
            
            return [
                {
                    "id": str(row.id),
                    "event_type": row.event_type,
                    "event_data": row.event_data,
                    "created_at": row.event_time.isoformat() if row.event_time else None
                }
                for row in result
            ]
    
    def create_event_text(self, event: Dict[str, Any]) -> str:
        """Create searchable text representation of an event"""
        parts = []
        
        # Add event type
        parts.append(f"Event Type: {event.get('event_type', 'unknown')}")
        
        # Add timestamp
        if event.get('created_at'):
            parts.append(f"Time: {event['created_at']}")
        
        # Process event data
        event_data = event.get('event_data', {})
        if isinstance(event_data, dict):
            for key, value in event_data.items():
                if key in ['message', 'thought', 'action', 'observation', 'error', 'raw_output', 
                          'output', 'result', 'task', 'agent', 'content', 'query', 'response']:
                    # Important fields get full text
                    parts.append(f"{key}: {value}")
                elif key == 'messages' and isinstance(value, list):
                    # Handle message arrays
                    for msg in value:
                        if isinstance(msg, dict) and 'content' in msg:
                            parts.append(f"message_{msg.get('role', 'unknown')}: {msg['content']}")
                elif isinstance(value, (str, int, float, bool)):
                    # Simple values
                    parts.append(f"{key}: {value}")
                elif isinstance(value, dict) and key == 'usage':
                    # Special handling for usage stats
                    parts.append(f"usage: {json.dumps(value)}")
                elif isinstance(value, dict):
                    # Complex objects get summarized
                    parts.append(f"{key}: {json.dumps(value)[:500]}...")
        
        return "\n".join(parts)
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        if len(text) <= self.max_chunk_size:
            return [{"text": text, "start": 0, "end": len(text)}]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + self.max_chunk_size
            
            # Try to break at a newline or space
            if end < len(text):
                # Look for newline first
                newline_pos = text.rfind('\n', start + self.chunk_overlap, end)
                if newline_pos > start:
                    end = newline_pos + 1
                else:
                    # Look for space
                    space_pos = text.rfind(' ', start + self.chunk_overlap, end)
                    if space_pos > start:
                        end = space_pos + 1
            
            chunks.append({
                "text": text[start:end],
                "start": start,
                "end": end
            })
            
            # Move start position (with overlap)
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI API with retry logic"""
        max_retries = 5
        base_delay = 1
        
        for retry in range(max_retries):
            try:
                logger.info(f"  📡 Requesting OpenAI embeddings for {len(texts)} texts...")
                
                # OpenAI's new client
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                
                response = client.embeddings.create(
                    model=self.embedding_model,
                    input=texts
                )
                
                embeddings = [item.embedding for item in response.data]
                logger.info(f"  ✅ Received {len(embeddings)} embeddings")
                return embeddings
                
            except Exception as e:
                delay = base_delay * (2 ** retry)
                logger.error(f"  ⚠️  Error: {e}")
                
                if retry < max_retries - 1:
                    logger.info(f"  ⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"  ❌ Failed after {max_retries} retries")
                    # Return zero vectors as fallback
                    return [[0.0] * self.embedding_dimension for _ in texts]
    
    async def vectorize_job(self, job_id: str):
        """Vectorize all events for a job"""
        from sqlalchemy import text  # Import here to avoid issues
        logger.info(f"\n🚀 Starting OpenAI vectorization for job {job_id}")
        logger.info("=" * 60)
        
        
        # Get job events
        logger.info("📥 Fetching job events...")
        events = self.get_job_events(job_id)
        logger.info(f"✅ Found {len(events)} events")
        
        if not events:
            logger.info("❌ No events found for this job")
            return
        
        total_chunks = 0
        processed_events = 0
        failed_events = 0
        
        with self.Session() as session:
            # Process events one by one for reliability
            for event_idx, event in enumerate(events):
                try:
                    logger.info(f"\n📦 Processing event {event_idx + 1}/{len(events)} (ID: {event['id']}, Type: {event['event_type']})")
                    
                    # Create text representation
                    event_text = self.create_event_text(event)
                    
                    # Chunk the text
                    chunks = self.chunk_text(event_text)
                    logger.info(f"  📄 Created {len(chunks)} chunks")
                    
                    # Process chunks in small batches
                    chunk_batch_size = 3
                    for i in range(0, len(chunks), chunk_batch_size):
                        chunk_batch = chunks[i:i+chunk_batch_size]
                        texts = [chunk['text'] for chunk in chunk_batch]
                        
                        # Get embeddings with retry
                        embeddings = await self.get_embeddings(texts)
                        
                        # Store each chunk
                        for j, (chunk, embedding) in enumerate(zip(chunk_batch, embeddings)):
                            chunk_idx = i + j
                            event_id = event['id']
                            
                            # Check if exists
                            result = session.execute(
                                text("""
                                    SELECT 1 FROM document_vectors_openai
                                    WHERE source_table = :source_table 
                                    AND source_id = :source_id
                                    AND chunk_index = :chunk_index
                                """),
                                {
                                    "source_table": "crew_job_event",
                                    "source_id": event_id,
                                    "chunk_index": chunk_idx
                                }
                            )
                            
                            exists = result.scalar() is not None
                            
                            metadata = {
                                "job_id": job_id,
                                "event_id": event_id,
                                "event_type": event.get('event_type'),
                                "event_time": event.get('created_at'),
                                "event_idx": event_idx,
                                "chunk_start": chunk['start'],
                                "chunk_end": chunk['end'],
                                "total_chunks": len(chunks),
                                "model": self.embedding_model,
                                "embedding_dimension": self.embedding_dimension
                            }
                            
                            if exists:
                                # Update existing
                                session.execute(
                                    text("""
                                        UPDATE document_vectors_openai 
                                        SET chunk_text = :chunk_text,
                                            embedding = :embedding,
                                            metadata = :metadata,
                                            updated_at = NOW()
                                        WHERE source_table = :source_table 
                                          AND source_id = :source_id
                                          AND chunk_index = :chunk_index
                                    """),
                                    {
                                        "source_table": "crew_job_event",
                                        "source_id": event_id,
                                        "chunk_index": chunk_idx,
                                        "chunk_text": chunk['text'],
                                        "embedding": embedding,
                                        "metadata": json.dumps(metadata)
                                    }
                                )
                            else:
                                # Insert new
                                session.execute(
                                    text("""
                                        INSERT INTO document_vectors_openai 
                                        (source_table, source_id, source_column, chunk_index, 
                                         chunk_text, embedding, metadata)
                                        VALUES 
                                        (:source_table, :source_id, :source_column, :chunk_index,
                                         :chunk_text, :embedding, :metadata)
                                    """),
                                    {
                                        "source_table": "crew_job_event",
                                        "source_column": "event_data",
                                        "source_id": event_id,
                                        "chunk_index": chunk_idx,
                                        "chunk_text": chunk['text'],
                                        "embedding": embedding,
                                        "metadata": json.dumps(metadata)
                                    }
                                )
                            
                            total_chunks += 1
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.5)
                    
                    # Commit after each event
                    session.commit()
                    processed_events += 1
                    logger.info(f"  ✅ Event processed: {total_chunks} total chunks so far")
                    
                except Exception as e:
                    logger.error(f"  ❌ Failed to process event {event['id']}: {e}")
                    failed_events += 1
                    session.rollback()
                    continue
        
        logger.info(f"\n🎉 Vectorization complete!")
        logger.info(f"  - Total events: {len(events)}")
        logger.info(f"  - Processed events: {processed_events}")
        logger.error(f"  - Failed events: {failed_events}")
        logger.info(f"  - Total chunks: {total_chunks}")
        logger.info(f"  - Average chunks per event: {total_chunks / processed_events if processed_events > 0 else 0:.2f}")

async def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        logger.info("Usage: python vectorize_job_openai.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    
    try:
        vectorizer = OpenAIVectorizer()
        await vectorizer.vectorize_job(job_id)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())