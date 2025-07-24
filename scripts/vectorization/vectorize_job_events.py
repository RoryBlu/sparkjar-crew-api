#!/usr/bin/env python3
"""
Vectorize job crew events using centralized ChromaDB service.

This script:
1. Loads crew job event data from JSON file
2. Generates embeddings using configured provider (OpenAI or custom)
3. Stores embeddings in centralized ChromaDB service at chroma-gjdq.railway.internal:8000
4. Provides similarity search testing functionality

Data is stored in both ChromaDB for vector search and PostgreSQL for structured data.
ChromaDB provides optimized vector similarity search capabilities.
"""
import json
import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from shared.services.chroma_service import get_chroma_service
from shared.services.object_embeddings_service import ObjectEmbeddingsService
from shared.database.connection import get_direct_session

# Try to import EmbeddingClient from the correct location
try:
    from services.crew_api.src.utils.embedding_client import EmbeddingClient
except ImportError:
    try:
        from src.sparkjar_crew.services.crew_api.utils.embedding_client import EmbeddingClient
    except ImportError:
        # Create a mock EmbeddingClient for testing
        class EmbeddingClient:
            def __init__(self):
                self.provider = type('Provider', (), {'value': 'mock'})()
                self.model_name = "mock-model"
                self.dimension = 768
            
            async def get_embeddings(self, texts):
                # Return mock embeddings for testing
                import random
                return [[random.random() for _ in range(self.dimension)] for _ in texts]

load_dotenv()

async def vectorize_job_events(job_data: Dict[str, Any]):
    """
    Vectorize job events and store in centralized ChromaDB service and PostgreSQL.
    """
    job_id = job_data.get('job_id')
    if not job_id:
        raise ValueError("Job ID is required")
    
    events = job_data.get("events", [])
    if not events:
        logger.info("No events found in job data")
        return
    
    logger.info(f"Processing {len(events)} events for job {job_id}...")
    
    # Initialize services
    embedding_client = EmbeddingClient()  # Uses EMBEDDING_PROVIDER from .env
    chroma_service = get_chroma_service()
    
    logger.info(f"Using embedding provider: {embedding_client.provider.value}")
    logger.info(f"Model: {embedding_client.model_name}")
    logger.info(f"Dimension: {embedding_client.dimension}")
    
    # Test ChromaDB connection
    health_check = await chroma_service.health_check()
    if not health_check:
        logger.error("ChromaDB service is not healthy, aborting vectorization")
        return
    
    # Create collection for this job
    collection_name = f"crew_job_{job_id}"
    collection = chroma_service.get_or_create_collection(
        name=collection_name,
        metadata={
            "job_id": job_id,
            "created_at": datetime.utcnow().isoformat(),
            "embedding_model": embedding_client.model_name,
            "embedding_provider": embedding_client.provider.value
        }
    )
    
    # Also store in PostgreSQL for structured queries
    async with get_direct_session() as session:
        embedding_service = ObjectEmbeddingsService(session)
        
        processed_count = 0
        batch_size = 10  # Process 10 events at a time
        
        # Prepare batch data for ChromaDB
        chroma_documents = []
        chroma_metadatas = []
        chroma_ids = []
        chroma_embeddings = []
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(events) + batch_size - 1)//batch_size}")
            
            for j, event in enumerate(batch):
                try:
                    event_id = event.get('id', f"event_{i+j}")
                    event_type = event.get('event_type', 'unknown')
                    
                    # Create document text from event data
                    document_text = create_event_document(event)
                    
                    # Generate embedding
                    embeddings = await embedding_client.get_embeddings([document_text])
                    if not embeddings:
                        logger.warning(f"Failed to generate embedding for event {event_id}")
                        continue
                    
                    # Create metadata
                    metadata = {
                        "job_id": job_id,
                        "event_type": event_type,
                        "event_id": str(event_id),
                        "created_at": event.get("created_at", datetime.utcnow().isoformat()),
                        "event_index": i + j,
                        "embedding_model": embedding_client.model_name,
                        "embedding_provider": embedding_client.provider.value
                    }
                    
                    # Add important fields from event_data to metadata
                    event_data = event.get("event_data", {})
                    if isinstance(event_data, dict):
                        for key in ["level", "task_name", "agent_name", "tool_name", "status"]:
                            if key in event_data:
                                metadata[f"event_{key}"] = str(event_data[key])[:100]
                    
                    # Prepare ChromaDB data
                    chroma_documents.append(document_text)
                    chroma_metadatas.append(metadata)
                    chroma_ids.append(f"{job_id}_event_{event_id}")
                    chroma_embeddings.append(embeddings[0])
                    
                    # Store in PostgreSQL for structured queries
                    client_user_id = job_data.get('client_user_id')
                    if client_user_id and isinstance(client_user_id, str):
                        try:
                            client_id = uuid.UUID(client_user_id)
                        except:
                            client_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"job.{job_id}")
                    else:
                        client_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"job.{job_id}")
                    
                    await embedding_service.store_embedding(
                        client_id=client_id,
                        sj_table="crew_job_event",
                        sj_column="event_data", 
                        vectorize_text=document_text,
                        embedding=embeddings[0],
                        metadata=metadata
                    )
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing event {i+j}: {e}")
                    continue
            
            # Store batch in ChromaDB
            if chroma_documents:
                success = chroma_service.add_documents(
                    collection_name=collection_name,
                    documents=chroma_documents,
                    metadatas=chroma_metadatas,
                    ids=chroma_ids,
                    embeddings=chroma_embeddings
                )
                
                if success:
                    logger.info(f"Stored {len(chroma_documents)} events in ChromaDB")
                else:
                    logger.error(f"Failed to store batch in ChromaDB")
                
                # Clear batch data
                chroma_documents.clear()
                chroma_metadatas.clear()
                chroma_ids.clear()
                chroma_embeddings.clear()
            
            logger.info(f"Processed {processed_count}/{len(events)} events so far...")
    
    logger.info(f"\nVectorization complete!")
    logger.info(f"Total events processed: {processed_count}")
    logger.info(f"ChromaDB collection: {collection_name}")
    
    # Test similarity search
    if processed_count > 0:
        await test_similarity_search(job_id, collection_name)

