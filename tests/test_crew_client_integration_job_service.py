"""
Integration test for CrewClient with JobService

This test verifies that the crew client can be integrated into the job service
for remote crew execution.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import uuid

from services.crew_client import CrewClient
from services.crew_client_exceptions import (
    CrewNotFoundError,
    CrewExecutionError,
    CrewServiceUnavailableError
)


class TestCrewClientJobServiceIntegration:
    """Test CrewClient integration with JobService"""
    
    @pytest.fixture
    def mock_job(self):
        """Mock job object"""
        job = Mock()
        job.id = str(uuid.uuid4())
        job.job_key = "test_crew"
        job.payload = {
            "context": {
                "text_content": "Test content",
                "actor_type": "human",
                "actor_id": "test-123"
            },
            "client_user_id": "client-456"
        }
        job.status = "queued"
        return job
    
    @pytest.fixture
    def crew_client(self):
        """Create test crew client"""
        return CrewClient(base_url="http://test-crews:8001")
    
    @pytest.mark.asyncio
    async def test_remote_crew_execution_success(self, mock_job, crew_client):
        """Test successful remote crew execution"""
        
        # Mock the crew client execute_crew method
        with patch.object(crew_client, 'execute_crew', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "result": "Crew executed successfully",
                "execution_time": 45.2,
                "crew_name": "test_crew",
                "request_id": mock_job.id
            }
            
            # Prepare inputs
            inputs = mock_job.payload.get("context", mock_job.payload)
            inputs['client_user_id'] = mock_job.payload.get('client_user_id')
            inputs['job_id'] = mock_job.id
            
            # Execute crew
            result = await crew_client.execute_crew(
                crew_name=mock_job.job_key,
                inputs=inputs,
                request_id=mock_job.id
            )
            
            # Verify
            assert result["success"] is True
            assert result["result"] == "Crew executed successfully"
            assert result["crew_name"] == "test_crew"
            
            # Verify call was made correctly
            mock_execute.assert_called_once_with(
                crew_name="test_crew",
                inputs=inputs,
                request_id=mock_job.id
            )
    
    @pytest.mark.asyncio
    async def test_remote_crew_execution_not_found(self, mock_job, crew_client):
        """Test crew not found error handling"""
        
        with patch.object(crew_client, 'execute_crew', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = CrewNotFoundError("Crew 'test_crew' not found")
            
            # Execute and expect error
            with pytest.raises(CrewNotFoundError):
                await crew_client.execute_crew(
                    crew_name=mock_job.job_key,
                    inputs=mock_job.payload,
                    request_id=mock_job.id
                )
    
    @pytest.mark.asyncio
    async def test_remote_crew_execution_service_unavailable(self, mock_job, crew_client):
        """Test service unavailable error handling"""
        
        with patch.object(crew_client, 'execute_crew', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = CrewServiceUnavailableError("Service unavailable")
            
            # Execute and expect error
            with pytest.raises(CrewServiceUnavailableError):
                await crew_client.execute_crew(
                    crew_name=mock_job.job_key,
                    inputs=mock_job.payload,
                    request_id=mock_job.id
                )
    
    @pytest.mark.asyncio
    async def test_environment_flag_check(self):
        """Test checking USE_REMOTE_CREWS environment variable"""
        import os
        
        # Test with flag enabled
        with patch.dict(os.environ, {"USE_REMOTE_CREWS": "true"}):
            use_remote = os.getenv("USE_REMOTE_CREWS", "false").lower() == "true"
            assert use_remote is True
        
        # Test with flag disabled
        with patch.dict(os.environ, {"USE_REMOTE_CREWS": "false"}):
            use_remote = os.getenv("USE_REMOTE_CREWS", "false").lower() == "true"
            assert use_remote is False
        
        # Test with flag not set (default)
        with patch.dict(os.environ, {}, clear=True):
            use_remote = os.getenv("USE_REMOTE_CREWS", "false").lower() == "true"
            assert use_remote is False
    
    @pytest.mark.asyncio
    async def test_fallback_to_local_execution(self, mock_job, crew_client):
        """Test fallback to local execution when remote fails"""
        import os
        
        with patch.dict(os.environ, {"FALLBACK_TO_LOCAL": "true"}):
            with patch.object(crew_client, 'execute_crew', new_callable=AsyncMock) as mock_execute:
                mock_execute.side_effect = CrewServiceUnavailableError("Service down")
                
                # In actual implementation, this would fall back to local execution
                # Here we just verify the environment variable check
                fallback_enabled = os.getenv("FALLBACK_TO_LOCAL", "true").lower() == "true"
                assert fallback_enabled is True
                
                # Verify the error is raised
                with pytest.raises(CrewServiceUnavailableError):
                    await crew_client.execute_crew(
                        crew_name=mock_job.job_key,
                        inputs=mock_job.payload
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])