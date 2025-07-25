#!/usr/bin/env python3
"""
Create a test JWT token for testing the chat API
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_token(
    client_id: str = None,
    user_id: str = None,
    scopes: list = None,
    expires_hours: int = 24
):
    """Create a test JWT token with proper claims"""
    
    # Get secret key from environment
    secret_key = os.getenv("API_SECRET_KEY", "development-secret-key")
    
    # Default values
    if not client_id:
        client_id = str(uuid4())
    if not user_id:
        user_id = str(uuid4())
    if not scopes:
        scopes = ["sparkjar_internal"]
    
    # Create token payload
    payload = {
        "sub": user_id,
        "client_id": client_id,
        "user_id": user_id,
        "scopes": scopes,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
        "type": "access"
    }
    
    # Encode token
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    return token, payload


def main():
    """Generate and display test token"""
    
    print("Creating test JWT token for SparkJAR Chat API...")
    print("-" * 50)
    
    # Create token
    token, payload = create_test_token()
    
    # Display information
    print(f"Client ID: {payload['client_id']}")
    print(f"User ID: {payload['user_id']}")
    print(f"Scopes: {', '.join(payload['scopes'])}")
    print(f"Expires: {datetime.fromtimestamp(payload['exp']).isoformat()}")
    print("-" * 50)
    print(f"Token:\n{token}")
    print("-" * 50)
    
    # Show example usage
    api_url = os.getenv("CREW_API_URL", "https://crew-api.up.railway.app")
    print(f"\nExample usage:")
    print(f"""
curl -X POST {api_url}/chat/v1/messages \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "message": "Hello, can you help me?",
    "mode": "tutor",
    "session_id": "test-session-001"
  }}'
""")


if __name__ == "__main__":
    main()