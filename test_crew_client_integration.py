#!/usr/bin/env python
"""
Integration test for CrewClient with real crews service

This test verifies that the crew client can communicate with the actual crews service.
"""

import asyncio
import logging
from services.crew_client import CrewClient
from services.crew_client_exceptions import CrewServiceUnavailableError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_crew_client_integration():
    """Test crew client integration with real service"""
    
    # Use localhost crews service for testing
    client = CrewClient(base_url="http://localhost:8001")
    
    try:
        print("🔍 Testing crew client integration...")
        
        # Test 1: Health check
        print("\n1. Testing health check...")
        try:
            health = await client.health_check()
            print(f"✅ Health check passed: {health['status']}")
            print(f"   Available crews: {health.get('available_crews', [])}")
        except CrewServiceUnavailableError:
            print("⚠️  Crews service not available - skipping integration tests")
            print("   Start the crews service with: cd _reorg/sparkjar-crews && python run_api.py")
            return
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Test 2: List crews
        print("\n2. Testing crew listing...")
        try:
            crews = await client.list_crews()
            print(f"✅ Found {len(crews)} crews: {crews}")
        except Exception as e:
            print(f"❌ Crew listing failed: {e}")
            return
        
        # Test 3: Execute crew (if available)
        if crews:
            print(f"\n3. Testing crew execution with '{crews[0]}'...")
            try:
                # Use a simple test input
                test_inputs = {
                    "text_content": "This is a test message for crew execution",
                    "actor_type": "human",
                    "actor_id": "test-user-123",
                    "client_user_id": "test-client-456"
                }
                
                result = await client.execute_crew(
                    crew_name=crews[0],
                    inputs=test_inputs,
                    timeout=60  # Short timeout for testing
                )
                
                if result["success"]:
                    print(f"✅ Crew execution successful!")
                    print(f"   Execution time: {result['execution_time']:.2f}s")
                    print(f"   Total time: {result['total_time']:.2f}s")
                    print(f"   Result preview: {str(result['result'])[:100]}...")
                else:
                    print(f"❌ Crew execution failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Crew execution failed: {e}")
        else:
            print("\n3. No crews available for execution test")
        
        # Test 4: Error handling
        print("\n4. Testing error handling...")
        try:
            await client.execute_crew(
                crew_name="nonexistent_crew",
                inputs={"test": "data"}
            )
            print("❌ Should have failed for nonexistent crew")
        except Exception as e:
            print(f"✅ Properly handled error: {type(e).__name__}: {e}")
        
        print("\n🎉 Integration tests completed!")
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_crew_client_integration())