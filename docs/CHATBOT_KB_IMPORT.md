# Chatbot knowledge base import

Use these endpoints to ingest landing and FAQ content into the public chatbot.

**Auth:** Use either a **logged-in session** (JWT/session cookie from the dashboard) or an **X-API-Key** header. Optional **X-Tenant-ID** if you use tenants.

---

## Single document: POST /api/chatbot/knowledge/import

**Headers:** `X-API-Key: <your-api-key>`, `Content-Type: application/json`

**Body (one of):**

- **Content only:** `{ "title": "Pricing", "content": "Starter $39/mo...", "category": "pricing", "document_type": "article", "tags": ["pricing"], "keywords": ["plan", "trial"] }`
- **FAQ style:** `{ "question": "What is Fikiri?", "answer": "Fikiri Solutions is...", "title": "What is Fikiri?", "category": "general" }`

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| title | No | Short title (default: "Imported Knowledge" or question) |
| content | Yes* | Full text (*or use question + answer) |
| question | Yes* | FAQ question (*with answer) |
| answer | Yes* | FAQ answer (*with question) |
| category | No | Category slug (default: "general") |
| document_type | No | "faq" \| "article" \| etc. (default: "faq") |
| tags | No | Array of tags |
| keywords | No | Array of keywords |

**Example (curl):**

```bash
curl -X POST https://your-api/api/chatbot/knowledge/import \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Home","content":"Fikiri automates your outreach. We connect email, CRM, and calendar.","category":"landing"}'
```

---

## Bulk import: POST /api/chatbot/knowledge/import/bulk

**Headers:** `X-API-Key: <your-api-key>`, `Content-Type: application/json`

**Body:** `{ "documents": [ { ... }, { ... } ] }` — each item has the same shape as the single-import body (content or question+answer, plus optional title, category, document_type, tags, keywords).

**Response:** `{ "success": true, "imported": N, "total": M, "results": [ { "index": 0, "success": true, "document_id": "...", "vector_id": "..." }, ... ] }`

**Example (curl) – two docs:**

```bash
curl -X POST https://your-api/api/chatbot/knowledge/import/bulk \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"title":"Home","content":"Fikiri automates outreach. One place for email, CRM, scheduling.","category":"landing"},
      {"question":"How much does it cost?","answer":"Starter $39/mo, Growth $79/mo, Business $199/mo, Enterprise $399/mo. Free trial available.","category":"pricing"}
    ]
  }'
```

---

## Landing content ready to import

**docs/landing-content-for-kb.md** contains text extracted from the frontend landing pages (/, /pricing, /about, /contact, /services-landing, industry pages). You can:

1. Copy sections from that file into single-import requests, or  
2. Use the **ready-to-use JSON** and **script**:
   - **scripts/chatbot_kb_landing_documents.json** – `documents` array (9 items: Home, Pricing, About, Contact, Services, Landscaping, Restaurant, Medical, Legal).
   - **scripts/import_landing_to_chatbot_kb.py** – Calls the bulk endpoint. Set `CHATBOT_KB_API_KEY` or `API_KEY` in `.env`, optionally `API_BASE_URL` (default `http://localhost:5000`), then run:
     ```bash
     python scripts/import_landing_to_chatbot_kb.py
     ```
     Or pass a custom JSON path: `python scripts/import_landing_to_chatbot_kb.py path/to/documents.json`

No network crawl is needed; the content is derived from the React/TSX source.

---

## Widget coverage

The public chatbot widget is already on: RadiantLandingPage, LandingPage, PricingPage, ServicesLanding, AIAssistantLanding, About, Contact, TermsOfService, PrivacyPolicy, LandscapingLanding, RestaurantLanding, MedicalLanding.
