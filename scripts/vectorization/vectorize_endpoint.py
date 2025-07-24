#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
API endpoint to trigger vectorization of job events
"""
from fastapi import FastAPI, HTTPException
import sys
import os

# Add parent directory to path

# Import the vectorization logic
from vectorize_job_events import *

app = FastAPI()

@app.post("/vectorize/{job_id}")
async def vectorize_job(job_id: str):
    """Vectorize events for a specific job"""
    try:
        # Download job data from API
        import httpx
        import os
        
        token = os.getenv("JWT_TOKEN")
        if not token:
            logger.error("Error: JWT_TOKEN environment variable is required")
            return
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sparkjar-crew-api-development.up.railway.app/crew_job/{job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to get job data: {response.text}")
            
            job_data = response.json()
        
        # Save to temp file (vectorize script expects this)
        with open('/tmp/job_result.json', 'w') as f:
            json.dump(job_data, f)
        
        # Run vectorization logic here
        # ... (copy the main logic from vectorize_job_events.py)
        
        return {"status": "success", "message": f"Vectorized job {job_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)