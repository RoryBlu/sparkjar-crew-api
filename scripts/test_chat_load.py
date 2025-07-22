#!/usr/bin/env python3
"""
Simple load testing script for chat API.
Tests concurrent sessions and basic performance metrics.
"""

import asyncio
import httpx
import time
import statistics
from uuid import uuid4
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.auth import create_access_token


# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
NUM_SESSIONS = int(os.getenv("NUM_SESSIONS", "100"))
NUM_MESSAGES_PER_SESSION = int(os.getenv("MESSAGES_PER_SESSION", "3"))


async def create_chat_session(session_num: int) -> dict:
    """
    Create a single chat session and measure performance.
    
    Returns:
        Dict with timing and success metrics
    """
    # Create unique IDs for this session
    client_id = str(uuid4())
    actor_id = str(uuid4())
    session_id = str(uuid4())
    
    # Create auth token
    token_data = {
        "client_user_id": client_id,
        "actor_type": "synth",
        "actor_id": actor_id,
        "scopes": ["chat"]
    }
    token = create_access_token(token_data)
    
    # Track metrics
    metrics = {
        "session_num": session_num,
        "success": True,
        "response_times": [],
        "errors": []
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Send multiple messages in the session
        for msg_num in range(NUM_MESSAGES_PER_SESSION):
            request = {
                "session_id": session_id,
                "client_user_id": client_id,
                "actor_type": "synth",
                "actor_id": actor_id,
                "message": f"Test message {msg_num} from session {session_num}. Tell me about Project {chr(65 + msg_num)}",
                "enable_sequential_thinking": False,
                "metadata": {
                    "test_session": session_num,
                    "test_message": msg_num
                }
            }
            
            try:
                start_time = time.time()
                response = await client.post(
                    f"{API_URL}/chat",
                    json=request,
                    headers=headers
                )
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status_code == 200:
                    metrics["response_times"].append(response_time)
                else:
                    metrics["success"] = False
                    metrics["errors"].append(f"HTTP {response.status_code}: {response.text[:100]}")
                    
            except Exception as e:
                metrics["success"] = False
                metrics["errors"].append(f"Exception: {str(e)}")
                
    return metrics


async def test_client_isolation():
    """Test that different clients can't access each other's sessions."""
    print("\n🔒 Testing Client Isolation...")
    
    # Create two different clients
    client1_id = str(uuid4())
    client2_id = str(uuid4())
    shared_session_id = str(uuid4())
    
    # Client 1 creates a session
    token1 = create_access_token({
        "client_user_id": client1_id,
        "actor_type": "synth",
        "actor_id": str(uuid4()),
        "scopes": ["chat"]
    })
    
    async with httpx.AsyncClient() as client:
        # Client 1 sends a message
        response = await client.post(
            f"{API_URL}/chat",
            json={
                "session_id": shared_session_id,
                "client_user_id": client1_id,
                "actor_type": "synth",
                "actor_id": str(uuid4()),
                "message": "Client 1 secret message"
            },
            headers={"Authorization": f"Bearer {token1}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Client 1 failed to create session: {response.status_code}")
            return False
            
        # Client 2 tries to access the session
        token2 = create_access_token({
            "client_user_id": client2_id,
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "scopes": ["chat"]
        })
        
        response = await client.get(
            f"{API_URL}/chat/session/{shared_session_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        if response.status_code == 403:
            print("✅ Client isolation working - Client 2 denied access to Client 1's session")
            return True
        else:
            print(f"❌ Client isolation FAILED - Client 2 got status {response.status_code}")
            return False


async def main():
    """Run load tests and display results."""
    print(f"🚀 Chat API Load Test")
    print(f"📍 Target: {API_URL}")
    print(f"💬 Sessions: {NUM_SESSIONS}")
    print(f"📝 Messages per session: {NUM_MESSAGES_PER_SESSION}")
    print(f"📊 Total requests: {NUM_SESSIONS * NUM_MESSAGES_PER_SESSION}")
    print("-" * 50)
    
    # Test client isolation first
    isolation_ok = await test_client_isolation()
    if not isolation_ok:
        print("⚠️  Client isolation test failed - stopping tests")
        return
    
    # Run concurrent session tests
    print(f"\n🏃 Starting {NUM_SESSIONS} concurrent sessions...")
    start_time = time.time()
    
    # Create tasks for concurrent execution
    tasks = [create_chat_session(i) for i in range(NUM_SESSIONS)]
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful_sessions = sum(1 for r in results if r["success"])
    failed_sessions = NUM_SESSIONS - successful_sessions
    all_response_times = []
    all_errors = []
    
    for result in results:
        all_response_times.extend(result["response_times"])
        all_errors.extend(result["errors"])
    
    # Display results
    print("\n📊 Results")
    print("-" * 50)
    print(f"⏱️  Total test duration: {total_time:.2f} seconds")
    print(f"✅ Successful sessions: {successful_sessions}/{NUM_SESSIONS}")
    print(f"❌ Failed sessions: {failed_sessions}/{NUM_SESSIONS}")
    print(f"📨 Total successful requests: {len(all_response_times)}")
    print(f"🔥 Requests per second: {len(all_response_times) / total_time:.2f}")
    
    if all_response_times:
        print(f"\n📈 Response Time Statistics (ms):")
        print(f"   Min: {min(all_response_times):.2f}")
        print(f"   Max: {max(all_response_times):.2f}")
        print(f"   Average: {statistics.mean(all_response_times):.2f}")
        print(f"   Median: {statistics.median(all_response_times):.2f}")
        
        # Calculate percentiles
        sorted_times = sorted(all_response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        
        print(f"   P95: {sorted_times[p95_index]:.2f}")
        print(f"   P99: {sorted_times[p99_index]:.2f}")
    
    if all_errors:
        print(f"\n⚠️  Errors encountered ({len(all_errors)} total):")
        # Show unique errors
        unique_errors = list(set(all_errors))[:5]  # Show first 5 unique errors
        for error in unique_errors:
            print(f"   - {error}")
    
    # Performance assessment
    print("\n🎯 Performance Assessment:")
    if failed_sessions == 0 and all_response_times:
        avg_response = statistics.mean(all_response_times)
        if avg_response < 200:
            print("   🟢 Excellent - Average response under 200ms")
        elif avg_response < 500:
            print("   🟡 Good - Average response under 500ms")
        else:
            print("   🔴 Needs optimization - Average response over 500ms")
    elif failed_sessions > NUM_SESSIONS * 0.1:  # More than 10% failure
        print("   🔴 High failure rate - needs investigation")
    else:
        print("   🟡 Some failures detected - check error logs")
    
    # Save detailed results
    results_file = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(results_file, 'w') as f:
        f.write(f"Load Test Results - {datetime.now()}\n")
        f.write(f"Sessions: {NUM_SESSIONS}\n")
        f.write(f"Messages per session: {NUM_MESSAGES_PER_SESSION}\n")
        f.write(f"Total duration: {total_time:.2f}s\n")
        f.write(f"Successful requests: {len(all_response_times)}\n")
        f.write(f"Failed sessions: {failed_sessions}\n")
        if all_response_times:
            f.write(f"Average response time: {statistics.mean(all_response_times):.2f}ms\n")
        f.write("\nErrors:\n")
        for error in all_errors:
            f.write(f"  {error}\n")
    
    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    # Check if API is accessible
    try:
        response = httpx.get(f"{API_URL}/health", timeout=5.0)
        if response.status_code != 200:
            print(f"❌ API health check failed: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_URL}: {e}")
        sys.exit(1)
    
    # Run tests
    asyncio.run(main())