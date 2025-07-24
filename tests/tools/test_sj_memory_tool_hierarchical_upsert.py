"""
Test for upsert_entity action in SJMemoryToolHierarchical.

This test file verifies that the upsert_entity action is properly implemented
and works with the Memory Service API.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.tools.sj_memory_tool_hierarchical import (
    SJMemoryToolHierarchical,
    HierarchicalMemoryConfig,
    create_hierarchical_memory_tool
)


class TestUpsertEntity:
    """Test suite for upsert_entity action."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a test configuration."""
        return HierarchicalMemoryConfig(
            mcp_registry_url="http://test-registry",
            api_secret_key="test-secret",
            timeout=5,
            enable_hierarchy=True,
            enable_consolidation=True
        )
    
    @pytest.fixture
    def memory_tool(self, mock_config):
        """Create a memory tool instance for testing."""
        tool = SJMemoryToolHierarchical(config=mock_config)
        tool.set_actor_context(
            actor_type="synth",
            actor_id=str(uuid4()),
            client_id=str(uuid4())
        )
        return tool
    
    def test_upsert_entity_action_exists(self, memory_tool):
        """Test that upsert_entity is listed as an available action."""
        # Create a test query that should fail since upsert_entity is not implemented yet
        query = json.dumps({
            "action": "upsert_entity",
            "params": {
                "name": "test_policy",
                "entity_type": "policy",
                "observations": [
                    {
                        "observation": "Test policy content",
                        "observation_type": "policy_statement",
                        "metadata": {"source": "test"}
                    }
                ],
                "metadata": {"version": "1.0"}
            }
        })
        
        # This should fail with "Unknown action" error
        result = memory_tool._run(query)
        
        # The test expects this to fail initially
        assert "Unknown action 'upsert_entity'" in result
        assert "Available:" in result
        # Verify that upsert_entity is NOT in the list of available actions
        assert "upsert_entity" not in result.split("Available:")[1]
    
    @patch('src.tools.sj_memory_tool_hierarchical.httpx.AsyncClient')
    async def test_upsert_entity_basic_functionality(self, mock_client_class, memory_tool):
        """Test basic upsert_entity functionality once implemented."""
        # This test will pass once we implement the feature
        
        # Mock the HTTP client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful service discovery
        memory_tool._service_url = "http://test-memory-service"
        memory_tool._service_discovered_at = pytest.mock.ANY
        
        # Mock successful upsert response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "id": str(uuid4()),
            "name": "test_policy",
            "entity_type": "policy",
            "observations": [
                {
                    "id": str(uuid4()),
                    "observation": "Test policy content",
                    "observation_type": "policy_statement",
                    "metadata": {"source": "test"}
                }
            ],
            "metadata": {"version": "1.0"}
        }]
        
        mock_client.post.return_value = mock_response
        
        # Once implemented, this should work
        result = await memory_tool._upsert_entity(
            name="test_policy",
            entity_type="policy",
            observations=[
                {
                    "observation": "Test policy content",
                    "observation_type": "policy_statement",
                    "metadata": {"source": "test"}
                }
            ],
            metadata={"version": "1.0"}
        )
        
        # Verify the result
        assert result["success"] is True
        assert "entity" in result
        assert result["entity"]["name"] == "test_policy"
        
        # Verify the API was called correctly
        mock_client.post.assert_called_once_with(
            "/memory/entities/upsert",
            json=[{
                "name": "test_policy",
                "entityType": "policy",
                "observations": [
                    {
                        "observation": "Test policy content",
                        "observation_type": "policy_statement",
                        "metadata": {"source": "test"}
                    }
                ],
                "metadata": {"version": "1.0"}
            }]
        )
    
    def test_upsert_entity_parameter_validation(self, memory_tool):
        """Test that upsert_entity validates required parameters."""
        # Test missing name
        query = json.dumps({
            "action": "upsert_entity",
            "params": {
                "entity_type": "policy",
                "observations": []
            }
        })
        
        # Once implemented, this should return an error about missing 'name'
        result = memory_tool._run(query)
        # For now, it will say unknown action
        assert "Unknown action" in result or "Missing required parameter: name" in result
    
    def test_upsert_entity_with_consolidation(self, memory_tool):
        """Test that upsert_entity supports memory consolidation when enabled."""
        # This tests the advanced consolidation features
        query = json.dumps({
            "action": "upsert_entity",
            "params": {
                "name": "performance_metrics",
                "entity_type": "metric",
                "observations": [
                    {
                        "observation": "Blog performance: 85%",
                        "observation_type": "statistic",
                        "metadata": {"date": "2025-01-01"}
                    }
                ],
                "enable_consolidation": True
            }
        })
        
        # Once implemented with consolidation, this should:
        # 1. Load the memory graph
        # 2. Check for existing statistics
        # 3. Update in place rather than append
        result = memory_tool._run(query)
        
        # For now, it will fail
        assert "Unknown action" in result


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])