# Automation Readiness

Run the readiness report locally (no UI required):

```bash
python3 scripts/automation_readiness.py
```

The script loads `.env` from the project root when run locally, so keys in `.env` are visible to `os.getenv()`. In CI or production, set variables in the **runtime environment** (not only in a file); the script and app check `os.getenv()` and the DB, not file contents.

## Requirements for SELLABLE

| Integration | What is checked | Required |
|-------------|------------------|----------|
| **LLM** | `OPENAI_API_KEY` in runtime env | Set in env (or in `.env` and run script after load) |
| **Vector DB (KB)** | `PINECONE_API_KEY`; optional: `PINECONE_INDEX_NAME`, `PINECONE_EMBEDDING_MODEL` | Set in runtime env |
| **Gmail / Outlook** | Rows in `oauth_tokens` table (connected, active, not expired) | Env vars alone are not enough; user must connect accounts so tokens exist in DB |
| **Stripe** | `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in runtime env | Both set in runtime env |
| **SMS (workflows)** | `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` in runtime env | Both set in runtime env |

Service status is derived from `details.integration_health` in the JSON output. Each service (e.g. chatbot, mailbox_automation, billing) requires its listed integrations to be `"connected"` for SELLABLE.

**Chatbot and KB↔vector sync:** KB update/delete now sync to the vector index (see `docs/CRUD_RAG_ARCHITECTURE.md`). The previous “ghost context” caveat is closed: if you update or delete knowledge base content, the chatbot stops using the old info. With `vector_search` and LLM/vector keys configured, Chatbot can move to SELLABLE when revenue-flow tests are stable, guardrails are in place, and integration health is green—without a ghost-context caveat.

What it does:
- Runs the revenue-flow test suite 3x to detect flakiness
- Scans for forbidden patterns:
  - Direct OpenAI calls outside `core/ai`
  - `print()` in production paths
  - Hardcoded localhost backend URLs in `frontend/`
- Checks integration health (OAuth tokens + env config)
- Outputs JSON with SELLABLE / BETA / NOT READY

Exit codes:
- `0`: all services SELLABLE
- `1`: at least one service BETA
- `2`: at least one service NOT READY

Optional:
- `--runs N` to change stability test repetitions

Example:

```json
{
  "chatbot": "SELLABLE",
  "crm_leads": "SELLABLE",
  "mailbox_automation": "BETA",
  "workflows": "BETA",
  "billing": "SELLABLE",
  "security": "SELLABLE",
  "notes": [
    "Revenue-flow tests stable (pass 3/3)"
  ],
  "details": {
    "tests": {
      "runs": 3,
      "results": [true, true, true],
      "stable": true,
      "flaky": false
    },
    "static_checks": {
      "openai_violations": [],
      "print_violations": [],
      "frontend_violations": []
    },
    "integration_health": {
      "gmail": "missing",
      "llm_provider": "connected",
      "outlook": "missing",
      "sms_provider": "missing",
      "stripe": "connected",
      "vector_db": "missing"
    },
    "observability": {
      "billing": true,
      "chatbot": true,
      "crm_leads": true,
      "mailbox_automation": true,
      "security": true,
      "workflows": true
    }
  }
}
```