def create_event_document(event: Dict[str, Any]) -> str:
    """Create searchable text representation of an event"""
    parts = []
    
    # Add event type
    parts.append(f"Event Type: {event.get('event_type', 'unknown')}")
    
    # Add timestamp
    if event.get("created_at"):
        parts.append(f"Time: {event['created_at']}")
    
    # Process event data
    event_data = event.get("event_data", {})
    if isinstance(event_data, dict):
        for key, value in event_data.items():
            if key in ["message", "thought", "action", "observation", "error"]:
                # Important fields get full text
                parts.append(f"{key}: {value}")
            elif isinstance(value, (str, int, float, bool)):
                # Simple values
                parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                # Complex objects get summarized
                parts.append(f"{key}: {json.dumps(value)[:200]}...")
    
    return "\n".join(parts)

async def test_similarity_search(job_id: str, collection_name: str):
    """Test similarity search on stored embeddings in both ChromaDB and PostgreSQL"""
    logger.info(f"\nTesting similarity search for job {job_id}...")
    
    try:
        embedding_client = EmbeddingClient()
        chroma_service = get_chroma_service()
        
        # Test queries
        test_queries = [
            "research findings", 
            "agent task execution",
            "error or failure"
        ]
        
        for query in test_queries:
            logger.info(f"\nSearching for: '{query}'")
            
            # Generate query embedding
            query_embeddings = await embedding_client.get_embeddings([query])
            if not query_embeddings:
                logger.warning("Failed to generate query embedding")
                continue
            
            # Test ChromaDB search
            logger.info("Testing ChromaDB similarity search...")
            try:
                chroma_results = chroma_service.query_collection(
                    collection_name=collection_name,
                    query_embeddings=[query_embeddings[0]],
                    n_results=3
                )
                
                if chroma_results and 'documents' in chroma_results:
                    documents = chroma_results['documents'][0] if chroma_results['documents'] else []
                    metadatas = chroma_results['metadatas'][0] if chroma_results.get('metadatas') else []
                    distances = chroma_results['distances'][0] if chroma_results.get('distances') else []
                    
                    logger.info(f"ChromaDB found {len(documents)} similar events:")
                    for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                        logger.info(f"  {i+1}. Distance: {distance:.3f}")
                        logger.info(f"     Event: {metadata.get('event_type', 'unknown')}")
                        logger.info(f"     Preview: {doc[:100]}...")
                else:
                    logger.info("No results from ChromaDB search")
                    
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}")
            
            # Test PostgreSQL search for comparison
            logger.info("Testing PostgreSQL similarity search...")
            try:
                async with get_direct_session() as session:
                    embedding_service = ObjectEmbeddingsService(session)
                    
                    # Use same client_id logic as in storage
                    client_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"job.{job_id}")
                    
                    # Search for similar events
                    results = await embedding_service.similarity_search(
                        client_id=client_id,
                        query_embedding=query_embeddings[0],
                        sj_table="crew_job_event",
                        limit=3,
                        similarity_threshold=0.5
                    )
                    
                    logger.info(f"PostgreSQL found {len(results)} similar events:")
                    for i, (embedding_record, similarity_score) in enumerate(results):
                        logger.info(f"  {i+1}. Score: {similarity_score:.3f}")
                        logger.info(f"     Event: {embedding_record.column_metadata.get('event_type', 'unknown')}")
                        logger.info(f"     Preview: {embedding_record.vectorize_text[:100]}...")
                        
            except Exception as e:
                logger.error(f"PostgreSQL search failed: {e}")
    
    except Exception as e:
        logger.error(f"Error during similarity search test: {e}")

async def main():
    """Main function to process job data"""
    # Load job data - can be from file or passed as argument
    job_file = "/tmp/job_result.json"
    if len(sys.argv) > 1:
        job_file = sys.argv[1]
    
    if not os.path.exists(job_file):
        logger.info(f"Job file not found: {job_file}")
        logger.info("Usage: python vectorize_job_events_supabase.py [job_file.json]")
        sys.exit(1)
    
    with open(job_file, "r") as f:
        job_data = json.load(f)
    
    await vectorize_job_events(job_data)

if __name__ == "__main__":
    asyncio.run(main())