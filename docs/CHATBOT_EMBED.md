# Website Chatbot Embed (Public API)

This repo exposes a public chatbot endpoint intended for Shopify/Squarespace/Replit/custom websites.

## Public Endpoint (v1)
- `POST /api/public/chatbot/query`
- Header: `X-API-Key: fik_...`

Request body:
```json
{
  "query": "What are your business hours?",
  "conversation_id": "optional-id",
  "context": {
    "session_id": "optional-session",
    "user_id": "optional-user"
  },
  "lead": {
    "email": "optional@example.com",
    "phone": "+1-555-555-1212",
    "name": "Optional Name"
  }
}
```

Response (stable schema v1):
```json
{
  "success": true,
  "schema_version": "v1",
  "query": "What are your business hours?",
  "response": "We are open 9am-5pm.",
  "confidence": 0.9,
  "fallback_used": false,
  "sources": [],
  "conversation_id": "conv_123",
  "tenant_id": "tenant_abc",
  "plan": "starter",
  "llm_trace_id": "trace_123",
  "lead_id": 42
}
```

## Hosted Widget (Recommended)
Use the hosted widget script + stylesheet. Replace `YOUR_DOMAIN` and `YOUR_API_KEY`.

```html
<link rel="stylesheet" href="https://YOUR_DOMAIN/static/fikiri-chatbot.css" />
<script
  src="https://YOUR_DOMAIN/static/fikiri-chatbot.js"
  data-api-url="https://YOUR_DOMAIN/api/public/chatbot/query"
  data-api-key="YOUR_API_KEY"
  data-title="Ask Fikiri"
  data-theme="light"
  data-accent="#0f766e"
></script>
```

### Optional data-* attributes
- `data-title`: widget header text
- `data-theme`: `light` or `dark` (cosmetic)
- `data-accent`: hex color for button
- `data-css`: custom stylesheet URL (overrides default)

## Inline Embed (Minimal)
If you can’t host an external script, use this inline snippet.

```html
<div id="fikiri-chatbot"></div>
<script>
  (function () {
    const API_URL = "https://YOUR_DOMAIN/api/public/chatbot/query";
    const API_KEY = "YOUR_API_KEY";

    const root = document.getElementById("fikiri-chatbot");
    root.innerHTML = `
      <div style="border:1px solid #ddd;padding:12px;max-width:360px;font-family:Arial;">
        <div id="fikiri-chat-log" style="min-height:60px;margin-bottom:8px;"></div>
        <input id="fikiri-chat-input" placeholder="Ask a question..." style="width:100%;padding:8px;" />
      </div>
    `;

    const log = root.querySelector("#fikiri-chat-log");
    const input = root.querySelector("#fikiri-chat-input");

    async function sendMessage(text) {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY
        },
        body: JSON.stringify({ query: text })
      });
      const data = await res.json();
      log.innerHTML += `<div><strong>You:</strong> ${text}</div>`;
      log.innerHTML += `<div><strong>Bot:</strong> ${data.response || "No response"}</div>`;
    }

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && input.value.trim()) {
        sendMessage(input.value.trim());
        input.value = "";
      }
    });
  })();
</script>
```

## Notes
- The public endpoint supports API key auth and rate limiting.
- If billing is enabled, LLM usage is gated by plan.
- Provide `lead.email` or include an email in the message to auto-create a CRM lead.
