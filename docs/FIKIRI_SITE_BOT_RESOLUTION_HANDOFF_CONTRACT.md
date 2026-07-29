# Fikiri Site Bot — Resolution Window & Software Handoff Contract

**Status:** Planning only (no implementation in this document)  
**Non-regression rule:** Do not change transcript design, turn cap value, persistence path, mode routing, retrieval, or grounding while this contract is refined.  
**Related:** [FIKIRI_SITE_BOT_ROUTING_TRACE.md](./FIKIRI_SITE_BOT_ROUTING_TRACE.md), [FIKIRI_SITE_BOT_PHASE_5B_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_5B_HANDOFF.md), [FIKIRI_SITE_BOT_ENGINEERING_RULES.md](./FIKIRI_SITE_BOT_ENGINEERING_RULES.md)

---

## Governing principle

> The 12-turn cap protects infrastructure. Conversation design protects the customer.  
> Before the cap is reached, the bot must either **resolve** the concern or create a **complete, actionable human handoff**.

The unacceptable outcome is:

```text
Turn limit reached → generic goodbye → concern lost
```

---

## Two chatbots (do not mix)

| | Landing-page bot | In-app client bot |
|---|---|---|
| Audience | fikiriSolutions.com visitors | Paying tenants inside the app |
| Code | `company_chatbot/` | Tenant chatbot / `core/chatbot_*` |
| API | `/api/site/chat/*` | Product chatbot / SDK |
| Tables | `site_chat_sessions`, `site_chat_messages` | `chatbot_conversations`, `chatbot_messages` |
| Escalation target (current plan) | Fikiri Solutions **software** team | Tenant support / product flows |

This contract applies **only** to the landing-page bot.

---

## Session outcomes (required model)

Every website-chat session should end in one of:

| Outcome | Meaning |
|---------|---------|
| **Resolved** | Grounded answer addressed the visitor’s question |
| **Guided** | Visitor directed to the correct service, form, `/intake`, or `/contact` |
| **Qualified handoff** | Enough contact + problem context for humans to continue |
| **Safe unresolved handoff** | Bot cannot answer confidently; gap documented; team notified |

---

## Turn budget (strategic use of the existing 12-turn window)

`MAX_TURN_CAP = 12` in `company_chatbot/guards.py` counts **user turns** via `session.turn_count` (incremented once per `handle_message()`). Cap fires when `turn_count >= 12` **before** mode handling.

| Turns | Intent |
|-------|--------|
| **1–4** | Understand and answer — capability map + retrieval; avoid unnecessary intake |
| **5–8** | Clarify or narrow — only high-value questions |
| **9–10** | Prepare handoff if still unresolved — explain software review; collect missing contact |
| **11–12** | Finalize — summarize, confirm contact, flag session, notify team, set visitor expectation |

Do **not** wait until turn 12 to start collecting handoff information.  
Target: when `turns_remaining <= 2` **and** concern unresolved → initiate handoff before hard cap.

---

## Storage & cost posture (locked for now)

Keep the current transcript architecture. It is review-oriented and lean.

| Decision | Status |
|----------|--------|
| Feature-flagged Postgres transcripts | Keep |
| Fail-open on transcript write | Keep |
| Separate `site_chat_*` tables | Keep |
| No routing_trace in DB yet | Keep |
| Store all bounded transcripts for 90 days | Keep (default) |
| Miss-only / sample mode | Later, only if measured volume justifies |

Conservative footprint (includes indexes / overhead): **~2–5 KB per turn**. At 200 sessions/day × 5 turns × 90 days ≈ **200–600 MB** — manageable vs Supabase’s **8 GB provisioned DB disk** (not object Storage).

### Highest-value operational gaps (plan only; implement later)

1. **Retention not scheduled** — `purge_expired_transcripts()` exists; no daily job calls it yet.  
2. **No stored-content bound** — rate limits and turn cap exist; oversized single messages are not truncated for persistence yet.  
3. **Index/write tuning** — leave alone until metrics show pressure.

**PR order when we implement (still additive):**

1. Schedule existing purge (daily, batched, fail-safe)  
2. Bound persisted content with explicit truncation metadata  
3. Measure table + index growth  
4. Optional selective sampling only if volume requires it  

