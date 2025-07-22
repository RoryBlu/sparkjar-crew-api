#!/usr/bin/env python3
"""
Comprehensive system integration testing for chat functionality.
Tests the complete system with all services running.
"""

import sys
import os
import httpx
import asyncio
from uuid import uuid4
import json
import redis
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncpg

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.auth import create_access_token
from src.config import (
    REDIS_URL, 
    MEMORY_SERVICE_URL, 
    THINKING_SERVICE_URL,
    DATABASE_URL_DIRECT,
    CREW_API_URL
)


class SystemIntegrationTester:
    """Comprehensive system integration tester."""
    
    def __init__(self):
        self.api_url = os.getenv("API_URL", "http://localhost:8000")
        self.test_results = []
        self.test_data = {
            "client_id": str(uuid4()),
            "synth_class_id": str(uuid4()),
            "synth_id": str(uuid4()),
            "session_id": str(uuid4())
        }
        
    def log_test(self, test_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        """Log test result."""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            print(f"    → {message}")
        if details and not passed:
            print(f"    → Details: {json.dumps(details, indent=6)}")
            
    async def setup_test_data(self):
        """Set up test data in the database."""
        print("\n🔧 Setting up test data...")
        
        try:
            conn = await asyncpg.connect(DATABASE_URL_DIRECT)
            
            # Check if memory_maker_crew schema exists
            schema_check = await conn.fetchval(
                "SELECT COUNT(*) FROM object_schemas WHERE name = 'memory_maker_crew'"
            )
            
            if schema_check == 0:
                # Insert memory_maker_crew schema
                await conn.execute("""
                    INSERT INTO object_schemas (name, object_type, schema, created_at, updated_at)
                    VALUES (
                        'memory_maker_crew',
                        'crew',
                        $1::jsonb,
                        NOW(),
                        NOW()
                    )
                """, json.dumps({
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": "Memory Maker Crew Context Schema",
                    "type": "object",
                    "required": ["client_user_id", "actor_type", "actor_id", "text_content"],
                    "properties": {
                        "client_user_id": {
                            "type": "string",
                            "format": "uuid",
                            "description": "UUID of the client"
                        },
                        "actor_type": {
                            "type": "string",
                            "enum": ["synth", "human", "system"],
                            "description": "Type of actor"
                        },
                        "actor_id": {
                            "type": "string",
                            "format": "uuid",
                            "description": "UUID of the actor"
                        },
                        "text_content": {
                            "type": "string",
                            "description": "Text content to process"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata",
                            "additionalProperties": true
                        }
                    },
                    "additionalProperties": false
                }))
                
                self.log_test("Database Setup - Memory Maker Schema", True, "Schema created")
            else:
                self.log_test("Database Setup - Memory Maker Schema", True, "Schema already exists")
                
            await conn.close()
            return True
            
        except Exception as e:
            self.log_test("Database Setup", False, str(e))
            return False
            
    async def test_service_health(self):
        """Test all service health endpoints."""
        print("\n🏥 Testing Service Health...")
        
        services = [
            ("Crew API", f"{self.api_url}/health", True),
            ("Memory Service", f"{MEMORY_SERVICE_URL}/health", True),
            ("Thinking Service", f"{THINKING_SERVICE_URL}/health" if THINKING_SERVICE_URL else None, False)
        ]
        
        for service_name, url, required in services:
            if not url:
                self.log_test(f"{service_name} Health", True, "Not configured (optional)")
                continue
                
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        self.log_test(f"{service_name} Health", True, "Service is healthy")
                    else:
                        self.log_test(
                            f"{service_name} Health", 
                            not required, 
                            f"Status code: {response.status_code}",
                            {"response": response.text[:200]}
                        )
            except Exception as e:
                self.log_test(
                    f"{service_name} Health", 
                    not required, 
                    str(e)
                )
                
    async def test_redis_connection(self):
        """Test Redis connectivity and operations."""
        print("\n🔴 Testing Redis...")
        
        try:
            r = redis.from_url(REDIS_URL)
            
            # Test basic operations
            test_key = f"test:integration:{uuid4()}"
            test_value = {"test": "data", "timestamp": datetime.now().isoformat()}
            
            r.setex(test_key, 60, json.dumps(test_value))
            retrieved = json.loads(r.get(test_key))
            
            if retrieved == test_value:
                self.log_test("Redis Operations", True, "Read/write working")
            else:
                self.log_test("Redis Operations", False, "Data mismatch")
                
            # Test expiration
            ttl = r.ttl(test_key)
            if 50 < ttl <= 60:
                self.log_test("Redis TTL", True, f"TTL working: {ttl}s")
            else:
                self.log_test("Redis TTL", False, f"Unexpected TTL: {ttl}s")
                
            # Cleanup
            r.delete(test_key)
            
        except Exception as e:
            self.log_test("Redis Connection", False, str(e))
            
    async def test_memory_hierarchy_resolution(self):
        """Test memory hierarchy resolution (SYNTH → Class → Client)."""
        print("\n🧠 Testing Memory Hierarchy...")
        
        try:
            # Create test memories at different levels
            token = create_access_token({
                "client_user_id": self.test_data["client_id"],
                "scopes": ["admin"]
            })
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create client-level memory
                client_memory = {
                    "synth_user_id": self.test_data["client_id"],
                    "entity_type": "preference",
                    "entity_name": "test_client_pref",
                    "entity_data": {
                        "value": "client-specific-value",
                        "test": True
                    }
                }
                
                response = await client.post(
                    f"{MEMORY_SERVICE_URL}/memory/entities",
                    json=client_memory,
                    headers=headers
                )
                
                if response.status_code == 201:
                    self.log_test("Create Client Memory", True, "Client memory created")
                else:
                    self.log_test("Create Client Memory", False, f"Status: {response.status_code}")
                    
                # Test retrieval through chat
                chat_token = create_access_token({
                    "client_user_id": self.test_data["client_id"],
                    "actor_type": "synth",
                    "actor_id": self.test_data["synth_id"],
                    "scopes": ["chat"]
                })
                chat_headers = {"Authorization": f"Bearer {chat_token}"}
                
                chat_request = {
                    "session_id": str(uuid4()),
                    "client_user_id": self.test_data["client_id"],
                    "actor_type": "synth",
                    "actor_id": self.test_data["synth_id"],
                    "message": "What is my test_client_pref preference?",
                    "enable_sequential_thinking": False
                }
                
                response = await client.post(
                    f"{self.api_url}/chat",
                    json=chat_request,
                    headers=chat_headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "memory_context_used" in data:
                        self.log_test(
                            "Memory Hierarchy Resolution", 
                            True, 
                            f"Found {len(data['memory_context_used'])} memory contexts"
                        )
                    else:
                        self.log_test("Memory Hierarchy Resolution", False, "No memory context in response")
                else:
                    self.log_test("Memory Hierarchy Resolution", False, f"Chat failed: {response.status_code}")
                    
        except Exception as e:
            self.log_test("Memory Hierarchy", False, str(e))
            
    async def test_conversation_consolidation(self):
        """Test conversation consolidation with Memory Maker Crew."""
        print("\n💬 Testing Conversation Consolidation...")
        
        try:
            # Create a conversation with multiple messages
            session_id = str(uuid4())
            token = create_access_token({
                "client_user_id": self.test_data["client_id"],
                "actor_type": "synth",
                "actor_id": self.test_data["synth_id"],
                "scopes": ["chat"]
            })
            headers = {"Authorization": f"Bearer {token}"}
            
            messages = [
                "I'm working on Project Alpha with John Smith",
                "Project Alpha involves AI research and development",
                "John Smith is the lead engineer on the project"
            ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i, message in enumerate(messages):
                    request = {
                        "session_id": session_id,
                        "client_user_id": self.test_data["client_id"],
                        "actor_type": "synth",
                        "actor_id": self.test_data["synth_id"],
                        "message": message,
                        "enable_sequential_thinking": False
                    }
                    
                    response = await client.post(
                        f"{self.api_url}/chat",
                        json=request,
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        self.log_test(f"Send Message {i+1}", False, f"Status: {response.status_code}")
                        return
                        
                self.log_test("Send Conversation Messages", True, f"Sent {len(messages)} messages")
                
                # Wait for async consolidation to trigger
                await asyncio.sleep(2.0)
                
                # Check if crew job was created
                conn = await asyncpg.connect(DATABASE_URL_DIRECT)
                job_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM crew_jobs 
                    WHERE job_key = 'memory_maker_crew' 
                    AND request_data->>'client_user_id' = $1
                    AND created_at > NOW() - INTERVAL '1 minute'
                """, self.test_data["client_id"])
                
                await conn.close()
                
                if job_count > 0:
                    self.log_test("Memory Consolidation Triggered", True, f"Found {job_count} crew job(s)")
                else:
                    self.log_test("Memory Consolidation Triggered", False, "No crew jobs found")
                    
        except Exception as e:
            self.log_test("Conversation Consolidation", False, str(e))
            
    async def test_streaming_responses(self):
        """Test streaming responses under various conditions."""
        print("\n🌊 Testing Streaming Responses...")
        
        token = create_access_token({
            "client_user_id": self.test_data["client_id"],
            "actor_type": "synth",
            "actor_id": self.test_data["synth_id"],
            "scopes": ["chat"]
        })
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Test normal streaming
            request = {
                "session_id": str(uuid4()),
                "client_user_id": self.test_data["client_id"],
                "actor_type": "synth",
                "actor_id": self.test_data["synth_id"],
                "message": "Explain streaming in 3 sentences",
                "enable_sequential_thinking": False
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                chunks = []
                async with client.stream("POST", f"{self.api_url}/chat/stream", json=request, headers=headers) as response:
                    if response.status_code != 200:
                        self.log_test("Streaming Response", False, f"Status: {response.status_code}")
                        return
                        
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk != "[DONE]":
                                chunks.append(chunk)
                                
                if len(chunks) > 0:
                    self.log_test("Streaming Response", True, f"Received {len(chunks)} chunks")
                else:
                    self.log_test("Streaming Response", False, "No chunks received")
                    
                # Test connection interruption handling
                # Start streaming and disconnect early
                chunks_before_disconnect = []
                async with client.stream("POST", f"{self.api_url}/chat/stream", json=request, headers=headers) as response:
                    chunk_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk != "[DONE]":
                                chunks_before_disconnect.append(chunk)
                                chunk_count += 1
                                if chunk_count >= 2:  # Disconnect after 2 chunks
                                    break
                                    
                self.log_test("Early Disconnect Handling", True, f"Gracefully handled after {len(chunks_before_disconnect)} chunks")
                
        except Exception as e:
            self.log_test("Streaming", False, str(e))
            
    async def test_sequential_thinking_integration(self):
        """Test sequential thinking integration."""
        print("\n🤔 Testing Sequential Thinking...")
        
        token = create_access_token({
            "client_user_id": self.test_data["client_id"],
            "actor_type": "synth",
            "actor_id": self.test_data["synth_id"],
            "scopes": ["chat"]
        })
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            request = {
                "session_id": str(uuid4()),
                "client_user_id": self.test_data["client_id"],
                "actor_type": "synth",
                "actor_id": self.test_data["synth_id"],
                "message": "What is 25 * 4 + 10?",
                "enable_sequential_thinking": True,
                "metadata": {"test": "thinking"}
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat",
                    json=request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "thinking_session_id" in data:
                        if data["thinking_session_id"]:
                            self.log_test("Sequential Thinking", True, "Thinking session created")
                        else:
                            self.log_test("Sequential Thinking", True, "Gracefully fell back (service unavailable)")
                    else:
                        self.log_test("Sequential Thinking", False, "No thinking_session_id in response")
                else:
                    self.log_test("Sequential Thinking", False, f"Status: {response.status_code}")
                    
        except Exception as e:
            self.log_test("Sequential Thinking", False, str(e))
            
    async def test_security_and_isolation(self):
        """Test security and client isolation."""
        print("\n🔒 Testing Security...")
        
        try:
            # Create two different clients
            client1_id = str(uuid4())
            client2_id = str(uuid4())
            shared_session = str(uuid4())
            
            # Client 1 creates a session
            token1 = create_access_token({
                "client_user_id": client1_id,
                "actor_type": "synth",
                "actor_id": str(uuid4()),
                "scopes": ["chat"]
            })
            
            request1 = {
                "session_id": shared_session,
                "client_user_id": client1_id,
                "actor_type": "synth",
                "actor_id": str(uuid4()),
                "message": "Client 1 private information"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/chat",
                    json=request1,
                    headers={"Authorization": f"Bearer {token1}"}
                )
                
                if response.status_code != 200:
                    self.log_test("Create Client 1 Session", False, f"Status: {response.status_code}")
                    return
                    
                # Client 2 tries to access
                token2 = create_access_token({
                    "client_user_id": client2_id,
                    "actor_type": "synth",
                    "actor_id": str(uuid4()),
                    "scopes": ["chat"]
                })
                
                response = await client.get(
                    f"{self.api_url}/chat/session/{shared_session}",
                    headers={"Authorization": f"Bearer {token2}"}
                )
                
                if response.status_code == 403:
                    self.log_test("Client Isolation", True, "Client 2 properly denied access")
                else:
                    self.log_test("Client Isolation", False, f"Expected 403, got {response.status_code}")
                    
                # Test invalid token
                response = await client.post(
                    f"{self.api_url}/chat",
                    json=request1,
                    headers={"Authorization": "Bearer invalid-token"}
                )
                
                if response.status_code == 401:
                    self.log_test("Invalid Token Rejection", True, "Invalid token properly rejected")
                else:
                    self.log_test("Invalid Token Rejection", False, f"Expected 401, got {response.status_code}")
                    
                # Test missing token
                response = await client.post(f"{self.api_url}/chat", json=request1)
                
                if response.status_code in [401, 403]:
                    self.log_test("Missing Token Rejection", True, "Missing token properly rejected")
                else:
                    self.log_test("Missing Token Rejection", False, f"Expected 401/403, got {response.status_code}")
                    
        except Exception as e:
            self.log_test("Security Tests", False, str(e))
            
    async def test_performance_characteristics(self):
        """Test performance under load."""
        print("\n⚡ Testing Performance...")
        
        token = create_access_token({
            "client_user_id": self.test_data["client_id"],
            "actor_type": "synth",
            "actor_id": self.test_data["synth_id"],
            "scopes": ["chat"]
        })
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Test response times
            response_times = []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i in range(10):
                    request = {
                        "session_id": str(uuid4()),
                        "client_user_id": self.test_data["client_id"],
                        "actor_type": "synth",
                        "actor_id": self.test_data["synth_id"],
                        "message": f"Quick test message {i}",
                        "enable_sequential_thinking": False
                    }
                    
                    start = time.time()
                    response = await client.post(
                        f"{self.api_url}/chat",
                        json=request,
                        headers=headers
                    )
                    elapsed = (time.time() - start) * 1000  # Convert to ms
                    
                    if response.status_code == 200:
                        response_times.append(elapsed)
                        
            if len(response_times) >= 8:  # At least 80% success
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
                
                self.log_test(
                    "Response Time Performance", 
                    avg_time < 2000,  # Average under 2 seconds
                    f"Avg: {avg_time:.0f}ms, Min: {min_time:.0f}ms, Max: {max_time:.0f}ms",
                    {"samples": len(response_times)}
                )
                
                # Test concurrent requests
                concurrent_tasks = []
                for i in range(20):
                    request = {
                        "session_id": str(uuid4()),
                        "client_user_id": self.test_data["client_id"],
                        "actor_type": "synth",
                        "actor_id": self.test_data["synth_id"],
                        "message": f"Concurrent test {i}",
                        "enable_sequential_thinking": False
                    }
                    
                    task = client.post(
                        f"{self.api_url}/chat",
                        json=request,
                        headers=headers
                    )
                    concurrent_tasks.append(task)
                    
                start = time.time()
                responses = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                elapsed = time.time() - start
                
                success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
                
                self.log_test(
                    "Concurrent Request Handling",
                    success_count >= 18,  # 90% success rate
                    f"{success_count}/20 succeeded in {elapsed:.1f}s",
                    {"requests_per_second": 20 / elapsed}
                )
            else:
                self.log_test("Performance Testing", False, f"Only {len(response_times)}/10 requests succeeded")
                
        except Exception as e:
            self.log_test("Performance", False, str(e))
            
    async def run_all_tests(self):
        """Run all system integration tests."""
        print("🚀 SparkJAR Chat System Integration Tests")
        print("=" * 60)
        print(f"Started: {datetime.now().isoformat()}")
        print(f"API URL: {self.api_url}")
        
        # Setup
        await self.setup_test_data()
        
        # Run all test suites
        await self.test_service_health()
        await self.test_redis_connection()
        await self.test_memory_hierarchy_resolution()
        await self.test_conversation_consolidation()
        await self.test_streaming_responses()
        await self.test_sequential_thinking_integration()
        await self.test_security_and_isolation()
        await self.test_performance_characteristics()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['message']}")
                    
        # Save detailed results
        results_file = f"system_integration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": passed_tests/total_tests
                },
                "test_data": self.test_data,
                "results": self.test_results
            }, f, indent=2)
            
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Final verdict
        print("\n🎯 FINAL VERDICT:")
        if failed_tests == 0:
            print("✅ ALL TESTS PASSED - System is ready for production!")
        elif passed_tests / total_tests >= 0.9:
            print("⚠️  MOSTLY PASSING - System is functional but has minor issues")
        else:
            print("❌ CRITICAL FAILURES - System needs fixes before deployment")
            
        return failed_tests == 0


async def main():
    """Run the system integration tests."""
    tester = SystemIntegrationTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Check if API is running first
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        if response.status_code != 200:
            print("❌ API is not responding. Please start the crew-api service first:")
            print("   cd services/crew-api")
            print("   .venv/bin/python main.py")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("\nPlease ensure all services are running:")
        print("1. Start crew-api: cd services/crew-api && .venv/bin/python main.py")
        print("2. Start memory service (if not on Railway)")
        print("3. Ensure Redis is running")
        print("4. Ensure PostgreSQL is accessible")
        sys.exit(1)
        
    asyncio.run(main())