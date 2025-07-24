"""
Test suite for Context Query Tool.
Tests the context query functionality with human and synth actors.
"""
import asyncio
import json
import os
import sys

import pytest

pytestmark = pytest.mark.integration

# Add project root to path

from services.crew_api.src.tools.context_query_tool import (ContextQueryTool,
                                          execute_context_query)

class TestContextQueryTool:
    """Test Context Query Tool functionality."""

    def setup_method(self):
        """Set up test data for each test."""
        # Human actor test data
        self.context_params_human = {
            "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
            "actor_type": "human",
            "actor_id": "587f8370-825f-4f0c-8846-2e6d70782989"
        }

        # Synth actor test data  
        self.context_params_synth = {
            "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
            "actor_type": "synth", 
            "actor_id": "1131ca9d-35d8-4ad1-ad77-0485b0239b86"
        }

    @pytest.mark.asyncio
    async def test_context_query_human_actor(self):
        """Test context query with human actor."""
        print("Testing context query with human actor...")
        
        try:
            result = await execute_context_query(
                query_type="actor_context",
                context_params=self.context_params_human
            )
            
            # Validate result structure
            assert "data" in result
            assert "client_context" in result["data"]
            assert "actor_context" in result["data"]
            
            # Validate client context fields
            client_context = result["data"]["client_context"]
            assert "client_id" in client_context
            assert "client_name" in client_context
            assert "client_user_id" in client_context
            assert "client_user_name" in client_context
            assert "client_user_email" in client_context
            
            # Validate actor context fields
            actor_context = result["data"]["actor_context"]
            assert "id" in actor_context
            assert "type" in actor_context
            assert "name" in actor_context
            assert "email" in actor_context
            assert actor_context["type"] == "human"
            
            print(f"✅ Human actor context query successful")
            print(f"Client: {client_context['client_name']} - {client_context['client_user_name']}")
            print(f"Actor: {actor_context['name']} ({actor_context['type']})")
            
        except Exception as e:
            print(f"❌ Human actor test failed: {e}")
            pytest.fail(f"Human actor context query failed: {e}")

    @pytest.mark.asyncio
    async def test_context_query_synth_actor(self):
        """Test context query with synth actor."""
        print("Testing context query with synth actor...")
        
        try:
            result = await execute_context_query(
                query_type="actor_context",
                context_params=self.context_params_synth
            )
            
            # Validate result structure
            assert "data" in result
            assert "client_context" in result["data"]
            assert "actor_context" in result["data"]
            
            # Validate client context fields
            client_context = result["data"]["client_context"]
            assert "client_id" in client_context
            assert "client_name" in client_context
            assert "client_user_id" in client_context
            assert "client_user_name" in client_context
            assert "client_user_email" in client_context
            
            # Validate actor context fields (synth uses description)
            actor_context = result["data"]["actor_context"]
            assert "id" in actor_context
            assert "type" in actor_context
            assert "name" in actor_context
            assert "description" in actor_context
            assert actor_context["type"] == "synth"
            
            print(f"✅ Synth actor context query successful")
            print(f"Client: {client_context['client_name']} - {client_context['client_user_name']}")
            print(f"Actor: {actor_context['name']} ({actor_context['type']})")
            
        except Exception as e:
            print(f"❌ Synth actor test failed: {e}")
            pytest.fail(f"Synth actor context query failed: {e}")

    @pytest.mark.asyncio
    async def test_context_query_tool_integration(self):
        """Test the ContextQueryTool as a CrewAI tool."""
        print("Testing ContextQueryTool as CrewAI tool...")
        
        try:
            tool = ContextQueryTool()
            
            # Test with human actor
            result_json = await tool._arun(
                query_type="actor_context",
                context_params=self.context_params_human
            )
            
            result = json.loads(result_json)
            
            # Validate tool result structure
            assert "data" in result
            assert result["data"]["actor_type"] == "human"
            
            print(f"✅ CrewAI tool integration successful")
            
        except Exception as e:
            print(f"❌ Tool integration test failed: {e}")
            pytest.fail(f"ContextQueryTool integration failed: {e}")

    @pytest.mark.asyncio
    async def test_invalid_actor_type(self):
        """Test context query with invalid actor type."""
        print("Testing context query with invalid actor type...")
        
        invalid_params = {
            "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
            "actor_type": "invalid",
            "actor_id": "587f8370-825f-4f0c-8846-2e6d70782989"
        }
        
        try:
            result = await execute_context_query(
                query_type="actor_context",
                context_params=invalid_params
            )
            
            # Should return error in result
            assert "error" in result
            print("✅ Invalid actor type properly handled")
            
        except Exception as e:
            # Exception is expected for invalid actor type
            print(f"✅ Invalid actor type properly rejected: {str(e)}")
            assert "Invalid actor_type" in str(e)

    @pytest.mark.asyncio
    async def test_missing_parameters(self):
        """Test context query with missing required parameters."""
        print("Testing context query with missing parameters...")
        
        incomplete_params = {
            "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989"
            # Missing actor_type and actor_id
        }
        
        try:
            result = await execute_context_query(
                query_type="actor_context",
                context_params=incomplete_params
            )
            
            # Should return error in result
            assert "error" in result
            print("✅ Missing parameters properly handled")
            
        except Exception as e:
            # Exception is expected for missing parameters
            print(f"✅ Missing parameters properly rejected: {str(e)}")
            assert "Missing required parameter" in str(e)

# Standalone test execution
async def run_context_query_tests():
    """Run context query tests standalone."""
    print("🧪 Testing Context Query Tool")
    print("=" * 50)
    
    test_instance = TestContextQueryTool()
    test_instance.setup_method()
    
    try:
        print("\n1. Testing Human Actor Context Query...")
        await test_instance.test_context_query_human_actor()
        
        print("\n2. Testing Synth Actor Context Query...")
        await test_instance.test_context_query_synth_actor()
        
        print("\n3. Testing Tool Integration...")
        await test_instance.test_context_query_tool_integration()
        
        print("\n4. Testing Error Handling...")
        await test_instance.test_invalid_actor_type()
        await test_instance.test_missing_parameters()
        
        print("\n✅ All context query tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Context query tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_context_query_tests())