Do **not** move chats to object storage, add compression infrastructure, or redesign tables now.

---

## Handoff information contract

Collect only what is necessary. Not every field is mandatory.

**Minimum useful handoff:**

- Contact method (email preferred)
- Clear concern / unanswered question
- Session / transcript identifier
- Handoff reason

**Full payload shape (planning):**

```json
{
  "name": null,
  "email": null,
  "phone": null,
  "business_name": null,
  "preferred_contact_method": "email",
  "concern_summary": "",
  "affected_area": "crm|email_automation|website_bot|billing|integration|other",
  "urgency": "normal|high",
  "attempted_resolution": "",
  "unanswered_question": "",
  "session_id": "site_…",
  "lead_tier": "casual|possible|warm|hot",
  "handoff_reason": "not_grounded|turn_cap_approaching|frustration|explicit_human|technical_defect|integration_failure|unsupported_capability",
  "responsible_team": "software"
}
```

---

## When to flag for software-team review

Flag when any of:

- Bot lacks grounded information for a technical/product question
- Visitor reports a technical defect or integration failure
- Unsupported / unclear functionality questions
- Repeated fallbacks
- Frustration after unsuccessful answers
- Explicit ask for developer / engineer / human
- Turn limit approaching with unresolved concern
- High-value implementation request needing technical discovery

**Not every** contact request needs software escalation. Sales, billing, and general inquiries should eventually have other owners. Current default for unresolved **technical/product** questions: software team.

---

## Slack notification contract

**Responsible party (current):** Fikiri Solutions software team.

**Must be concise and actionable.** Include visitor identity (when known), area, urgency, lead tier, concern, what the bot already tried, the remaining human question, and `session_id`.

**Must not include:**

- Full raw transcript by default
- API keys, cookies, auth headers
- Stack traces
- Large routing traces
- Secrets or provider responses

Staff use `session_id` + admin transcript API for full review.

### Reliability rule (non-negotiable)

```text
1. Persist handoff + transcript
2. Return visitor-facing confirmation
3. Attempt Slack notification
4. Record success/failure
5. Retry later via worker / bounded retry (future)
```

Slack failure **must never** block the visitor response or erase the handoff.  
Deduplicate: one Slack alert per `(session_id, handoff_reason)` unless a material new concern appears.

Feature flag (future): notification delivery independently disableable from chat.

---

## Architecture preservation (implementation constraint)

Build on what already exists — do **not** add a second orchestrator, transcript system, lead DB, or routing engine.

```text
Existing handle_message()
  → guards / modes / retrieval / grounding
  → lead assessment + handoff metadata
  → transcript persistence (flagged)
  → small escalation decision (future)
  → Slack adapter (future, reusable, not inline in every handler)
```

Conceptual call sites only (not implemented yet):

```text
handoff = build_handoff_summary(...)
notify_responsible_team(handoff)  # after response path; fail-open
```

---

## Capability map: what already exists vs missing

### Already built

| Capability | Location | Notes |
|------------|----------|-------|
| Turn cap (12 user turns) | `guards.py` `MAX_TURN_CAP` | Hard stop → `suggest_handoff` + generic handoff message |
| Frustration / stuck / repeat guards | `guards.py` | Escalates to handoff messaging |
| Mode + capability + retrieval | `modes.py`, `capabilities.py`, `retrieval.py`, `grounding.py` | Deterministic hybrid stack |
| Lead assessment + synopsis | `lead_scoring.py` | Tiers + `recommended_handoff` (`/intake` or `/contact`) |
| Handoff metadata | `schemas.HandoffMetadata` | Widget primary; secondary path |
| Intake slots (email, industry, pain, timeline) | `intake.py` | Buying modes only |
| Transcript persistence | `transcript_store.py` | Flagged; fail-open; hashed IP/UA |
| Staff transcript + miss APIs | `routes/admin_site_chat_api.py` | Owner/admin JWT |
| Slack webhook plumbing (product ops) | `core/monitoring.py`, `services/automation_engine.py` | `SLACK_WEBHOOK_URL` — **not** wired to site bot |
| Inline routing trace (runtime) | `routing_trace.py` | Flagged; not persisted |

### Missing (smallest connection for later slices)

