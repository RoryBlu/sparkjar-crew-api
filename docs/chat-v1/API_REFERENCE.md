# Chat with Memory v1 - API Reference

## Overview

The Chat with Memory v1 API provides intelligent conversational capabilities with hierarchical memory access. It supports two distinct modes:

- **Agent Mode**: Passive task execution following procedures from memory
- **Tutor Mode**: Proactive educational guidance with learning path tracking

Base URL: `https://api.sparkjar.com/v1/chat`

## Authentication

All endpoints require JWT bearer token authentication with the `sparkjar_internal` scope.

```bash
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting

- **Per minute**: 20 requests
- **Per hour**: 200 requests

Rate limit headers are included in all responses:
```
X-RateLimit-Limit-Minute: 20
X-RateLimit-Remaining-Minute: 15
X-RateLimit-Limit-Hour: 200
X-RateLimit-Remaining-Hour: 185
```

## Endpoints

### Create Chat Completion

Create a chat completion with memory context.

```
POST /v1/chat/completions
```

#### Request Body

```json
{
  "client_user_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor_type": "synth",
  "actor_id": "660e8400-e29b-41d4-a716-446655440000",
  "message": "How do I optimize database queries?",
  "mode": "tutor",
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "include_realms": {
    "include_own": true,
    "include_class": true,
    "include_skills": true,
    "include_client": true
  },
  "context_depth": 2,
  "learning_preferences": {
    "style": "practical",
    "pace": "moderate"
  }
}
```

#### Response

```json
{
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "message_id": "880e8400-e29b-41d4-a716-446655440000",
  "message": "How do I optimize database queries?",
  "response": "To optimize database queries, let's start with understanding indexes...",
  "mode_used": "tutor",
  "memory_context_used": [
    "query_optimization_guide",
    "index_best_practices"
  ],
  "memory_realms_accessed": {
    "synth": 1,
    "synth_class": 2,
    "client": 1
  },
  "learning_context": {
    "understanding_level": 3,
    "learning_objective": "Learn to optimize database queries",
    "follow_up_questions": [
      "Would you like to see examples of index usage?",
      "Shall we explore query execution plans?"
    ],
    "suggested_topics": [
      "Index Types",
      "Query Execution Plans"
    ]
  },
  "learning_path": [
    "SQL Basics",
    "Query Optimization"
  ],
  "relationships_traversed": 5,
  "memory_query_time_ms": 150
}
```

### Create Streaming Chat Completion

Create a streaming chat completion using Server-Sent Events (SSE).

```
POST /v1/chat/completions/stream
```

#### Request Body

Same as non-streaming endpoint.

#### Response

Returns Server-Sent Events stream:

```
event: metadata
data: {"session_id":"...","mode":"tutor","memory_context":{"memories_used":3}}

event: typing
data: {"status":"started"}

event: search_status
data: {"phase":"Searching memories","status":"started"}

event: chunk
data: {"chunk":"To optimize database","index":0,"total":10}

event: chunk
data: {"chunk":" queries, you should","index":1,"total":10}

event: complete
data: {"session_id":"...","follow_up_questions":["..."],"suggested_topics":["..."]}

