#!/usr/bin/env python3
"""
Simple chat interface for testing Vervelyn policy queries.
Assumes the memory maker crew has already been run to ingest the policies.
"""

import asyncio
import httpx
import json
import os
import time
from uuid import uuid4
import jwt
from typing import Optional

# Configuration
API_URL = os.getenv("SPARKJAR_API_URL", "http://localhost:8000")
JWT_SECRET = os.getenv("API_SECRET_KEY", "test-secret-key-change-in-production")

# Vervelyn IDs
VERVELYN_CLIENT_ID = "f7264b3a-2b15-4d52-9f6a-8c7d89e3a123"
CHAT_SYNTH_ID = str(uuid4())  # Create a synth for chatting


def create_auth_token():
    """Create a JWT token for chat access."""
    payload = {
        "client_user_id": VERVELYN_CLIENT_ID,
        "actor_type": "synth",
        "actor_id": CHAT_SYNTH_ID,
        "scopes": ["chat", "sparkjar_internal"],
        "exp": int(time.time()) + 3600  # 1 hour
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def send_chat_message(message: str, session_id: Optional[str] = None):
    """Send a chat message and get response."""
    token = create_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create chat request
    chat_request = {
        "client_user_id": VERVELYN_CLIENT_ID,
        "actor_type": "synth",
        "actor_id": CHAT_SYNTH_ID,
        "message": message,
        "enable_sequential_thinking": True,
        "stream_response": False  # Non-streaming for simplicity
    }
    
    if session_id:
        chat_request["session_id"] = session_id
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_URL}/chat",
                json=chat_request,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Details: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None


async def interactive_chat():
    """Run an interactive chat session."""
    print("\n🤖 Vervelyn Policy Chat Interface")
    print("==================================")
    print("Ask questions about Vervelyn Publishing policies.")
    print("Type 'exit' to quit, 'help' for examples.\n")
    
    session_id = None
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if user_input.lower() == 'exit':
                print("\nGoodbye! 👋")
                break
                
            if user_input.lower() == 'help':
                print("\n📚 Example questions:")
                print("- What is Vervelyn's policy on external communications?")
                print("- How do Memory Makers work at Vervelyn?")
                print("- What are the requirements for synths in public communications?")
                print("- Explain the memory curation principles")
                print("- What happens during a crisis at Vervelyn?\n")
                continue
                
            if not user_input:
                continue
            
            # Send message
            print("\nAssistant: ", end="", flush=True)
            result = await send_chat_message(user_input, session_id)
            
            if result:
                # Extract session ID for continuity
                if not session_id and result.get("session_id"):
                    session_id = result["session_id"]
                
                # Print response
                response_text = result.get("response", "I couldn't generate a response.")
                print(response_text)
                
                # Show thinking info if available
                if result.get("thinking_session_id"):
                    print(f"\n💭 (Used sequential thinking: {result['thinking_session_id']})")
                    
                print()  # Empty line for readability
            else:
                print("Failed to get response.\n")
                
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


async def test_single_query():
    """Test a single query to verify the system works."""
    print("\n🧪 Testing single query...")
    
    test_message = "What are the key principles of memory curation at Vervelyn Publishing?"
    print(f"Question: {test_message}")
    print("\nAnswer: ", end="", flush=True)
    
    result = await send_chat_message(test_message)
    
    if result:
        print(result.get("response", "No response received"))
        if result.get("thinking_session_id"):
            print(f"\n💭 Used sequential thinking: {result['thinking_session_id']}")
        return True
    else:
        print("Failed to get response")
        return False


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run single test query
        success = await test_single_query()
        if not success:
            sys.exit(1)
    else:
        # Run interactive chat
        await interactive_chat()


if __name__ == "__main__":
    asyncio.run(main())