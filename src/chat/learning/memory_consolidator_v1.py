"""
Memory Consolidation Pipeline for Learning Loop.

KISS principles:
- Simple crew job creation
- Basic retry logic
- Progress tracking without complexity
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """
    Consolidates conversation insights via Memory Maker Crew.
    
    KISS: Queue jobs and track progress, that's it.
    """
    
    def __init__(self, crew_api_url: str, api_token: str):
        """
        Initialize consolidator.
        
        Args:
            crew_api_url: URL for crew API
            api_token: Authentication token
        """
        self.crew_api_url = crew_api_url
        self.api_token = api_token
        self.pending_jobs = {}  # Track pending consolidation jobs
        
    async def consolidate_conversation(
        self,
        session_id: UUID,
        entity_id: str,
        mode: str,
        patterns: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Queue conversation for consolidation.
        
        Args:
            session_id: Chat session ID
            entity_id: Conversation entity ID
            mode: Chat mode used
            patterns: Extracted patterns
            
        Returns:
            Job ID if queued successfully
        """
        try:
            job_request = self._create_consolidation_job(
                session_id,
                entity_id,
                mode,
                patterns
            )
            
            # Queue the job
            job_id = await self._queue_crew_job(job_request)
            
            if job_id:
                # Track the job
                self.pending_jobs[job_id] = {
                    "session_id": str(session_id),
                    "entity_id": entity_id,
                    "created_at": datetime.utcnow(),
                    "status": "queued"
                }
                
                logger.info(f"Queued consolidation job: {job_id}")
                
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to consolidate conversation: {e}")
            return None
            
    async def consolidate_patterns(
        self,
        patterns: List[Dict[str, Any]],
        source_sessions: List[UUID]
    ) -> Optional[str]:
        """
        Consolidate multiple patterns into insights.
        
        Args:
            patterns: Successful patterns to consolidate
            source_sessions: Source session IDs
            
        Returns:
            Job ID if queued successfully
        """
        try:
            job_request = {
                "job_key": "memory_maker_crew",
                "request_data": {
                    "source_type": "pattern_consolidation",
                    "patterns": patterns,
                    "source_sessions": [str(s) for s in source_sessions],
                    "consolidation_type": "pattern_insights",
                    "metadata": {
                        "pattern_count": len(patterns),
                        "consolidation_timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
            
            job_id = await self._queue_crew_job(job_request)
            
            if job_id:
                self.pending_jobs[job_id] = {
                    "type": "pattern_consolidation",
                    "pattern_count": len(patterns),
                    "created_at": datetime.utcnow(),
                    "status": "queued"
                }
                
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to consolidate patterns: {e}")
            return None
            
    async def check_job_status(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Check consolidation job status.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Job status information
        """
        try:
            # In production, this would call the crew API
            # For now, simulate status check
            if job_id in self.pending_jobs:
                job_info = self.pending_jobs[job_id]
                
                # Simulate job progression
                created_at = job_info["created_at"]
                elapsed = (datetime.utcnow() - created_at).total_seconds()
                
                if elapsed < 30:
                    status = "running"
                elif elapsed < 60:
                    status = "completed"
                else:
                    status = "failed"
                    
                job_info["status"] = status
                return job_info
                
            return {"status": "not_found"}
            
        except Exception as e:
            logger.error(f"Failed to check job status: {e}")
            return {"status": "error", "error": str(e)}
            
    async def retry_failed_jobs(self) -> int:
        """
        Retry failed consolidation jobs.
        
        Returns:
            Number of jobs retried
        """
        retried = 0
        
        for job_id, job_info in list(self.pending_jobs.items()):
            if job_info.get("status") == "failed":
                retry_count = job_info.get("retry_count", 0)
                
                if retry_count < 3:  # Max 3 retries
                    # Update retry count
                    job_info["retry_count"] = retry_count + 1
                    job_info["status"] = "retrying"
                    
                    # In production, re-queue the job
                    logger.info(f"Retrying job {job_id} (attempt {retry_count + 1})")
                    retried += 1
                    
        return retried
        
    def get_consolidation_progress(self) -> Dict[str, Any]:
        """
        Get overall consolidation progress.
        
        Returns:
            Progress summary
        """
        total = len(self.pending_jobs)
        if total == 0:
            return {
                "total_jobs": 0,
                "status": "idle"
            }
            
        status_counts = {}
        for job_info in self.pending_jobs.values():
            status = job_info.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
        return {
            "total_jobs": total,
            "queued": status_counts.get("queued", 0),
            "running": status_counts.get("running", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "completion_rate": status_counts.get("completed", 0) / total if total > 0 else 0
        }
        
    def _create_consolidation_job(
        self,
        session_id: UUID,
        entity_id: str,
        mode: str,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create job request for conversation consolidation."""
        return {
            "job_key": "memory_maker_crew",
            "request_data": {
                "source_type": "chat_conversation",
                "session_id": str(session_id),
                "entity_id": entity_id,
                "mode": mode,
                "consolidation_type": "conversation_insights",
                "patterns": patterns,
                "metadata": {
                    "consolidation_timestamp": datetime.utcnow().isoformat(),
                    "pattern_count": len(patterns)
                }
            }
        }
        
    async def _queue_crew_job(
        self,
        job_request: Dict[str, Any]
    ) -> Optional[str]:
        """
        Queue job with crew API.
        
        In production, this would make an HTTP request to crew API.
        """
        try:
            # Simulate job creation
            # In production:
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(
            #         f"{self.crew_api_url}/crew_job",
            #         json=job_request,
            #         headers={"Authorization": f"Bearer {self.api_token}"}
            #     )
            #     result = response.json()
            #     return result.get("job_id")
            
            # For now, return simulated job ID
            job_id = str(uuid4())
            logger.info(f"Simulated crew job creation: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to queue crew job: {e}")
            return None
            
    async def cleanup_old_jobs(self, days: int = 7):
        """
        Clean up old completed jobs.
        
        Args:
            days: Remove jobs older than this many days
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        removed = 0
        
        for job_id, job_info in list(self.pending_jobs.items()):
            created_at = job_info.get("created_at")
            status = job_info.get("status")
            
            if created_at < cutoff and status in ["completed", "failed"]:
                del self.pending_jobs[job_id]
                removed += 1
                
        if removed > 0:
            logger.info(f"Cleaned up {removed} old consolidation jobs")