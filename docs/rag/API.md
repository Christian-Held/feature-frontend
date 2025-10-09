# RAG API Documentation

## Base URL
All RAG endpoints are prefixed with `/v1/rag`

## Authentication
- **Website Management Endpoints**: Require Bearer token authentication (JWT access token)
- **Chat Endpoint**: Requires custom header `X-Embed-Token` with the website's embed token

---

## Website Management

### Create Website
`POST /v1/rag/websites`

**Auth**: Required (Bearer token)

**Request Body**:
```json
{
  "url": "https://example.com",
  "name": "Example Website",
  "brand_color": "#3B82F6",
  "logo_url": "https://example.com/logo.png",
  "welcome_message": "Hi! How can I help you today?",
  "position": "BOTTOM_RIGHT",
  "language": "en",
  "crawl_frequency": "MANUAL",
  "max_pages": 100
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "url": "https://example.com",
  "name": "Example Website",
  "status": "PENDING",
  "embed_token": "generated_token",
  "brand_color": "#3B82F6",
  ...
}
```

### List Websites
`GET /v1/rag/websites`

**Auth**: Required

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "url": "https://example.com",
    "status": "READY",
    "pages_indexed": 42,
    ...
  }
]
```

### Get Website
`GET /v1/rag/websites/{website_id}`

**Auth**: Required

**Response**: `200 OK` (same structure as Create)

### Update Website
`PUT /v1/rag/websites/{website_id}`

**Auth**: Required

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "brand_color": "#10B981",
  "welcome_message": "New message",
  "is_active": false
}
```

### Delete Website
`DELETE /v1/rag/websites/{website_id}`

**Auth**: Required

**Response**: `204 No Content`

### Trigger Crawl
`POST /v1/rag/websites/{website_id}/crawl`

**Auth**: Required

**Response**: `200 OK`
```json
{
  "task_id": "celery_task_id",
  "status": "pending",
  "message": "Crawl task started"
}
```

---

## Custom Q&A

### Create Q&A
`POST /v1/rag/websites/{website_id}/qas`

**Auth**: Required

**Request Body**:
```json
{
  "question": "What are your hours?",
  "answer": "We're open Mon-Fri 9am-5pm",
  "priority": 100,
  "category": "hours",
  "keywords": "opening,hours,time"
}
```

**Response**: `201 Created`

### List Q&As
`GET /v1/rag/websites/{website_id}/qas`

**Auth**: Required

**Response**: `200 OK` (array of Q&As, sorted by priority desc)

### Delete Q&A
`DELETE /v1/rag/websites/{website_id}/qas/{qa_id}`

**Auth**: Required

**Response**: `204 No Content`

---

## Chat (Public)

### Send Message
`POST /v1/rag/chat`

**Auth**: Custom header `X-Embed-Token: {website_embed_token}`

**Request Body**:
```json
{
  "question": "What are your hours?",
  "conversation_history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
  ],
  "visitor_id": "optional_visitor_id"
}
```

**Response**: `200 OK`
```json
{
  "answer": "We're open Monday through Friday, 9am to 5pm.",
  "sources": [
    {
      "page_url": "https://example.com/about",
      "score": 0.92,
      "chunk_index": 2
    }
  ],
  "type": "rag",
  "confidence": "high",
  "actions": {
    "action": "SHOW_MAP",
    "data": {"lat": 40.7128, "lng": -74.0060}
  },
  "suggested_questions": [
    "Where are you located?",
    "How can I contact you?",
    "What services do you offer?"
  ]
}
```

**Response Types**:
- `custom_qa`: Matched a predefined Q&A
- `rag`: Generated from vector search + LLM
- `no_context`: No relevant information found

**Confidence Levels**:
- `high`: avg similarity score > 0.8
- `medium`: avg similarity score > 0.6
- `low`: avg similarity score > 0.5
- `none`: no results above threshold

**Actions** (optional):
- `SHOW_MAP`: Display map with coordinates
- `OPEN_HOURS`: Highlight hours section
- `CONTACT_INFO`: Show contact details
- `HIGHLIGHT`: Highlight specific content

---

## Analytics

### Get Usage Stats
`GET /v1/rag/websites/{website_id}/analytics`

**Auth**: Required

**Response**: `200 OK`
```json
[
  {
    "date": "2025-10-09",
    "conversations_count": 45,
    "messages_count": 123,
    "tokens_used": 15000,
    "cost_usd": 0.0225,
    "avg_satisfaction_rating": 4.5,
    "total_ratings": 12
  }
]
```

Returns last 30 days of stats.

---

## Error Responses

All endpoints return standard error format:

```json
{
  "detail": "Error message"
}
```

**Common Status Codes**:
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing/invalid auth
- `403 Forbidden`: No permission
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., crawl already running)
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Chat endpoint should be rate-limited per embed token to prevent abuse.

Recommended limits:
- 100 requests/minute per token
- 1000 requests/hour per token

---

## CORS

The chat endpoint must allow cross-origin requests for embedded widgets:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: X-Embed-Token, Content-Type
```
