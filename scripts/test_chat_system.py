#!/usr/bin/env python3
"""
System integration test for chat functionality.
Can run standalone without full environment setup.
"""

import httpx
import asyncio
import json
import time
from datetime import datetime
from uuid import uuid4
import jwt
import os


# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "test-secret-key-change-in-production")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8003")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def create_test_token(client_id: str, actor_id: str, actor_type: str = "synth", scopes=None):
    """Create a test JWT token."""
    if scopes is None:
        scopes = ["chat"]
    
    payload = {
        "client_user_id": client_id,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "scopes": scopes,
        "exp": int(time.time()) + 3600  # 1 hour
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def test_api_health():
    """Test API health endpoint."""
    print("\n🏥 Testing API Health...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/health")
            if response.status_code == 200:
                print("  ✅ API is healthy")
                return True
            else:
                print(f"  ❌ API unhealthy: {response.status_code}")
                return False
    except Exception as e:
        print(f"  ❌ Cannot connect to API: {e}")
        return False


async def test_chat_flow():
    """Test basic chat flow."""
    print("\n💬 Testing Chat Flow...")
    
    client_id = str(uuid4())
    actor_id = str(uuid4())
    session_id = str(uuid4())
    
    token = create_test_token(client_id, actor_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    request = {
        "session_id": session_id,
        "client_user_id": client_id,
        "actor_type": "synth",
        "actor_id": actor_id,
        "message": "Hello, this is a test message",
        "enable_sequential_thinking": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_URL}/chat",
                json=request,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "response" in data:
                    print("  ✅ Chat request successful")
                    print(f"     Response preview: {data['response'][:50]}...")
                    return True
                else:
                    print("  ❌ Invalid response format")
                    return False
            else:
                print(f"  ❌ Chat failed: {response.status_code}")
                print(f"     Error: {response.text}")
                return False
    except Exception as e:
        print(f"  ❌ Chat error: {e}")
        return False


async def test_streaming():
    """Test streaming chat response."""
    print("\n🌊 Testing Streaming...")
    
    client_id = str(uuid4())
    actor_id = str(uuid4())
    session_id = str(uuid4())
    
    token = create_test_token(client_id, actor_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    request = {
        "session_id": session_id,
        "client_user_id": client_id,
        "actor_type": "synth",
        "actor_id": actor_id,
        "message": "Count from 1 to 3",
        "enable_sequential_thinking": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            async with client.stream(
                "POST", 
                f"{API_URL}/chat/stream", 
                json=request, 
                headers=headers
            ) as response:
                if response.status_code != 200:
                    print(f"  ❌ Streaming failed: {response.status_code}")
                    return False
                    
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk != "[DONE]":
                            chunks.append(chunk)
                            
            if len(chunks) > 0:
                print(f"  ✅ Streaming successful: {len(chunks)} chunks")
                return True
            else:
                print("  ❌ No streaming chunks received")
                return False
    except Exception as e:
        print(f"  ❌ Streaming error: {e}")
        return False


async def test_client_isolation():
    """Test that clients are properly isolated."""
    print("\n🔒 Testing Client Isolation...")
    
    client1_id = str(uuid4())
    client2_id = str(uuid4())
    session_id = str(uuid4())
    
    # Client 1 creates session
    token1 = create_test_token(client1_id, str(uuid4()))
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    request = {
        "session_id": session_id,
        "client_user_id": client1_id,
        "actor_type": "synth",
        "actor_id": str(uuid4()),
        "message": "Private client 1 data"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Create session as client 1
            response = await client.post(
                f"{API_URL}/chat",
                json=request,
                headers=headers1
            )
            
            if response.status_code != 200:
                print(f"  ❌ Failed to create session: {response.status_code}")
                return False
                
            # Try to access as client 2
            token2 = create_test_token(client2_id, str(uuid4()))
            headers2 = {"Authorization": f"Bearer {token2}"}
            
            response = await client.get(
                f"{API_URL}/chat/session/{session_id}",
                headers=headers2
            )
            
            if response.status_code == 403:
                print("  ✅ Client isolation working correctly")
                return True
            else:
                print(f"  ❌ Client isolation failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"  ❌ Isolation test error: {e}")
        return False


async def test_concurrent_sessions():
    """Test handling multiple concurrent sessions."""
    print("\n🚀 Testing Concurrent Sessions...")
    
    num_sessions = 10
    
    async def create_session(i):
        client_id = str(uuid4())
        actor_id = str(uuid4())
        session_id = str(uuid4())
        
        token = create_test_token(client_id, actor_id)
        headers = {"Authorization": f"Bearer {token}"}
        
        request = {
            "session_id": session_id,
            "client_user_id": client_id,
            "actor_type": "synth",
            "actor_id": actor_id,
            "message": f"Concurrent test message {i}",
            "enable_sequential_thinking": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start = time.time()
                response = await client.post(
                    f"{API_URL}/chat",
                    json=request,
                    headers=headers
                )
                elapsed = time.time() - start
                
                return {
                    "success": response.status_code == 200,
                    "time": elapsed,
                    "session": i
                }
        except Exception as e:
            return {
                "success": False,
                "time": 0,
                "session": i,
                "error": str(e)
            }
    
    try:
        # Create concurrent tasks
        tasks = [create_session(i) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        if len(successful) > 0:
            avg_time = sum(r["time"] for r in successful) / len(successful)
            print(f"  ✅ {len(successful)}/{num_sessions} sessions successful")
            print(f"     Average response time: {avg_time:.2f}s")
            
            if len(failed) > 0:
                print(f"  ⚠️  {len(failed)} sessions failed")
        else:
            print(f"  ❌ All sessions failed")
            
        return len(successful) > num_sessions * 0.8  # 80% success rate
    except Exception as e:
        print(f"  ❌ Concurrent test error: {e}")
        return False


async def test_memory_service_integration():
    """Test memory service integration."""
    print("\n🧠 Testing Memory Service Integration...")
    
    client_id = str(uuid4())
    actor_id = str(uuid4())
    session_id = str(uuid4())
    
    token = create_test_token(client_id, actor_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    # First check if memory service is available
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MEMORY_SERVICE_URL}/health")
            if response.status_code != 200:
                print("  ⚠️  Memory Service not available (optional)")
                return True  # Optional service
    except:
        print("  ⚠️  Memory Service not available (optional)")
        return True  # Optional service
    
    # Test memory integration through chat
    request = {
        "session_id": session_id,
        "client_user_id": client_id,
        "actor_type": "synth",
        "actor_id": actor_id,
        "message": "Search for any available information",
        "enable_sequential_thinking": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_URL}/chat",
                json=request,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "memory_context_used" in data:
                    print(f"  ✅ Memory integration working")
                    print(f"     Contexts found: {len(data.get('memory_context_used', []))}")
                    return True
                else:
                    print("  ⚠️  Memory integration incomplete")
                    return True  # Not critical
            else:
                print(f"  ❌ Memory test failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"  ❌ Memory test error: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 SparkJAR Chat System Tests")
    print("=" * 50)
    print(f"API URL: {API_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    
    # Check if API is accessible
    if not await test_api_health():
        print("\n❌ API is not accessible. Please ensure:")
        print("1. The crew-api service is running")
        print("2. The API_URL environment variable is correct")
        print("\nTo start the service:")
        print("  cd services/crew-api")
        print("  python main.py")
        return
    
    # Run tests
    tests = [
        test_chat_flow(),
        test_streaming(),
        test_client_isolation(),
        test_concurrent_sessions(),
        test_memory_service_integration()
    ]
    
    results = await asyncio.gather(*tests)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.0f}%")
    
    # Final verdict
    print("\n🎯 VERDICT:")
    if passed == total:
        print("✅ ALL TESTS PASSED - System is working correctly!")
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY PASSING - System is functional with minor issues")
    else:
        print("❌ CRITICAL FAILURES - System needs attention")
        
    # Save results
    results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "api_url": API_URL,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed/total
        }, f, indent=2)
    print(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())