| Gap | Why it matters |
|-----|----------------|
| Soft “turns remaining ≤ 2 + unresolved” handoff | Cap currently fires as hard stop with generic message; no structured capture |
| Structured software handoff summary object | Lead synopsis exists; software-specific payload does not |
| Site-bot → Slack adapter | Monitoring/automation Slack exists; site bot does not call it |
| Deduped notification record | Prevent duplicate Slack spam |
| Scheduled transcript purge | Retention function exists; not operational |
| Persisted content length bound | Abuse / disk safety |
| Explicit outcome enum on session | Resolved / Guided / Qualified / Safe unresolved |

---

## Non-regression requirements (any future implementation)

Any implementation PR must prove:

1. Successful FAQ answers unchanged  
2. 12-turn guard still prevents unbounded sessions  
3. Resolved conversations do not create unnecessary Slack alerts  
4. Unresolved conversations escalate **before** hard termination when possible  
5. Slack failure does not break chat  
6. Transcript failure does not break chat  
7. Duplicate requests do not generate repeated Slack alerts  
8. Contact details bind to the correct `session_id`  
9. No cross-visitor transcript/handoff linkage  
10. No secrets or internal errors in Slack  
11. Notification feature flag can disable Slack independently of chat  

---

## Development sequence (no code until approved)

1. **This document** — resolution + handoff + storage contract  
2. Map existing handoff / lead / transcript / Slack (done above)  
3. Identify smallest missing connection (soft pre-cap handoff + Slack adapter)  
4. Finalize Slack payload + deduplication rule  
5. Finalize turn-budget escalation behavior (confirm turn counting — already: user turns)  
6. Focused tests first  
7. Implement behind **disabled** feature flags  
8. Enable in staging only  

### Fixed implementation order (do not reorder; do not start until explicitly approved)

| Slice | Scope | Must not touch |
|-------|-------|----------------|
| **A** | Schedule existing `purge_expired_transcripts()` (daily, fail-safe) — **implemented**: `scripts/purge_site_chat_transcripts.py` + `render.yaml` cron `fikiri-site-chat-transcript-purge` | Routing, cap value, table redesign, chatbot behavior |
| **B** | Bound persisted content only (+ truncation metadata) | User-facing answers, routing |
| **C** | Flagged pre-cap unresolved handoff | Cap value (`12`), detectors, unflagged enable |
| **D** | Fail-open Slack notification + dedupe (flagged) | Orchestrator rewrite; Slack must never block chat |
| **E** | Session outcome labeling | Product chatbot tables; existing persistence path unless additive |

**First future code change = Slice A only.** Immediate ops value; effectively zero chatbot behavior risk.

### Non-regression rules (locked)

1. The 12-turn cap stays at **12 user turns**.
2. The bot must remain as helpful as possible within that resolution window.
3. Resolved conversations must not create unnecessary handoffs.
4. Unresolved technical/product concerns should be summarized and escalated before the hard stop when possible (Slice C+).
5. Contact information must remain attached to the correct `session_id`.
6. Slack failure must never break the visitor response or lose the handoff (Slice D).
7. Slack receives a concise summary and session ID — not the full transcript or internal trace.
8. Current transcript tables and persistence path remain unchanged until a specific approved slice requires an **additive** change.

---

## Monitoring queries (ops, when volume exists)

```sql
SELECT
    COUNT(*) AS message_rows,
    COUNT(DISTINCT session_id) AS sessions,
    pg_size_pretty(pg_total_relation_size('site_chat_messages')) AS messages_total_size,
    pg_size_pretty(pg_total_relation_size('site_chat_sessions')) AS sessions_total_size,
    MIN(created_at) AS oldest_message,
    MAX(created_at) AS newest_message
FROM site_chat_messages;

SELECT
    pg_size_pretty(pg_relation_size('site_chat_messages')) AS table_size,
    pg_size_pretty(pg_indexes_size('site_chat_messages')) AS index_size,
    pg_size_pretty(pg_total_relation_size('site_chat_messages')) AS total_size;
```

---

## Verdict

Keep the current transcript and routing architecture. Use the 12-turn window as a **resolution window**, not a cliff. Make retention operational and bound stored content before adding Slack. Wire Slack only as a fail-open adapter after structured handoff exists — behind a flag, with dedupe, and never as a second chatbot.
