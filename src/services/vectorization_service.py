"""
Vectorization service for storing document embeddings in PostgreSQL
Uses the generic document_vectors table with pgvector
"""

import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from config import EMBEDDINGS_API_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSION
from utils.embedding_client import EmbeddingClient

from sqlalchemy import select, text
from database.connection import get_direct_session

logger = logging.getLogger(__name__)

class VectorizationService:
    """Service for vectorizing documents and storing in PostgreSQL"""

    def __init__(self):
        # Use the new embedding client with provider switching
        self.embedding_client = EmbeddingClient()
        self.max_chunk_size = 2000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks

    async def vectorize_job_events(
        self, job_id: str, events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Vectorize job events and store in document_vectors table

        Args:
            job_id: The job ID
            events: List of event dictionaries from crew_job_event

        Returns:
            Summary of vectorization results
        """
        total_chunks = 0
        processed_events = 0

        async with get_direct_session() as session:
            try:
                # Process each event
                for event in events:
                    event_id = event.get("id")
                    if not event_id:
                        continue

                    # Create text representation of event
                    event_text = self._create_event_text(event)

                    # Chunk the text if needed
                    chunks = self._chunk_text(event_text)

                    # Get embeddings for all chunks
                    embeddings = await self._get_embeddings(
                        [chunk["text"] for chunk in chunks]
                    )

                    # Store each chunk with its embedding
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        # Check if this chunk already exists
                        existing = await session.execute(
                            select(text("1"))
                            .where(
                                text(
                                    """
                                    source_table = :source_table 
                                    AND source_id = :source_id 
                                    AND chunk_index = :chunk_index
                                """
                                )
                            )
                            .params(
                                source_table="crew_job_event",
                                source_id=event_id,
                                chunk_index=i,
                            )
                        )

                        if existing.scalar():
                            # Update existing
                            await session.execute(
                                text(
                                    """
                                    UPDATE document_vectors 
                                    SET chunk_text = :chunk_text,
                                        embedding = :embedding,
                                        metadata = :metadata,
                                        updated_at = NOW()
                                    WHERE source_table = :source_table 
                                      AND source_id = :source_id 
                                      AND chunk_index = :chunk_index
                                """
                                ),
                                {
                                    "source_table": "crew_job_event",
                                    "source_id": event_id,
                                    "chunk_index": i,
                                    "chunk_text": chunk["text"],
                                    "embedding": embedding,
                                    "metadata": json.dumps(
                                        {
                                            "job_id": job_id,
                                            "event_type": event.get("event_type"),
                                            "event_time": event.get("created_at"),
                                            "chunk_start": chunk["start"],
                                            "chunk_end": chunk["end"],
                                            "total_chunks": len(chunks),
                                            "model": self.embedding_client.model_name,
                                        }
                                    ),
                                },
                            )
                        else:
                            # Insert new
                            await session.execute(
                                text(
                                    """
                                    INSERT INTO document_vectors 
                                    (source_table, source_id, source_column, chunk_index, 
                                     chunk_text, embedding, metadata)
                                    VALUES 
                                    (:source_table, :source_id, :source_column, :chunk_index,
                                     :chunk_text, :embedding, :metadata)
                                """
                                ),
                                {
                                    "source_table": "crew_job_event",
                                    "source_id": event_id,
                                    "source_column": "event_data",
                                    "chunk_index": i,
                                    "chunk_text": chunk["text"],
                                    "embedding": embedding,
                                    "metadata": json.dumps(
                                        {
                                            "job_id": job_id,
                                            "event_type": event.get("event_type"),
                                            "event_time": event.get("created_at"),
                                            "chunk_start": chunk["start"],
                                            "chunk_end": chunk["end"],
                                            "total_chunks": len(chunks),
                                            "model": self.embedding_client.model_name,
                                        }
                                    ),
                                },
                            )

                        total_chunks += 1

                    processed_events += 1

                    # Commit periodically
                    if processed_events % 10 == 0:
                        await session.commit()
                        logger.info(
                            f"Processed {processed_events}/{len(events)} events"
                        )

                # Final commit
                await session.commit()

                return {
                    "total_events": len(events),
                    "processed_events": processed_events,
                    "total_chunks": total_chunks,
                    "avg_chunks_per_event": (
                        total_chunks / processed_events if processed_events > 0 else 0
                    ),
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Vectorization failed: {e}")
                raise

    def _create_event_text(self, event: Dict[str, Any]) -> str:
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

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
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
                newline_pos = text.rfind("\n", start + self.chunk_overlap, end)
                if newline_pos > start:
                    end = newline_pos + 1
                else:
                    # Look for space
                    space_pos = text.rfind(" ", start + self.chunk_overlap, end)
                    if space_pos > start:
                        end = space_pos + 1

            chunks.append({"text": text[start:end], "start": start, "end": end})

            # Move start position (with overlap)
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using the configured provider (OpenAI or custom)"""
        return await self.embedding_client.get_embeddings(texts)

    async def search_similar(
        self,
        query: str,
        source_table: Optional[str] = None,
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity

        Args:
            query: Search query text
            source_table: Optional filter by source table
            limit: Maximum results to return
            metadata_filter: Optional JSONB metadata filters

        Returns:
            List of similar documents with scores
        """
        # Get embedding for query
        embeddings = await self.embedding_client.get_embeddings([query])
        if not embeddings:
            return []

        query_embedding = embeddings[0]

        async with get_direct_session() as session:
            # Build query
            sql = """
                SELECT 
                    id,
                    source_table,
                    source_id,
                    chunk_index,
                    chunk_text,
                    metadata,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM document_vectors
                WHERE 1=1
            """

            params = {"embedding": query_embedding, "limit": limit}

            if source_table:
                sql += " AND source_table = :source_table"
                params["source_table"] = source_table

            if metadata_filter:
                for key, value in metadata_filter.items():
                    sql += f" AND metadata->'{key}' = :meta_{key}"
                    params[f"meta_{key}"] = json.dumps(value)

            sql += " ORDER BY embedding <=> :embedding::vector LIMIT :limit"

            result = await session.execute(text(sql), params)

            return [
                {
                    "id": str(row.id),
                    "source_table": row.source_table,
                    "source_id": str(row.source_id),
                    "chunk_index": row.chunk_index,
                    "text": row.chunk_text,
                    "metadata": row.metadata,
                    "similarity": float(row.similarity),
                }
                for row in result
            ]
