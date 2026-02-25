# Public API Testing

How to run and interpret tests for the public API (API key manager, chatbot, AI analysis, vector persistence).

## Run with pytest (preferred)

From project root:

```bash
pytest tests/test_api_key_manager.py tests/test_public_chatbot_api.py tests/test_ai_analysis_api.py tests/test_vector_persistence.py -v
```

Or run the public API runner script:

```bash
python tests/run_public_api_tests.py
```

For the full backend suite (including public API tests), see [TESTING.md](TESTING.md).

## Coverage summary

| Component | Tests | Notes |
|-----------|-------|--------|
| API Key Manager | ~10 | Generation, validation, tenant isolation, rate limits, revocation |
| Public Chatbot API | ~8 | Auth, invalid key rejection, rate limit (429), CORS |
| AI Analysis API | ~6 | Schema validation, contact/lead/business analysis, email validation |
| Vector Persistence | ~3 | FAQ/document indexing, graceful failure |

**Total: ~27 unit tests.** Integration with live backend is manual; run backend then use `X-API-Key` with curl or the dashboard.

## Manual smoke test

1. Start backend: `python app.py`
2. Generate a key (e.g. via dashboard or `core.api_key_manager`).
3. `curl -X POST http://localhost:5000/api/public/chatbot/query -H "Content-Type: application/json" -H "X-API-Key: fik_YOUR_KEY" -d '{"query": "Hello"}'`

## References

- [PUBLIC_API_DOCUMENTATION.md](PUBLIC_API_DOCUMENTATION.md) — API reference
- [PUBLIC_API_IMPLEMENTATION.md](PUBLIC_API_IMPLEMENTATION.md) — Implementation summary
- [TESTING.md](TESTING.md) — Full test suite and sellability gate
