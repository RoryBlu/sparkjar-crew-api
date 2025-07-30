#!/usr/bin/env python3
"""
Interactive chat interface for querying Vervelyn company policies.
This script:
1. First ensures the policies are stored in memory using the memory maker crew
2. Then provides an interactive chat interface to query those policies
"""

import asyncio
import json
import time
import os
from uuid import UUID
from typing import Dict, Any, Optional
import httpx
import jwt
from datetime import datetime
from pathlib import Path

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
JWT_SECRET = os.getenv("API_SECRET_KEY", "test-secret-key-change-in-production")
VERVELYN_CLIENT_ID = "f7264b3a-2b15-4d52-9f6a-8c7d89e3a123"
VERVELYN_ACTOR_ID = "f7264b3a-2b15-4d52-9f6a-8c7d89e3a123"


def create_auth_token(scopes=None):
    """Create a JWT token for authentication."""
    if scopes is None:
        scopes = ["sparkjar_internal"]
    
    payload = {
        "client_user_id": VERVELYN_CLIENT_ID,
        "actor_type": "client",
        "actor_id": VERVELYN_ACTOR_ID,
        "scopes": scopes,
        "exp": int(time.time()) + 3600  # 1 hour
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def check_existing_memories():
    """Check if Vervelyn policies are already in memory."""
    print("\n🔍 Checking for existing Vervelyn policy memories...")
    
    token = create_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Search for existing memories
    search_request = {
        "client_id": VERVELYN_CLIENT_ID,
        "actor_type": "client",
        "actor_id": VERVELYN_ACTOR_ID,
        "query": "Vervelyn Publishing corporate policy external communications",
        "limit": 5
    }
    
    try:
        # Try memory service endpoint
        memory_url = os.getenv("MEMORY_API_URL", "http://localhost:8001")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{memory_url}/memory/search",
                json=search_request,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    print("  ✅ Found existing Vervelyn policy memories")
                    print(f"     Number of results: {len(data['results'])}")
                    return True
                else:
                    print("  ⚠️  No Vervelyn policy memories found")
                    return False
            else:
                print(f"  ⚠️  Could not check memories: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"  ⚠️  Error checking memories: {e}")
        return False


async def ingest_vervelyn_policies():
    """Ingest Vervelyn policies using the memory maker crew."""
    print("\n📥 Ingesting Vervelyn policies using Memory Maker Crew...")
    
    # Load the payload
    payload_path = Path(__file__).parent.parent / "test_payloads" / "vervelyn_corporate_policy_payload.json"
    
    if not payload_path.exists():
        print(f"  ❌ Payload file not found: {payload_path}")
        return False
        
    with open(payload_path, 'r') as f:
        payload = json.load(f)
    
    # Create crew job
    token = create_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Submit crew job
            response = await client.post(
                f"{API_URL}/crew_job",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"  ❌ Failed to create crew job: {response.status_code}")
                print(f"     Error: {response.text}")
                return False
                
            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"  ✅ Created crew job: {job_id}")
            
            # Poll for completion
            print("  ⏳ Waiting for memory ingestion to complete...")
            max_attempts = 60  # 5 minutes max
            for i in range(max_attempts):
                await asyncio.sleep(5)  # Check every 5 seconds
                
                status_response = await client.get(
                    f"{API_URL}/crew_job/{job_id}",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status")
                    
                    if status == "completed":
                        print("  ✅ Memory ingestion completed successfully!")
                        result = status_data.get("result", {})
                        print(f"     Entities created: {len(result.get('entities_created', []))}")
                        print(f"     Entities updated: {len(result.get('entities_updated', []))}")
                        print(f"     Observations added: {len(result.get('observations_added', []))}")
                        return True
                    elif status == "failed":
                        print("  ❌ Memory ingestion failed!")
                        print(f"     Error: {status_data.get('error', 'Unknown error')}")
                        return False
                    else:
                        print(f"  ⏳ Status: {status} ({i+1}/{max_attempts})")
                        
            print("  ❌ Timeout waiting for memory ingestion")
            return False
            
    except Exception as e:
        print(f"  ❌ Error during ingestion: {e}")
        return False


async def interactive_chat():
    """Interactive chat interface for querying Vervelyn policies."""
    print("\n💬 Starting interactive chat with Vervelyn policies...")
    print("   Type 'exit' or 'quit' to end the session")
    print("   Type 'help' for example questions\n")
    
    token = create_auth_token(scopes=["chat", "sparkjar_internal"])
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a chat session
    session_id = str(UUID("22222222-2222-2222-2222-222222222222"))
    
    while True:
        try:
            # Get user input
            user_message = input("\n🧑 You: ").strip()
            
            if user_message.lower() in ['exit', 'quit']:
                print("\n👋 Goodbye!")
                break
                
            if user_message.lower() == 'help':
                print("\n📚 Example questions:")
                print("   - What are the memory curation principles at Vervelyn?")
                print("   - How should synths handle crisis situations?")
                print("   - What are the requirements for external communications?")
                print("   - Explain the role of Memory Makers")
                print("   - What privacy and security measures are in place?")
                continue
                
            if not user_message:
                continue
                
            # Send chat request
            chat_request = {
                "session_id": session_id,
                "client_user_id": VERVELYN_CLIENT_ID,
                "actor_type": "synth",
                "actor_id": "33333333-3333-3333-3333-333333333333",  # Chat synth
                "message": user_message,
                "enable_sequential_thinking": True,
                "context": {
                    "topic": "Vervelyn Publishing corporate policies",
                    "retrieval_enabled": True
                }
            }
            
            print("\n🤖 Assistant: ", end="", flush=True)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{API_URL}/chat",
                    json=chat_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    assistant_response = data.get("response", "I couldn't generate a response.")
                    print(assistant_response)
                    
                    # Show thinking process if available
                    if data.get("thinking_session_id"):
                        print(f"\n   💭 Thinking session: {data['thinking_session_id']}")
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    
        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue


async def main():
    """Main function to orchestrate the policy chat system."""
    print("🚀 Vervelyn Policy Chat System")
    print("================================")
    
    # Check if policies are already in memory
    has_memories = await check_existing_memories()
    
    if not has_memories:
        # Ingest policies
        success = await ingest_vervelyn_policies()
        if not success:
            print("\n❌ Failed to ingest policies. Cannot proceed with chat.")
            return
            
        # Wait a bit for memories to be fully indexed
        print("\n⏳ Waiting for memory indexing...")
        await asyncio.sleep(5)
    
    # Start interactive chat
    await interactive_chat()


if __name__ == "__main__":
    asyncio.run(main())