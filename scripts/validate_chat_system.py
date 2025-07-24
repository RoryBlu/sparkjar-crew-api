#!/usr/bin/env python3
"""
Simple system validation script for chat functionality.
Checks that all key components are working together.
"""

import sys
import os
import httpx
import asyncio
from uuid import uuid4
import json
import redis
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.auth import create_access_token
from src.config import (
    REDIS_URL, 
    MEMORY_SERVICE_URL, 
    THINKING_SERVICE_URL, 
    API_URL,
    DATABASE_URL_DIRECT
)


class ChatSystemValidator:
    """Validates chat system integration."""
    
    def __init__(self):
        self.results = {}
        self.api_url = os.getenv("API_URL", "http://localhost:8000")
        
    async def check_redis_connection(self):
        """Check Redis connectivity."""
        try:
            r = redis.from_url(REDIS_URL)
            r.ping()
            self.results["redis"] = {"status": "✅", "message": "Redis connected"}
            return True
        except Exception as e:
            self.results["redis"] = {"status": "❌", "message": f"Redis error: {str(e)}"}
            return False
            
    async def check_memory_service(self):
        """Check Memory Service connectivity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{MEMORY_SERVICE_URL}/health")
                if response.status_code == 200:
                    self.results["memory_service"] = {
                        "status": "✅", 
                        "message": "Memory Service healthy"
                    }
                    return True
                else:
                    self.results["memory_service"] = {
                        "status": "❌", 
                        "message": f"Memory Service returned {response.status_code}"
                    }
                    return False
        except Exception as e:
            self.results["memory_service"] = {
                "status": "❌", 
                "message": f"Memory Service error: {str(e)}"
            }
            return False
            
    async def check_thinking_service(self):
        """Check Thinking Service connectivity (optional)."""
        if not THINKING_SERVICE_URL:
            self.results["thinking_service"] = {
                "status": "⚠️", 
                "message": "Thinking Service not configured (optional)"
            }
            return True
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{THINKING_SERVICE_URL}/health")
                if response.status_code == 200:
                    self.results["thinking_service"] = {
                        "status": "✅", 
                        "message": "Thinking Service healthy"
                    }
                    return True
                else:
                    self.results["thinking_service"] = {
                        "status": "⚠️", 
                        "message": f"Thinking Service returned {response.status_code} (optional)"
                    }
                    return True  # Optional service
        except Exception as e:
            self.results["thinking_service"] = {
                "status": "⚠️", 
                "message": f"Thinking Service unavailable: {str(e)} (optional)"
            }
            return True  # Optional service
            
    async def check_database(self):
        """Check database connectivity."""
        try:
            import asyncpg
            conn = await asyncpg.connect(DATABASE_URL_DIRECT)
            
            # Check essential tables
            tables_query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('crew_jobs', 'object_schemas', 'crew_configurations')
            """
            rows = await conn.fetch(tables_query)
            tables = [row['tablename'] for row in rows]
            
            await conn.close()
            
            if len(tables) >= 3:
                self.results["database"] = {
                    "status": "✅", 
                    "message": f"Database connected, found {len(tables)} required tables"
                }
                return True
            else:
                self.results["database"] = {
                    "status": "❌", 
                    "message": f"Missing tables. Found: {tables}"
                }
                return False
        except Exception as e:
            self.results["database"] = {
                "status": "❌", 
                "message": f"Database error: {str(e)}"
            }
            return False
            
    async def test_chat_flow(self):
        """Test a complete chat flow."""
        try:
            # Create test data
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
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test chat request
            request = {
                "session_id": session_id,
                "client_user_id": client_id,
                "actor_type": "synth",
                "actor_id": actor_id,
                "message": "System validation test message",
                "enable_sequential_thinking": False,
                "metadata": {"test": "validation"}
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send chat request
                response = await client.post(
                    f"{self.api_url}/chat",
                    json=request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "response" in data and data["session_id"] == session_id:
                        self.results["chat_flow"] = {
                            "status": "✅", 
                            "message": "Chat flow working correctly"
                        }
                        
                        # Check session retrieval
                        session_response = await client.get(
                            f"{self.api_url}/chat/session/{session_id}",
                            headers=headers
                        )
                        
                        if session_response.status_code == 200:
                            self.results["session_management"] = {
                                "status": "✅", 
                                "message": "Session management working"
                            }
                        else:
                            self.results["session_management"] = {
                                "status": "❌", 
                                "message": f"Session retrieval failed: {session_response.status_code}"
                            }
                            
                        # Clean up
                        await client.delete(
                            f"{self.api_url}/chat/session/{session_id}",
                            headers=headers
                        )
                        
                        return True
                    else:
                        self.results["chat_flow"] = {
                            "status": "❌", 
                            "message": "Chat response invalid"
                        }
                        return False
                else:
                    self.results["chat_flow"] = {
                        "status": "❌", 
                        "message": f"Chat request failed: {response.status_code}"
                    }
                    return False
                    
        except Exception as e:
            self.results["chat_flow"] = {
                "status": "❌", 
                "message": f"Chat flow error: {str(e)}"
            }
            return False
            
    async def test_memory_integration(self):
        """Test memory service integration."""
        try:
            # Create test data
            client_id = str(uuid4())
            actor_id = str(uuid4())
            
            # Test memory search through chat
            token_data = {
                "client_user_id": client_id,
                "actor_type": "synth",
                "actor_id": actor_id,
                "scopes": ["chat"]
            }
            token = create_access_token(token_data)
            headers = {"Authorization": f"Bearer {token}"}
            
            request = {
                "session_id": str(uuid4()),
                "client_user_id": client_id,
                "actor_type": "synth",
                "actor_id": actor_id,
                "message": "Search for information about projects and entities",
                "enable_sequential_thinking": False
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat",
                    json=request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Check if memory context was used (even if empty)
                    if "memory_context_used" in data:
                        self.results["memory_integration"] = {
                            "status": "✅", 
                            "message": f"Memory integration working, found {len(data.get('memory_context_used', []))} contexts"
                        }
                        return True
                    else:
                        self.results["memory_integration"] = {
                            "status": "⚠️", 
                            "message": "Memory integration partially working"
                        }
                        return True
                else:
                    self.results["memory_integration"] = {
                        "status": "❌", 
                        "message": f"Memory integration test failed: {response.status_code}"
                    }
                    return False
                    
        except Exception as e:
            self.results["memory_integration"] = {
                "status": "❌", 
                "message": f"Memory integration error: {str(e)}"
            }
            return False
            
    async def run_validation(self):
        """Run all validation checks."""
        print("🔍 SparkJAR Chat System Validation")
        print("=" * 50)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"API URL: {self.api_url}")
        print()
        
        # Check API health first
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/health")
                if response.status_code == 200:
                    print("✅ API is running")
                else:
                    print(f"❌ API health check failed: {response.status_code}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print("\nMake sure the crew-api service is running:")
            print("  cd services/crew-api")
            print("  .venv/bin/python main.py")
            return
            
        # Run all checks
        checks = [
            ("Redis Connection", self.check_redis_connection()),
            ("Database Connection", self.check_database()),
            ("Memory Service", self.check_memory_service()),
            ("Thinking Service", self.check_thinking_service()),
            ("Chat Flow", self.test_chat_flow()),
            ("Memory Integration", self.test_memory_integration())
        ]
        
        print("\n📋 Running System Checks:")
        print("-" * 50)
        
        for name, check_coro in checks:
            print(f"Checking {name}...", end=" ", flush=True)
            await check_coro
            result = self.results.get(name.lower().replace(" ", "_"), {})
            print(f"{result.get('status', '?')} {result.get('message', '')}")
            
        # Summary
        print("\n📊 Validation Summary:")
        print("-" * 50)
        
        total_checks = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "✅")
        warnings = sum(1 for r in self.results.values() if r["status"] == "⚠️")
        failed = sum(1 for r in self.results.values() if r["status"] == "❌")
        
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"❌ Failed: {failed}")
        
        # Overall status
        print("\n🎯 Overall Status:")
        if failed == 0:
            if warnings > 0:
                print("✅ System is operational (with optional features disabled)")
            else:
                print("✅ System is fully operational!")
        else:
            print("❌ System has issues that need to be resolved")
            print("\nFailed checks:")
            for name, result in self.results.items():
                if result["status"] == "❌":
                    print(f"  - {name}: {result['message']}")
                    
        # Save results
        results_file = f"chat_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "api_url": self.api_url,
                "results": self.results,
                "summary": {
                    "total": total_checks,
                    "passed": passed,
                    "warnings": warnings,
                    "failed": failed
                }
            }, f, indent=2)
            
        print(f"\n💾 Results saved to: {results_file}")


async def main():
    """Run the validation."""
    validator = ChatSystemValidator()
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main())