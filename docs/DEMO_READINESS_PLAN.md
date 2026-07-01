# Fikiri Solutions — Demo Readiness Plan (consulting-first, OpenAI-aware)

**Last updated:** 2026-06-30  
**Positioning:** Fikiri is **consulting-first** — workflow discovery → private/custom builds (ColorScalez, Symbolics Technology, SteerTown pending) → optional platform layer. The app demonstrates the operating model; it is not a fully finished generic SaaS.

**Rule:** Do not regress working systems to make unfinished features look ready. **Hide, gate, or label** unstable surfaces until verified.

---

## Three layers (what to say to clients)

| Layer | Status | Demo |
|-------|--------|------|
| **Consulting & workflow audit** | Core business | Lead with this |
| **Private client builds** | Real proof | Mention ColorScalez, Symbolics |
| **Fikiri internal platform** | Evolving | Demo **stable modules only** |

**Client framing:**  
> “Fikiri is consulting-first. We start by understanding the workflow, then build or configure the right system. Today I’ll show the stable parts that support that process.”

**Not:** “Some things are broken.”  
**Instead:** “Some features are intentionally not in today’s demo until verified in the right environment.”

---

## Frontend demo flags (Vercel `frontend/.env.local` or build env)

| Variable | Purpose |
|----------|---------|
| `VITE_DEMO_SAFE_MODE=true` | Hides unstable nav; gates `/ai`, Chatbot Builder, Analytics; Services shows preview banner |
| `VITE_DEMO_EMAIL_AI_ENABLED=true` | Enables Inbox **Analyze / Suggest reply** — only after health check + rehearsal |
| `VITE_SITE_CHAT_WIDGET_ENABLED=true` | Marketing site chat bubble |

**Set `VITE_DEMO_SAFE_MODE=true` on tomorrow’s production frontend build.**

---

## Feature policy

| Feature | Policy |
|---------|--------|
| **CRM** | Primary logged-in demo — always enabled |
| **Marketing site chatbot** | Safe if deterministic KB (`FIKIRI_SITE_BOT_LLM_POLISH` off) |
| **Email Analyze / Reply** | Only if `VITE_DEMO_EMAIL_AI_ENABLED=true` + health check + inbox rehearsal |
| **`/assistant`, `/ai`** | Hidden from nav in demo mode; route shows unavailable page |
| **Chatbot Builder** | Hidden from nav; optional internal use only |
| **Dashboard metrics** | Neutral empty/error — no mock numbers |
| **Services toggles** | Preview banner — not persisted settings |
| **Public embed chatbot** | Do not demo |

---

## Pre-demo checks

```bash
python3 scripts/demo_openai_health_check.py
```

Then, only if OpenAI passes: set `VITE_DEMO_EMAIL_AI_ENABLED=true` and rehearse `/inbox` Analyze + Suggest reply.

---

## Recommended demo order (10–15 min)

1. Consulting framing + workflow audit story  
2. **CRM** — pipeline, add lead, drag stage  
3. **Site chatbot** on `/pricing` (incognito)  
4. **Inbox** read/reply only — or AI if explicitly enabled  
5. Client builds proof (ColorScalez / Symbolics)  
6. Close: next step = workflow audit or inbox connect  

---

## Code touchpoints (demo safety only)

- `frontend/src/lib/demoSafety.ts` — flags  
- `frontend/src/navigation/dashboardNav.ts` — nav filtering  
- `frontend/src/components/DemoGatedFeature.tsx` — route gates  
- `frontend/src/pages/Dashboard.tsx` — no mock metrics/charts  
- `frontend/src/pages/EmailInbox.tsx` — email AI gate  
- `frontend/src/pages/AIAssistant.tsx` — no canned AI fallback  
- `core/ai_chat_api.py` — 503 when LLM unavailable  

**Left untouched:** CRM service, site chatbot orchestrator, OAuth, billing, DB schema.
