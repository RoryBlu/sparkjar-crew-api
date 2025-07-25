# Chat with Memory v1 - Integration Guide

## Quick Start

### JavaScript/TypeScript

```typescript
// Install dependencies
// npm install axios eventsource

import axios from 'axios';
import { EventSource } from 'eventsource';

class ChatClient {
  private baseUrl: string;
  private token: string;
  private sessionId?: string;

  constructor(baseUrl: string, token: string) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  // Create a chat completion
  async sendMessage(message: string, mode: 'tutor' | 'agent' = 'agent') {
    const response = await axios.post(
      `${this.baseUrl}/v1/chat/completions`,
      {
        client_user_id: 'your-user-id',
        actor_type: 'synth',
        actor_id: 'your-actor-id',
        message: message,
        mode: mode,
        session_id: this.sessionId
      },
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    // Store session ID for continuity
    this.sessionId = response.data.session_id;
    
    return response.data;
  }

  // Stream a chat completion
  streamMessage(message: string, onChunk: (chunk: string) => void) {
    const eventSource = new EventSource(
      `${this.baseUrl}/v1/chat/completions/stream`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify({
          client_user_id: 'your-user-id',
          actor_type: 'synth',
          actor_id: 'your-actor-id',
          message: message,
          session_id: this.sessionId
        })
      }
    );

    eventSource.addEventListener('chunk', (event) => {
      const data = JSON.parse(event.data);
      onChunk(data.chunk);
    });

    eventSource.addEventListener('complete', (event) => {
      const data = JSON.parse(event.data);
      this.sessionId = data.session_id;
      eventSource.close();
    });

    eventSource.addEventListener('error', (event) => {
      console.error('Stream error:', event);
      eventSource.close();
    });

    return eventSource;
  }
}

// Usage
const client = new ChatClient('https://api.sparkjar.com', 'your-jwt-token');

// Simple message
const response = await client.sendMessage('How do I create an index?');
console.log(response.response);

// Streaming
client.streamMessage('Explain database optimization', (chunk) => {
  process.stdout.write(chunk);
});
```

### Python

```python
# Install dependencies
# pip install httpx httpx-sse

import httpx
from httpx_sse import connect_sse
import json

class ChatClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.session_id = None
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}
        )
    
    async def send_message(self, message: str, mode: str = "agent"):
        """Send a chat message and get response."""
        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "client_user_id": "your-user-id",
                "actor_type": "synth",
                "actor_id": "your-actor-id",
                "message": message,
                "mode": mode,
                "session_id": self.session_id
            }
        )
        
        data = response.json()
        self.session_id = data["session_id"]
        
        return data
    
    async def stream_message(self, message: str):
        """Stream a chat response."""
        async with connect_sse(
            self.client,
            "POST",
            f"{self.base_url}/v1/chat/completions/stream",
            json={
                "client_user_id": "your-user-id",
                "actor_type": "synth",
                "actor_id": "your-actor-id",
                "message": message,
                "session_id": self.session_id
            }
        ) as event_source:
            async for sse in event_source.aiter_sse():
                if sse.event == "chunk":
                    data = json.loads(sse.data)
                    yield data["chunk"]
                elif sse.event == "complete":
                    data = json.loads(sse.data)
                    self.session_id = data["session_id"]
    
    async def get_learning_progress(self):
        """Get learning progress for tutor mode."""
        if not self.session_id:
            return None
            
        response = await self.client.get(
            f"{self.base_url}/v1/chat/sessions/{self.session_id}/progress"
        )
        
        return response.json()

# Usage
import asyncio

async def main():
    client = ChatClient("https://api.sparkjar.com", "your-jwt-token")
    
    # Simple message
    response = await client.send_message("How do I optimize queries?", mode="tutor")
    print(response["response"])
    
    # Check learning progress
    progress = await client.get_learning_progress()
    print(f"Understanding level: {progress['understanding_level']}")
    
    # Streaming
    async for chunk in client.stream_message("Explain indexes"):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

## React Component Example

```jsx
import React, { useState, useEffect } from 'react';

