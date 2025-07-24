#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Vectorize job events locally using remote embeddings server
"""
import os
import sys
import json
import httpx
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path

from dotenv import load_dotenv
load_dotenv()

class LocalVectorizer:
    """Vectorize job events using remote embeddings server"""
    
    def __init__(self):
        # Use the test URL for embeddings API (accessible from local)
        self.embeddings_api_url = os.getenv("EMBEDDINGS_API_URL_TEST", "https://embeddings-development.up.railway.app")
        self.embedding_model = "Alibaba-NLP/gte-multilingual-base"
        self.embedding_dimension = 768
        self.max_chunk_size = 2000
        self.chunk_overlap = 200
        
        # Database connection
        db_url = os.getenv("DATABASE_URL_POOLED", os.getenv("DATABASE_URL"))
        if not db_url:
            raise ValueError("DATABASE_URL not found")
        
        # Convert to sync URL
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
                    "id": str(row.id),  # Convert to string for text field
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
                if key in ['message', 'thought', 'action', 'observation', 'error', 'raw_output', 'output']:
                    # Important fields get full text
                    parts.append(f"{key}: {value}")
                elif isinstance(value, (str, int, float, bool)):
                    # Simple values
                    parts.append(f"{key}: {value}")
                elif isinstance(value, dict) and key == 'usage':
                    # Special handling for usage stats
                    parts.append(f"usage: {json.dumps(value)}")
                elif isinstance(value, dict):
                    # Complex objects get summarized
                    parts.append(f"{key}: {json.dumps(value)[:200]}...")
        
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
        """Get embeddings from the remote embeddings service"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"📡 Requesting embeddings for {len(texts)} texts from {self.embeddings_api_url}")
            response = await client.post(
                f"{self.embeddings_api_url}/embed",
                json={
                    "inputs": texts,
                    "model": self.embedding_model
                }
            )
            response.raise_for_status()
            
            result = response.json()
            # The API returns embeddings directly as a list
            if isinstance(result, list):
                embeddings = result
            else:
                embeddings = result.get("embeddings", [])
            logger.info(f"✅ Received {len(embeddings)} embeddings")
            return embeddings
    
    async def vectorize_job(self, job_id: str):
        """Vectorize all events for a job"""
        from sqlalchemy import text  # Import here to avoid issues
        logger.info(f"\n🚀 Starting vectorization for job {job_id}")
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
        
        with self.Session() as session:
            # Process events in batches
            batch_size = 3  # Even smaller batch size
            for i in range(0, len(events), batch_size):
                batch = events[i:i+batch_size]
                logger.info(f"\n📦 Processing event batch {i//batch_size + 1}/{(len(events) + batch_size - 1)//batch_size}")
                
                # Prepare all texts and chunks for this batch
                all_chunks = []
                chunk_to_event = {}
                
                for event in batch:
                    event_text = self.create_event_text(event)
                    chunks = self.chunk_text(event_text)
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        global_idx = len(all_chunks)
                        all_chunks.append(chunk['text'])
                        chunk_to_event[global_idx] = (event, chunk, chunk_idx, len(chunks))
                
                # Get embeddings for chunks in smaller sub-batches
                if all_chunks:
                    embeddings = []
                    embedding_batch_size = 5  # Process only 5 chunks at a time
                    
                    for j in range(0, len(all_chunks), embedding_batch_size):
                        sub_batch = all_chunks[j:j+embedding_batch_size]
                        logger.info(f"  📊 Getting embeddings for {len(sub_batch)} chunks...")
                        try:
                            sub_embeddings = await self.get_embeddings(sub_batch)
                            embeddings.extend(sub_embeddings)
                        except Exception as e:
                            logger.error(f"  ⚠️  Error getting embeddings: {e}")
                            logger.info(f"  🔄 Retrying with smaller batch...")
                            # Retry one by one
                            for text in sub_batch:
                                try:
                                    single_embedding = await self.get_embeddings([text])
                                    embeddings.extend(single_embedding)
                                except Exception as e2:
                                    logger.error(f"  ❌ Failed to get embedding: {e2}")
                                    embeddings.append([0.0] * self.embedding_dimension)  # Zero vector as fallback
                    
                    # Store embeddings
                    for idx, embedding in enumerate(embeddings):
                        event, chunk_info, chunk_idx, total_event_chunks = chunk_to_event[idx]
                        event_id = event['id']
                        
                        # Check if exists
                        result = session.execute(
                            text("""
                                SELECT 1 FROM document_vectors
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
                        
                        if exists:
                            # Update
                            session.execute(
                                text("""
                                    UPDATE document_vectors 
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
                                    "chunk_text": chunk_info['text'],
                                    "embedding": embedding,
                                    "metadata": json.dumps({
                                        "job_id": job_id,
                                        "event_id": event_id,
                                        "event_type": event.get('event_type'),
                                        "event_time": event.get('created_at'),
                                        "chunk_start": chunk_info['start'],
                                        "chunk_end": chunk_info['end'],
                                        "total_chunks": total_event_chunks,
                                        "model": self.embedding_model
                                    })
                                }
                            )
                        else:
                            # Insert
                            session.execute(
                                text("""
                                    INSERT INTO document_vectors 
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
                                    "chunk_text": chunk_info['text'],
                                    "embedding": embedding,
                                    "metadata": json.dumps({
                                        "job_id": job_id,
                                        "event_id": event_id,
                                        "event_type": event.get('event_type'),
                                        "event_time": event.get('created_at'),
                                        "chunk_start": chunk_info['start'],
                                        "chunk_end": chunk_info['end'],
                                        "total_chunks": total_event_chunks,
                                        "model": self.embedding_model
                                    })
                                }
                            )
                        
                        total_chunks += 1
                
                # Commit batch
                session.commit()
                processed_events += len(batch)
                logger.info(f"✅ Processed {processed_events}/{len(events)} events, {total_chunks} chunks total")
        
        logger.info(f"\n🎉 Vectorization complete!")
        logger.info(f"  - Total events: {len(events)}")
        logger.info(f"  - Total chunks: {total_chunks}")
        logger.info(f"  - Average chunks per event: {total_chunks / len(events):.2f}")

async def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        logger.info("Usage: python vectorize_job_locally.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    
    try:
        vectorizer = LocalVectorizer()
        await vectorizer.vectorize_job(job_id)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())