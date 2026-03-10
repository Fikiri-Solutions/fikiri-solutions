# Chatbot feedback API

Log user ratings for chatbot answers (question, answer, retrieved docs, rating).

## Table: `chatbot_feedback`

| Column             | Type    | Description                                      |
|--------------------|---------|--------------------------------------------------|
| id                 | PK      | Auto-increment                                   |
| user_id            | INTEGER | Set when user is authenticated (session)         |
| session_id         | TEXT    | Optional client session id                       |
| question           | TEXT    | User question                                    |
| answer             | TEXT    | Bot answer                                       |
| retrieved_doc_ids  | TEXT    | JSON array of document IDs used for retrieval   |
| rating             | TEXT    | One of: correct, somewhat_correct, somewhat_incorrect, incorrect |
| created_at         | TIMESTAMP | Default CURRENT_TIMESTAMP                      |
| metadata           | TEXT    | Optional JSON object                             |
| prompt_version     | TEXT    | Optional                                          |
| retriever_version  | TEXT    | Optional                                          |

## Endpoint: POST /api/chatbot/feedback

- **URL:** `POST /api/chatbot/feedback`
- **Auth:** Optional. If the user is logged in (session), `user_id` is stored.
- **Content-Type:** `application/json`

### Request body

| Field               | Required | Type   | Description |
|---------------------|----------|--------|-------------|
| question            | Yes      | string | User question |
| answer              | Yes      | string | Bot answer |
| retrieved_doc_ids   | Yes      | array  | List of doc IDs (e.g. `["id1", "id2"]`) |
| rating              | Yes      | string | One of: `correct`, `somewhat_correct`, `somewhat_incorrect`, `incorrect` |
| session_id          | No       | string | Client session id |
| metadata            | No       | object | Arbitrary JSON |
| prompt_version      | No       | string | |
| retriever_version   | No       | string | |

### Response

- **200:** `{ "success": true, "message": "Feedback recorded" }`
- **400:** Missing/invalid field (see `code`: `MISSING_QUESTION`, `MISSING_ANSWER`, `INVALID_RATING`, `INVALID_RETRIEVED_DOC_IDS`, `INVALID_METADATA`)
- **503:** Table not available

### Example (curl)

```bash
# Minimal (no auth)
curl -X POST http://localhost:5000/api/chatbot/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are your business hours?",
    "answer": "We are open Monday–Friday 9am–5pm EST.",
    "retrieved_doc_ids": ["doc-pricing-1", "doc-faq-3"],
    "rating": "correct"
  }'

# With optional fields
curl -X POST http://localhost:5000/api/chatbot/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Do you support Gmail?",
    "answer": "Yes, we integrate with Gmail.",
    "retrieved_doc_ids": ["doc-integration-1"],
    "rating": "somewhat_correct",
    "session_id": "sess-abc-123",
    "metadata": { "source": "widget", "conversation_id": "conv-xyz" },
    "prompt_version": "v1",
    "retriever_version": "v2"
  }'

# With auth (session cookie): same as above; user_id is filled from session
curl -X POST http://localhost:5000/api/chatbot/feedback \
  -H "Content-Type: application/json" \
  -b "session=YOUR_SESSION_COOKIE" \
  -d '{"question":"Q","answer":"A","retrieved_doc_ids":[],"rating":"incorrect"}'
```

### Invalid rating (400)

```bash
curl -X POST http://localhost:5000/api/chatbot/feedback \
  -H "Content-Type: application/json" \
  -d '{"question":"Q","answer":"A","retrieved_doc_ids":[],"rating":"bad"}'
# -> 400, code: INVALID_RATING
```

## Registration

The route is on `chatbot_bp` (registered in `app.py` as `chatbot`), so the full path is `/api/chatbot/feedback`. No extra wiring required.

## Tests

```bash
python -m pytest tests/test_chatbot_feedback.py -v
```
