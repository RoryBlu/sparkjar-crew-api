"""
Job service for managing crew execution and job lifecycle.
Handles database operations, job queuing, and crew orchestration.
"""

import asyncio
import logging
import uuid
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from api.models import CrewJobRequest, JobStatus, JobStatusResponse
from database.connection import get_direct_session
from database.models import CrewJobEvent, CrewJobs

from utils.crew_logger import CrewExecutionLogger
from utils.enhanced_crew_logger import EnhancedCrewLogger

logger = logging.getLogger(__name__)

class JobService:
    """Service for managing crew jobs and execution."""

    def __init__(self):
        pass  # No crew registry needed

    async def create_job(self, job_request: CrewJobRequest) -> str:
        """
        Create a new crew job in the database.

        Args:
            job_request: Job creation request

        Returns:
            Job ID string
        """

        job_id = str(uuid.uuid4())

        try:
            async with get_direct_session() as session:
                # Create job record
                job = CrewJobs(
                    id=job_id,
                    job_key=job_request.job_key,
                    client_user_id=job_request.client_user_id,
                    actor_type=job_request.actor_type,
                    actor_id=job_request.actor_id,
                    status=JobStatus.QUEUED,
                    attempts=0,  # Initialize attempts to 0
                    payload=job_request.dict(),
                    created_at=datetime.utcnow(),
                )

                session.add(job)
                await session.commit()

                # Log job creation using centralized crew logger
                crew_logger = CrewExecutionLogger(job_id)
                await crew_logger.log_crew_step(
                    "job_created",
                    {
                        "message": f"Job created with key: {job_request.job_key}",
                        "job_key": job_request.job_key,
                        "payload": job_request.dict(),
                    },
                )

                logger.info(
                    f"Created job {job_id} for user {job_request.client_user_id}"
                )
                return job_id

        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    async def create_job_from_validated_data(
        self, validated_data: Dict[str, Any]
    ) -> str:
        """
        Create a new crew job from pre-validated data dictionary.

        Args:
            validated_data: Dictionary containing validated job data including
                          job_key, client_user_id, actor_type, actor_id, etc.

        Returns:
            Job ID string

        Raises:
            ValueError: If required fields missing
        """
        # Extract required fields
        job_key = validated_data.get("job_key")
        client_user_id = validated_data.get("client_user_id")
        actor_type = validated_data.get("actor_type")
        actor_id = validated_data.get("actor_id")

        # Validate required fields
        if not all([job_key, client_user_id, actor_type, actor_id]):
            missing = [
                k
                for k, v in {
                    "job_key": job_key,
                    "client_user_id": client_user_id,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                }.items()
                if not v
            ]
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        job_id = str(uuid.uuid4())

        try:
            async with get_direct_session() as session:
                # Create job record
                job = CrewJobs(
                    id=job_id,
                    job_key=job_key,
                    client_user_id=client_user_id,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    status=JobStatus.QUEUED,
                    attempts=0,  # Initialize attempts to 0
                    created_at=datetime.utcnow(),
                    payload=validated_data,  # Store the full validated data
                )

                session.add(job)
                await session.commit()

                # Log job creation using centralized crew logger
                crew_logger = CrewExecutionLogger(job_id)
                await crew_logger.log_crew_step(
                    "job_created",
                    {
                        "job_key": job_key,
                        "client_user_id": client_user_id,
                        "actor_type": actor_type,
                        "actor_id": actor_id,
                    },
                )

                logger.info(f"Created job {job_id} with job_key={job_key}")
                return job_id

        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise ValueError(f"Database error: {e}")

    async def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """
        Get job status and details.

        Args:
            job_id: Job identifier

        Returns:
            Job status response or None if not found
        """
        try:
            async with get_direct_session() as session:
                # Get job
                job = await session.get(CrewJobs, job_id)
                if not job:
                    return None

                # Get job events
                events_result = await session.execute(
                    select(CrewJobEvent)
                    .where(CrewJobEvent.job_id == job_id)
                    .order_by(CrewJobEvent.event_time)
                )
                events = events_result.scalars().all()

                # Build response
                return JobStatusResponse(
                    job_id=str(job.id),  # Convert UUID to string
                    status=job.status,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.finished_at,
                    error_message=job.last_error,
                    result=job.result,
                    events=[
                        {
                            "event_type": event.event_type,
                            "event_data": event.event_data,
                            "created_at": event.event_time.isoformat(),
                        }
                        for event in events
                    ],
                )

        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            raise

    async def execute_job(self, job_id: str):
        """
        Execute a crew job asynchronously with improved cleanup.

        Args:
            job_id: Job identifier
        """
        import asyncio

        try:
            # Update job status to running
            await self._update_job_status(job_id, JobStatus.RUNNING)
            await self._add_job_event(
                job_id, "job_started", {"message": "Job execution started"}
            )

            # Get job details
            job = await self._get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Determine object type by checking the schema used for this job_key
            from .services.json_validator import validate_crew_request

            validation_result = await validate_crew_request(job.payload)

            if not validation_result["valid"]:
                raise ValueError(
                    f"Job payload validation failed: {validation_result['errors']}"
                )

            # Get the schema to determine object type
            from .services.json_validator import validator

            schema_data = await validator.get_schema_by_name(
                validation_result["schema_used"]
            )
            object_type = schema_data["object_type"] if schema_data else None

            logger.info(
                f"Executing job {job_id} with job_key: {job.job_key}, object_type: {object_type}"
            )

            # Route based on object type
            if object_type == "gen_crew":
                # Use GenCrewHandler for gen_crew object types (pulls from crew_cfgs table)
                from .crews.gen_crew.gen_crew_handler import GenCrewHandler

                crew_handler = GenCrewHandler()
                crew_handler.set_job_id(uuid.UUID(job_id))
                
                # Execute the handler
                result = await crew_handler.execute(job.payload)
                
                # Update job with results
                await self._complete_job(job_id, result)
                await self._add_job_event(
                    job_id,
                    "job_completed",
                    {
                        "message": "Job completed successfully using gen_crew handler",
                        "result_summary": (
                            str(result)[:200] if result else "No result summary"
                        ),
                    },
                )
                logger.info(f"Job {job_id} completed successfully")
                return

            elif object_type == "crew":
                # Check feature flags for remote crew execution
                from .feature_flags import get_feature_flags
                from .crew_client import get_crew_client
                
                feature_flags = get_feature_flags()
                crew_name = job.job_key
                
                # Check if this crew should use remote execution
                if feature_flags.should_use_remote_crew(crew_name):
                    logger.info(f"Using remote execution for crew: {crew_name}")
                    
                    try:
                        # Use crew client for remote execution
                        crew_client = get_crew_client()
                        
                        # Execute crew remotely
                        result = await crew_client.execute_crew(
                            crew_name=crew_name,
                            inputs=job.payload,
                            request_id=job_id
                        )
                        
                        # Update job with results
                        await self._complete_job(job_id, result)
                        await self._add_job_event(
                            job_id,
                            "job_completed",
                            {
                                "message": "Job completed successfully via remote crew execution",
                                "execution_type": "remote",
                                "crew_name": crew_name,
                                "execution_time": result.get("execution_time"),
                                "total_time": result.get("total_time")
                            }
                        )
                        logger.info(f"Job {job_id} completed successfully via remote execution")
                        return
                        
                    except Exception as e:
                        logger.error(f"Remote crew execution failed: {e}")
                        
                        # Check if fallback is enabled
                        if feature_flags.should_fallback_to_local():
                            logger.warning(f"Falling back to local execution for crew: {crew_name}")
                            await self._add_job_event(
                                job_id,
                                "remote_execution_failed",
                                {
                                    "message": "Remote execution failed, falling back to local",
                                    "error": str(e),
                                    "crew_name": crew_name
                                }
                            )
                            # Continue to local execution below
                        else:
                            # No fallback, fail the job
                            raise
                
                # Local execution is no longer supported
                logger.error(f"Local execution not available for crew: {crew_name}")
                await self._add_job_event(
                    job_id,
                    "local_execution_disabled",
                    {
                        "message": "Local crew execution has been disabled. Enable remote execution via feature flags.",
                        "crew_name": crew_name,
                        "suggestion": f"Set feature flag 'use_remote_crews_{crew_name}' to true"
                    }
                )
                raise ValueError(
                    f"Local execution is disabled for crew '{crew_name}'. "
                    f"Enable remote execution by setting feature flag 'use_remote_crews_{crew_name}' to true."
                )

            else:
                raise ValueError(
                    f"Unknown object_type: {object_type} for job_key: {job.job_key}"
                )

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")

            # Update job status to failed with better error handling
            try:
                await self._fail_job(job_id, str(e))
                await self._add_job_event(
                    job_id,
                    "job_failed",
                    {"message": "Job execution failed", "error": str(e)},
                )
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to update job status after failure for {job_id}: {cleanup_error}"
                )
                # Even if we can't update the database, log the original error
                pass
        finally:
            # Ensure proper cleanup of any remaining connections or resources
            try:
                # Give any pending operations a moment to complete
                await asyncio.sleep(0.05)

                # Cancel any dangling tasks that might hold connections
                current_task = asyncio.current_task()
                pending_tasks = []

                for task in asyncio.all_tasks():
                    if (
                        not task.done()
                        and task != current_task
                        and (
                            not hasattr(task, "get_coro")
                            or "execute_job" not in str(task.get_coro())
                        )
                    ):
                        pending_tasks.append(task)

                # Cancel tasks related to this job execution that might hold connections
                for task in pending_tasks:
                    if hasattr(task, "get_name") and job_id in str(task.get_name()):
                        task.cancel()

                # Don't cleanup engines during individual job execution
                # Let the main test cleanup handle it

            except Exception as cleanup_error:
                # Use debug level to reduce noise - cleanup issues are usually non-critical
                logger.debug(f"Minor cleanup note for job {job_id}: {cleanup_error}")

    async def _get_job(self, job_id: str) -> Optional[CrewJobs]:
        """Get job from database."""
        async with get_direct_session() as session:
            return await session.get(CrewJobs, job_id)

    async def _update_job_status(
        self, job_id: str, status: str, started_at: Optional[datetime] = None
    ):
        """Update job status in database."""
        async with get_direct_session() as session:
            job = await session.get(CrewJobs, job_id)
            if job:
                job.status = status
                if started_at:
                    job.started_at = started_at
                elif status == JobStatus.RUNNING and not job.started_at:
                    job.started_at = datetime.utcnow()
                await session.commit()

    async def _complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with results."""
        import json

        try:
            async with get_direct_session() as session:
                job = await session.get(CrewJobs, job_id)
                if job:
                    job.status = JobStatus.COMPLETED
                    job.finished_at = datetime.utcnow()

                    # Ensure result is JSON serializable
                    try:
                        # Test serialization
                        json.dumps(result, default=str)
                        job.result = result
                    except (TypeError, ValueError) as e:
                        logger.warning(
                            f"Result not JSON serializable for job {job_id}: {e}"
                        )
                        # Store a safe summary instead
                        job.result = {
                            "status": result.get("status", "completed"),
                            "crew_name": result.get("crew_name", "unknown"),
                            "job_key": result.get("job_key", "unknown"),
                            "result_summary": (
                                str(result)[:500] + "..."
                                if len(str(result)) > 500
                                else str(result)
                            ),
                            "serialization_error": str(e),
                        }

                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            # Don't re-raise - we want the job to still be marked as completed
            # Store minimal success info
            try:
                async with get_direct_session() as session:
                    job = await session.get(CrewJobs, job_id)
                    if job:
                        job.status = JobStatus.COMPLETED
                        job.finished_at = datetime.utcnow()
                        job.result = {
                            "status": "completed",
                            "job_key": (
                                result.get("job_key", "unknown")
                                if isinstance(result, dict)
                                else "unknown"
                            ),
                            "completion_error": str(e),
                        }
                        await session.commit()
            except Exception as inner_e:
                logger.error(
                    f"Failed to set minimal completion for job {job_id}: {inner_e}"
                )

    async def _fail_job(self, job_id: str, error_message: str):
        """Mark job as failed with error message."""
        async with get_direct_session() as session:
            job = await session.get(CrewJobs, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.finished_at = datetime.utcnow()
                job.last_error = error_message
                await session.commit()

    async def _add_job_event(
        self, job_id: str, event_type: str, event_data: Dict[str, Any]
    ):
        """Add an event to job history using centralized crew logger."""
        crew_logger = CrewExecutionLogger(job_id)
        await crew_logger.log_crew_step(event_type, event_data)
