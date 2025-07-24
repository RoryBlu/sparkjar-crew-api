# Chat API Documentation

The Chat API provides conversational AI capabilities with memory context integration, session management, and optional sequential thinking mode.

## Overview

The Chat API is integrated into the Crew API service and provides:
- Stateful conversations with session management
- Hierarchical memory context (SYNTH → SYNTH Class → Client)
- Real-time streaming responses
- Optional sequential thinking for complex reasoning
- Automatic memory consolidation via Memory Maker Crew

## Authentication

All chat endpoints require JWT authentication with the `chat` scope.

### Token Structure
```json
{
  "client_user_id": "uuid",
  "actor_type": "synth|human|system",
  "actor_id": "uuid",
  "scopes": ["chat"],
  "exp": "timestamp"
}
```

## Endpoints

### POST /chat
Process a chat request with memory context.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
  "actor_type": "synth",
  "actor_id": "987fcdeb-51a2-43f1-9abc-123456789012",
  "message": "Tell me about Project Alpha",
  "enable_sequential_thinking": false,
  "metadata": {
    "source": "web_interface",
    "language": "en"
  }
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "789e0123-45bc-67de-89f0-123456789abc",
  "message": "Tell me about Project Alpha",
  "response": "Project Alpha is our new AI initiative...",
  "memory_context_used": ["project_alpha", "john_smith", "ai_initiative"],
  "thinking_session_id": null,
  "metadata": {
    "response_time_ms": 1250,
    "memory_queries": 1,
    "tokens_used": 150
  },
  "timestamp": "2024-07-21T10:30:00Z"
}
```

### POST /chat/stream
Process a chat request with Server-Sent Events streaming.

**Request:** Same as `/chat`

**Response:** Server-Sent Events stream
```
data: Hello! I'll help you

data:  understand Project Alpha.

data:  Project Alpha is

data:  our new AI initiative...

data: [DONE]
```

### GET /chat/session/{session_id}
Retrieve session context information.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_user_id": "123e4567-e89b-12d3-a456-426614174000",
  "actor_id": "987fcdeb-51a2-43f1-9abc-123456789012",
  "created_at": "2024-07-21T10:00:00Z",
  "last_activity": "2024-07-21T10:30:00Z",
  "message_count": 5,
  "has_thinking_session": false,
  "memory_context_count": 3
}
```

### DELETE /chat/session/{session_id}
Delete a chat session and its history.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted": true,
  "timestamp": "2024-07-21T10:35:00Z"
}
```

## Features

### Memory Context Integration
The chat service automatically searches for relevant memories based on:
- Current message content
- Recent conversation history
- SYNTH hierarchy (actor → class → client)

Memory types include:
- Facts and knowledge
- Skills and procedures
- Preferences and decisions
- Entity relationships

### Sequential Thinking Mode
Enable deep reasoning by setting `enable_sequential_thinking: true`:
- Creates structured thought chains
- Shows step-by-step reasoning
- Useful for complex problem solving
- Falls back gracefully if thinking service unavailable

### Session Management
- Sessions stored in Redis for horizontal scaling
- Configurable TTL (default 24 hours)
- Automatic cleanup of expired sessions
- Concurrent session support (10,000+)

### Memory Consolidation
After conversations, the Memory Maker Crew automatically:
- Extracts entities and relationships
- Identifies new facts and insights
- Updates the memory system
- Runs asynchronously without blocking

## Error Handling

### Error Response Format
```json
{
  "error": true,
  "message": "Error description",
  "category": "authentication|validation|memory_service|timeout",
  "details": {},
  "recoverable": true,
  "timestamp": "2024-07-21T10:30:00Z"
}
```

### Common Errors
- `401 Unauthorized`: Invalid or expired token
- `403 Forbidden`: Token valid but insufficient permissions
- `404 Not Found`: Session doesn't exist
- `503 Service Unavailable`: Required service down (Redis, Memory Service)

## Usage Examples

### Python Client Example
```python
import httpx
import json
from uuid import uuid4

# Configuration
API_URL = "http://localhost:8000"
TOKEN = "your-jwt-token"

# Create chat client
client = httpx.Client(
    base_url=API_URL,
    headers={"Authorization": f"Bearer {TOKEN}"}
)

# Start conversation
session_id = str(uuid4())
request = {
    "session_id": session_id,
    "client_user_id": "your-client-id",
    "actor_type": "synth",
    "actor_id": "your-synth-id",
    "message": "What projects are we working on?",
    "enable_sequential_thinking": False
}

# Send chat request
response = client.post("/chat", json=request)
data = response.json()
print(f"Response: {data['response']}")

# Stream response
with client.stream("POST", "/chat/stream", json=request) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            chunk = line[6:]
            if chunk != "[DONE]":
                print(chunk, end="", flush=True)
```

### JavaScript/TypeScript Example
```typescript
interface ChatRequest {
  session_id: string;
  client_user_id: string;
  actor_type: "synth" | "human" | "system";
  actor_id: string;
  message: string;
  enable_sequential_thinking?: boolean;
  metadata?: Record<string, any>;
}

async function chat(request: ChatRequest, token: string): Promise<any> {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(request)
  });
  
  return response.json();
}

// Streaming example
async function streamChat(request: ChatRequest, token: string) {
  const response = await fetch('http://localhost:8000/chat/stream', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(request)
  });
  
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data !== '[DONE]') {
          console.log(data);
        }
      }
    }
  }
}
```

## Performance Considerations

### Caching
- SYNTH context cached for 60 minutes
- Memory search results cached for 15 minutes
- Local and distributed (Redis) cache layers

### Connection Pooling
- HTTP/2 enabled for better multiplexing
- Persistent connections to external services
- Automatic retry with exponential backoff

### Scaling
- Horizontally scalable (stateless design)
- Session state in Redis
- Load balancer with sticky sessions for streams

## Configuration

Key environment variables:
```bash
# Required
REDIS_URL=redis://localhost:6379/0
MEMORY_SERVICE_URL=http://memory-service:8003
JWT_SECRET_KEY=your-secret-key

# Optional
THINKING_SERVICE_URL=http://thinking-service:8004
SESSION_TTL_HOURS=24
MAX_CONVERSATION_HISTORY=100
MEMORY_CACHE_TTL_MINUTES=15
SYNTH_CONTEXT_CACHE_TTL_MINUTES=60
```

## Best Practices

1. **Session Management**
   - Reuse session IDs for conversation continuity
   - Delete sessions when conversations end
   - Don't create new sessions for every message

2. **Memory Usage**
   - Be specific in messages for better memory retrieval
   - Include relevant context in metadata
   - Let the system build context over time

3. **Streaming**
   - Use streaming for better UX with long responses
   - Handle connection interruptions gracefully
   - Implement client-side reconnection logic

4. **Error Handling**
   - Implement retry logic for transient errors
   - Fall back to non-streaming on stream errors
   - Log errors with correlation IDs for debugging