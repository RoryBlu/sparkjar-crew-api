#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Search vectorized job events
"""
import os
import sys
import json
import httpx
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path

from dotenv import load_dotenv
load_dotenv()

class VectorSearcher:
    """Search vectorized documents"""
    
    def __init__(self):
        self.embeddings_api_url = os.getenv("EMBEDDINGS_API_URL_TEST", "https://embeddings-development.up.railway.app")
        self.embedding_model = "Alibaba-NLP/gte-multilingual-base"
        
        # Database connection
        db_url = os.getenv("DATABASE_URL_POOLED", os.getenv("DATABASE_URL"))
        if not db_url:
            raise ValueError("DATABASE_URL not found")
        
        db_url = db_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.embeddings_api_url}/embed",
                json={
                    "inputs": [text],
                    "model": self.embedding_model
                }
            )
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return []
    
    async def search(self, query: str, job_id: str = None, limit: int = 10):
        """Search for similar documents"""
        logger.info(f"\n🔍 Searching for: '{query}'")
        logger.info("=" * 60)
        
        # Get query embedding
        logger.info("📡 Getting query embedding...")
        query_embedding = await self.get_embedding(query)
        
        if not query_embedding:
            logger.error("❌ Failed to get query embedding")
            return
        
        with self.Session() as session:
            # Build search query
            sql = """
                SELECT 
                    dv.id,
                    dv.source_id,
                    dv.chunk_index,
                    dv.chunk_text,
                    dv.metadata,
                    1 - (dv.embedding <=> :embedding) as similarity
                FROM document_vectors dv
                WHERE dv.source_table = 'crew_job_event'
            """
            
            params = {"embedding": str(query_embedding), "limit": limit}
            
            if job_id:
                sql += " AND dv.metadata->>'job_id' = :job_id"
                params["job_id"] = job_id
            
            sql += " ORDER BY dv.embedding <=> :embedding LIMIT :limit"
            
            result = session.execute(text(sql), params)
            
            logger.info(f"\n🎯 Top {limit} results:\n")
            
            for i, row in enumerate(result, 1):
                logger.info(f"{i}. Score: {row.similarity:.3f}")
                logger.info(f"   Event: {row.source_id}, Chunk: {row.chunk_index}")
                
                metadata = row.metadata
                logger.info(f"   Type: {metadata.get('event_type', 'unknown')}")
                logger.info(f"   Time: {metadata.get('event_time', 'unknown')}")
                
                # Show preview of text
                preview = row.chunk_text[:200].replace('\n', ' ')
                logger.info(f"   Text: {preview}...")
                logger.info()

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        logger.info("Usage: python search_job_vectors.py <query> [job_id]")
        sys.exit(1)
    
    query = sys.argv[1]
    job_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        searcher = VectorSearcher()
        await searcher.search(query, job_id)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())