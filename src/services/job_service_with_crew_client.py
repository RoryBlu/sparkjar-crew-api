"""
Example modification for job_service.py to use CrewClient for remote crew execution.

This shows how to integrate the CrewClient into the existing job service.
Add this code to the execute_job method after the object_type check.
"""

# Add this import at the top of job_service.py
from .crew_client import get_crew_client

# Add this method to JobService class
async def _execute_crew_remote(self, job_id: str, crew_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute crew via remote HTTP service using CrewClient.
    
    Args:
        job_id: Job identifier
        crew_name: Name of the crew to execute
        inputs: Input parameters for the crew
        
    Returns:
        Crew execution result
    """
    crew_client = get_crew_client()
    
    try:
        # Execute crew via HTTP
        result = await crew_client.execute_crew(
            crew_name=crew_name,
            inputs=inputs,
            request_id=job_id
        )
        
        return result
        
    except CrewNotFoundError:
        raise ValueError(f"Crew '{crew_name}' not found in remote service")
    except CrewExecutionError as e:
        raise ValueError(f"Crew execution failed: {e}")
    except CrewServiceUnavailableError as e:
        logger.error(f"Crews service unavailable: {e}")
        raise ValueError(f"Crews service is currently unavailable: {e}")

# Modify the execute_job method to use remote execution:
# Replace the existing crew execution logic (lines 273-350) with:

elif object_type == "crew":
    # Check if we should use remote crew execution
    use_remote = os.getenv("USE_REMOTE_CREWS", "false").lower() == "true"
    
    if use_remote:
        # Use CrewClient for remote execution
        logger.info(f"Executing crew '{job.job_key}' via remote service")
        
        # Prepare inputs for crew
        payload_context = job.payload.get("context", job.payload)
        if isinstance(payload_context, dict):
            payload_context['client_user_id'] = job.payload.get('client_user_id')
            payload_context['job_id'] = job_id
        
        try:
            # Execute via remote service
            result = await self._execute_crew_remote(
                job_id=job_id,
                crew_name=job.job_key,
                inputs=payload_context
            )
            
            # Update job with results
            await self._complete_job(job_id, result)
            await self._add_job_event(
                job_id,
                "job_completed",
                {
                    "message": "Job completed successfully using remote crew service",
                    "execution_type": "remote",
                    "result_summary": str(result)[:200] if result else "No result summary"
                }
            )
            logger.info(f"Job {job_id} completed successfully via remote execution")
            
        except Exception as e:
            logger.error(f"Remote crew execution failed: {e}")
            # Optionally fall back to local execution
            if os.getenv("FALLBACK_TO_LOCAL", "true").lower() == "true":
                logger.warning("Falling back to local crew execution")
                # ... existing local execution code ...
            else:
                raise
    else:
        # Use existing local execution logic
        # ... (keep the existing code from lines 274-350)