event: typing
data: {"status":"stopped"}
```

### Get Session

Retrieve session details.

```
GET /v1/chat/sessions/{session_id}
```

#### Response

```json
{
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "client_user_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor_type": "synth",
  "actor_id": "660e8400-e29b-41d4-a716-446655440000",
  "mode": "tutor",
  "created_at": "2025-01-20T10:00:00Z",
  "last_activity": "2025-01-20T10:30:00Z",
  "expires_at": "2025-01-21T10:00:00Z",
  "message_count": 5,
  "learning_topic": "Database Optimization",
  "learning_path": ["SQL Basics", "Indexes", "Query Plans"],
  "understanding_level": 4
}
```

### Delete Session

Delete a chat session.

```
DELETE /v1/chat/sessions/{session_id}
```

#### Response

```json
{
  "deleted": true,
  "session_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

### Switch Mode

Switch between tutor and agent modes.

```
POST /v1/chat/sessions/{session_id}/mode
```

#### Request Body

```json
{
  "mode": "agent"
}
```

#### Response

```json
{
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "previous_mode": "tutor",
  "new_mode": "agent",
  "message": "Switched to agent mode"
}
```

### Get Learning Progress

Get learning progress for tutor mode sessions.

```
GET /v1/chat/sessions/{session_id}/progress
```

#### Response

```json
{
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "learning_topic": "Database Optimization",
  "understanding_level": 4,
  "learning_path": ["SQL Basics", "Indexes", "Query Plans"],
  "message_count": 10,
  "session_duration_minutes": 30
}
```

### Get Learning Path

Get detailed learning path visualization.

```
GET /v1/chat/sessions/{session_id}/learning-path
```

#### Response

```json
{
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "current_topic": "Query Optimization",
  "understanding_level": 4,
  "path": [
    "SQL Basics: Understanding fundamentals",
    "Indexes: Learn about database indexes",
    "Query Plans: Analyze execution plans"
  ],
  "topics_covered": 3,
  "session_duration_minutes": 30,
  "progress_summary": {
    "status": "in_progress",
    "topics_explored": 3,
    "depth": "moderate"
  }
}
```

### Export Learning Report

Export comprehensive learning report.

```
GET /v1/chat/sessions/{session_id}/learning-report
```

#### Response

```json
{
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "report_generated": "2025-01-20T11:00:00Z",
  "session_info": {
    "created": "2025-01-20T10:00:00Z",
    "last_activity": "2025-01-20T10:30:00Z",
    "duration_minutes": 30,
    "message_count": 10
  },
  "learning_progress": {
    "starting_topic": "SQL Basics",
    "current_topic": "Query Optimization",
    "topics_covered": ["SQL Basics", "Indexes", "Query Plans"],
    "understanding_progression": [3, 3, 4, 4],
    "final_understanding_level": 4
  },
  "learning_path_visualization": "Learning Journey:\n  1. SQL Basics\n     ↓\n  2. Indexes\n     ↓\n  3. Query Plans",
  "recommendations": {
    "strengths": ["Consistent learning engagement", "Progressing to advanced topics"],
    "areas_for_improvement": ["Explore more practice examples"],
    "next_steps": ["Apply knowledge in practical projects", "Explore advanced techniques"]
  }
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Error Codes

- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

## Models

### ChatRequestV1

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| client_user_id | UUID | Yes | User making the request |
| actor_type | string | Yes | Type of actor ("synth") |
| actor_id | UUID | Yes | Actor identifier |
| message | string | Yes | User's message |
| mode | string | No | Chat mode ("tutor" or "agent") |
| session_id | UUID | No | Existing session ID |
| include_realms | object | No | Memory realms to search |
| context_depth | integer | No | Relationship traversal depth (1-3) |
| learning_preferences | object | No | Tutor mode preferences |

### Memory Realms

Control which memory hierarchies to search:

```json
{
  "include_own": true,      // Actor's own memories
  "include_class": true,    // Synth class memories
  "include_skills": true,   // Skill module memories
  "include_client": true    // Client-level policies
}
```

## Best Practices

1. **Session Management**
   - Reuse session_id for conversation continuity
   - Sessions expire after 24 hours
   - Delete sessions when conversation ends

2. **Mode Selection**
   - Use "tutor" mode for learning and exploration
   - Use "agent" mode for task execution
   - Switch modes based on user needs

3. **Memory Configuration**
   - Start with default realm configuration
   - Only disable realms if specifically needed
   - CLIENT realm requires special permissions

4. **Error Handling**
   - Implement exponential backoff for rate limits
   - Handle streaming errors gracefully
   - Log security events for audit

5. **Performance**
   - Use streaming for better UX
   - Cache session data client-side
   - Batch related requests when possible