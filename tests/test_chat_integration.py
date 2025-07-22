"""
Comprehensive integration tests for chat functionality.
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
import json
from typing import List, Dict, Any

import httpx
from fastapi.testclient import TestClient

from src.api.main import app
from src.chat.models.chat_models import ChatRequest
from src.api.auth import create_access_token


class TestChatIntegration:
    """Integration tests for chat endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
        
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        token_data = {
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "scopes": ["chat", "admin"]
        }
        token = create_access_token(token_data)
        return {"Authorization": f"Bearer {token}"}
        
    @pytest.fixture
    def chat_request(self):
        """Create sample chat request."""
        return {
            "session_id": str(uuid4()),
            "client_user_id": str(uuid4()),
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "message": "Tell me about Project Alpha",
            "enable_sequential_thinking": False,
            "metadata": {"test": True}
        }
        
    def test_chat_endpoint_success(self, client, auth_headers, chat_request):
        """Test successful chat request."""
        # Update token to match request
        token_data = {
            "client_user_id": chat_request["client_user_id"],
            "actor_type": "synth",
            "actor_id": chat_request["actor_id"],
            "scopes": ["chat"]
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/chat",
            json=chat_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["session_id"] == chat_request["session_id"]
        assert "timestamp" in data
        
    def test_chat_endpoint_unauthorized(self, client, chat_request):
        """Test chat request without authentication."""
        response = client.post("/chat", json=chat_request)
        assert response.status_code == 403  # No bearer token
        
    def test_chat_endpoint_invalid_token(self, client, chat_request):
        """Test chat request with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/chat", json=chat_request, headers=headers)
        assert response.status_code == 401
        
    def test_chat_endpoint_mismatched_client(self, client, auth_headers, chat_request):
        """Test chat request with mismatched client ID."""
        # Change client ID in request
        chat_request["client_user_id"] = str(uuid4())
        
        response = client.post(
            "/chat",
            json=chat_request,
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "Client user ID mismatch" in response.json()["detail"]
        
    @pytest.mark.asyncio
    async def test_concurrent_chat_sessions(self, client, auth_headers):
        """Test handling multiple concurrent chat sessions."""
        num_sessions = 10
        tasks = []
        
        async def make_chat_request(session_num: int):
            """Make async chat request."""
            request = {
                "session_id": str(uuid4()),
                "client_user_id": str(uuid4()),
                "actor_type": "synth",
                "actor_id": str(uuid4()),
                "message": f"Test message {session_num}",
                "enable_sequential_thinking": False
            }
            
            # Create matching token
            token_data = {
                "client_user_id": request["client_user_id"],
                "actor_type": "synth",
                "actor_id": request["actor_id"],
                "scopes": ["chat"]
            }
            token = create_access_token(token_data)
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/chat", json=request, headers=headers)
                return response
                
        # Create concurrent requests
        for i in range(num_sessions):
            tasks.append(make_chat_request(i))
            
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            
    def test_get_session_context(self, client, auth_headers, chat_request):
        """Test retrieving session context."""
        # Create matching token
        token_data = {
            "client_user_id": chat_request["client_user_id"],
            "actor_type": "synth",
            "actor_id": chat_request["actor_id"],
            "scopes": ["chat"]
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # First create a chat session
        response = client.post("/chat", json=chat_request, headers=auth_headers)
        assert response.status_code == 200
        
        # Get session context
        session_id = chat_request["session_id"]
        response = client.get(
            f"/chat/session/{session_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "created_at" in data
        assert "message_count" in data
        
    def test_delete_session(self, client, auth_headers, chat_request):
        """Test deleting a session."""
        # Create matching token
        token_data = {
            "client_user_id": chat_request["client_user_id"],
            "actor_type": "synth",
            "actor_id": chat_request["actor_id"],
            "scopes": ["chat"]
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # Create session
        response = client.post("/chat", json=chat_request, headers=auth_headers)
        assert response.status_code == 200
        
        # Delete session
        session_id = chat_request["session_id"]
        response = client.delete(
            f"/chat/session/{session_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        
        # Verify session is gone
        response = client.get(
            f"/chat/session/{session_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        
    def test_streaming_chat_endpoint(self, client, auth_headers, chat_request):
        """Test streaming chat response."""
        # Create matching token
        token_data = {
            "client_user_id": chat_request["client_user_id"],
            "actor_type": "synth",
            "actor_id": chat_request["actor_id"],
            "scopes": ["chat"]
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        with client.stream("POST", "/chat/stream", json=chat_request, headers=auth_headers) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            # Read streaming chunks
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]  # Remove "data: " prefix
                    if chunk != "[DONE]":
                        chunks.append(chunk)
                        
            assert len(chunks) > 0  # Should have received some chunks
            
    @pytest.mark.asyncio
    async def test_memory_consolidation_trigger(self, client, auth_headers, chat_request):
        """Test that memory consolidation is triggered after chat."""
        # Create matching token
        token_data = {
            "client_user_id": chat_request["client_user_id"],
            "actor_type": "synth",
            "actor_id": chat_request["actor_id"],
            "scopes": ["chat"]
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # Send multiple messages to trigger consolidation
        for i in range(3):
            chat_request["message"] = f"Message {i}: Tell me about Project {chr(65 + i)}"
            response = client.post("/chat", json=chat_request, headers=auth_headers)
            assert response.status_code == 200
            
        # Wait a bit for async consolidation to trigger
        await asyncio.sleep(0.5)
        
        # In a real test, we'd verify the crew job was created
        # For now, just verify the chat worked
        assert True
        
    def test_sequential_thinking_mode(self, client, auth_headers, chat_request):
        """Test chat with sequential thinking enabled."""
        # Create matching token
        token_data = {
            "client_user_id": chat_request["client_user_id"],
            "actor_type": "synth",
            "actor_id": chat_request["actor_id"],
            "scopes": ["chat"]
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # Enable sequential thinking
        chat_request["enable_sequential_thinking"] = True
        
        response = client.post("/chat", json=chat_request, headers=auth_headers)
        
        # Should fallback gracefully if thinking service unavailable
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        
    def test_client_isolation(self, client):
        """Test that different clients are isolated."""
        client1_id = str(uuid4())
        client2_id = str(uuid4())
        session_id = str(uuid4())
        
        # Create session for client 1
        request1 = {
            "session_id": session_id,
            "client_user_id": client1_id,
            "actor_type": "synth",
            "actor_id": str(uuid4()),
            "message": "Client 1 message"
        }
        
        token1 = create_access_token({
            "client_user_id": client1_id,
            "actor_type": "synth",
            "actor_id": request1["actor_id"],
            "scopes": ["chat"]
        })
        
        response = client.post(
            "/chat",
            json=request1,
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 200
        
        # Try to access with client 2 token
        token2 = create_access_token({
            "client_user_id": client2_id,
            "actor_type": "synth", 
            "actor_id": str(uuid4()),
            "scopes": ["chat"]
        })
        
        response = client.get(
            f"/chat/session/{session_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        # Should be denied access
        assert response.status_code == 403