const ChatWithMemory = ({ token }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('agent');
  const [sessionId, setSessionId] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [learningProgress, setLearningProgress] = useState(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);

    const assistantMessage = { role: 'assistant', content: '' };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await fetch('/api/v1/chat/completions/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_user_id: 'current-user-id',
          actor_type: 'synth',
          actor_id: 'synth-id',
          message: input,
          mode: mode,
          session_id: sessionId
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.chunk) {
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].content += data.chunk;
                  return newMessages;
                });
              }
              
              if (data.session_id) {
                setSessionId(data.session_id);
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsStreaming(false);
      
      // Update learning progress if in tutor mode
      if (mode === 'tutor' && sessionId) {
        fetchLearningProgress();
      }
    }
  };

  const fetchLearningProgress = async () => {
    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/progress`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setLearningProgress(data);
    } catch (error) {
      console.error('Progress fetch error:', error);
    }
  };

  return (
    <div className="chat-container">
      <div className="mode-selector">
        <button 
          className={mode === 'agent' ? 'active' : ''}
          onClick={() => setMode('agent')}
        >
          Agent Mode
        </button>
        <button 
          className={mode === 'tutor' ? 'active' : ''}
          onClick={() => setMode('tutor')}
        >
          Tutor Mode
        </button>
      </div>

      {mode === 'tutor' && learningProgress && (
        <div className="learning-progress">
          <h3>Learning Progress</h3>
          <p>Topic: {learningProgress.learning_topic}</p>
          <p>Understanding: {learningProgress.understanding_level}/5</p>
          <p>Topics Covered: {learningProgress.learning_path?.length || 0}</p>
        </div>
      )}

      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          disabled={isStreaming}
          placeholder="Type your message..."
        />
        <button onClick={sendMessage} disabled={isStreaming}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatWithMemory;
```

## Mobile Integration (React Native)

```jsx
import React, { useState } from 'react';
import { View, TextInput, FlatList, Text, TouchableOpacity } from 'react-native';

const ChatScreen = ({ token }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { id: Date.now(), role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const response = await fetch('https://api.sparkjar.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_user_id: 'user-id',
          actor_type: 'synth',
          actor_id: 'actor-id',
          message: input,
          mode: 'agent',
          session_id: sessionId
        })
      });

      const data = await response.json();
      setSessionId(data.session_id);

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
    }
  };

  return (
    <View style={{ flex: 1 }}>
      <FlatList
        data={messages}
        keyExtractor={item => item.id.toString()}
        renderItem={({ item }) => (
          <View style={{
            padding: 10,
            backgroundColor: item.role === 'user' ? '#e3f2fd' : '#f5f5f5',
            margin: 5,
            borderRadius: 10
          }}>
            <Text>{item.content}</Text>
          </View>
        )}
      />
      
      <View style={{ flexDirection: 'row', padding: 10 }}>
        <TextInput
          style={{
            flex: 1,
            borderWidth: 1,
            borderColor: '#ddd',
            borderRadius: 20,
            paddingHorizontal: 15,
            paddingVertical: 10
          }}
          value={input}
          onChangeText={setInput}
          placeholder="Type a message..."
        />
        <TouchableOpacity
          onPress={sendMessage}
          style={{
            marginLeft: 10,
            backgroundColor: '#2196F3',
            borderRadius: 20,
            paddingHorizontal: 20,
            paddingVertical: 10
          }}
        >
          <Text style={{ color: 'white' }}>Send</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};
```

## Best Practices

### 1. Session Management

Always maintain session continuity:

```javascript
// Store session ID after first message
let sessionId = null;

async function chat(message) {
  const response = await api.post('/v1/chat/completions', {
    message,
    session_id: sessionId  // Include in subsequent requests
  });
  
  sessionId = response.data.session_id;
  return response.data;
}
```

### 2. Error Handling

Implement proper error handling with retries:

```python
import asyncio
from typing import Optional

async def send_with_retry(
    client: ChatClient,
    message: str,
    max_retries: int = 3
) -> Optional[dict]:
    for attempt in range(max_retries):
        try:
            return await client.send_message(message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                retry_after = int(e.response.headers.get('Retry-After', 60))
                await asyncio.sleep(retry_after)
            elif attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    return None
```

### 3. Mode Switching

Switch modes based on user intent:

```typescript
async function handleUserInput(message: string) {
  // Detect learning intent
  const learningKeywords = ['teach', 'explain', 'how does', 'what is'];
  const isLearning = learningKeywords.some(kw => 
    message.toLowerCase().includes(kw)
  );
  
  // Switch to appropriate mode
  if (isLearning && currentMode !== 'tutor') {
    await switchMode('tutor');
  } else if (!isLearning && currentMode !== 'agent') {
    await switchMode('agent');
  }
  
  // Send message
  return await sendMessage(message);
}
```

### 4. Streaming Best Practices

Handle streaming properly with buffering:

```javascript
class StreamBuffer {
  constructor() {
    this.buffer = '';
    this.onFlush = null;
  }
  
  add(chunk) {
    this.buffer += chunk;
    
    // Flush on sentence boundaries
    const sentences = this.buffer.split(/(?<=[.!?])\s+/);
    if (sentences.length > 1) {
      const complete = sentences.slice(0, -1).join(' ');
      this.buffer = sentences[sentences.length - 1];
      
      if (this.onFlush) {
        this.onFlush(complete);
      }
    }
  }
  
  flush() {
    if (this.buffer && this.onFlush) {
      this.onFlush(this.buffer);
      this.buffer = '';
    }
  }
}
```

### 5. Memory Configuration

Configure memory realms based on use case:

```python
# For general queries - search all realms
general_config = {
    "include_own": True,
    "include_class": True,
    "include_skills": True,
    "include_client": True
}

# For personal context only
personal_config = {
    "include_own": True,
    "include_class": False,
    "include_skills": False,
    "include_client": False
}

# For company policies
policy_config = {
    "include_own": False,
    "include_class": False,
    "include_skills": False,
    "include_client": True
}
```

## Migration from Existing Chat

If migrating from an existing chat system:

1. **Map User IDs**: Ensure your user IDs are UUIDs
2. **Convert Messages**: Transform to new request format
3. **Handle Sessions**: Implement session management
4. **Update UI**: Add mode switching and progress tracking

Example migration function:

```javascript
function migrateToV1(oldRequest) {
  return {
    client_user_id: oldRequest.userId || generateUUID(),
    actor_type: 'synth',
    actor_id: oldRequest.agentId || generateUUID(),
    message: oldRequest.text,
    mode: 'agent',  // Default to agent mode
    include_realms: {
      include_own: true,
      include_class: true,
      include_skills: true,
      include_client: false  // Unless user has permission
    }
  };
}
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Verify JWT token is valid
   - Check token has `sparkjar_internal` scope

2. **429 Too Many Requests**
   - Implement rate limit handling
   - Use exponential backoff

3. **Session Expired**
   - Sessions expire after 24 hours
   - Create new session on 404 errors

4. **Streaming Connection Drops**
   - Implement reconnection logic
   - Buffer partial responses

5. **Memory Timeouts**
   - Reduce `context_depth` parameter
   - Limit memory realms searched