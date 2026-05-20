# Staging smoke test — Inbox Command Center (pre–customer use)

Run once on **staging** (`fikiri-backend-staging` + staging Vercel) with a **dedicated test Gmail account** before promoting inbox/triage to customers.

**Positioning (say this, not more):** *AI-assisted inbox organization and lead capture* — not “zero hallucinations,” not “fully autonomous inbox.”

---

## Prerequisites

| Item | Check |
|------|--------|
| Staging API up | `GET {STAGING_URL}/api/health/live` → 200 |
| Staging frontend | Login works; `/inbox` and `/inbox/command-center` load |
| Test user | Gmail connected on staging; CRM/inbox services enabled for user |
| Logs | Tail Render staging logs or local `python app.py` with `FLASK_ENV=development` |

---

## Smoke steps (pass / fail)

| # | Step | Pass criteria | Logs / evidence |
|---|------|---------------|-----------------|
| 1 | **Connect Gmail** | OAuth completes; integrations page shows connected | Gmail OAuth callback success |
| 2 | **Sync inbox** | Job completes (`completed` or `partial`); Live mail shows new messages | `event=gmail_sync_started` → `event=gmail_sync_completed` |
| 3 | **Classify** | Command Center → “Classify synced” or auto-triage after sync; counts/tabs update | `email_triage.classify_unclassified_completed` (usage) |
| 4 | **Re-classify** | Select 1+ rows → Re-classify; category/reason updates | `email_triage.reclassified` |
| 5 | **Archive** | Bulk **Archive** on 1 message; leaves active tab; **does not reappear** in same tab after refresh | `event=inbox.workflow.bulk_action.completed` action=archive; workflow `archived` |
| 6 | **Dismiss** | Bulk **Dismiss** on 1 message; hidden from Command Center; **does not resurface** after refresh | Same bulk log with action=dismiss; workflow `dismissed` |
| 7 | **Create lead** | Bulk **Create leads** on a `business_lead` (or high score); lead in CRM | CRM lead row; workflow `converted_to_lead` |
| 8 | **Chatbot query** | Builder or public widget preview returns an answer with sources | `event=chatbot.retrieval.completed` |
| 9 | **Chatbot lead capture** | Widget/form capture creates/updates CRM lead | `event=chatbot.lead_capture.completed` |

**Archive vs dismiss:** Archive also removes INBOX in Gmail. Dismiss is workflow-only (stays in Gmail, hidden from Command Center).

---

## Verify “does not resurface”

After archive or dismiss:

1. Refresh Command Center tab (same category as before).
2. Message must **not** appear in the default active queue.
3. Optional: `GET /api/email/triage?category=<same>&include_handled=false` — id absent.

Handled statuses: `archived`, `dismissed`, `done`, `spam`, `converted_to_lead`, `replied`.

---

## Log grep cheat sheet (staging)

```bash
# Gmail sync
grep -E 'gmail_sync_started|gmail_sync_completed|Completed Gmail sync job'

# Command Center / workflow
grep -E 'inbox\.workflow\.bulk_action|bulk workflow persist|email_triage\.(classified|reclassified|bulk_action)'

# Chatbot
grep -E 'chatbot\.retrieval\.completed|chatbot\.lead_capture\.(completed|failed|skipped)'

# Usage blocked (plan/budget/tier)
grep -E 'chatbot\.usage\.blocked|usage_blocked'
```

Structured `event=` fields are in JSON `extra` on the same log lines.

---

## Usage / billing block test (optional)

1. Use a user on a capped plan or exhaust chatbot tier in staging.
2. Send chatbot preview/query until blocked.
3. Expect friendly API error (402/403), not 500.
4. Log: `event=chatbot.usage.blocked` with `error_code`.

---

## Sign-off

| Role | Date | Result |
|------|------|--------|
| Engineering | | ☐ Pass ☐ Fail |
| Notes | | |

If any step fails, **do not** tell customers the inbox is “fully automated.” Fix or document known limits first.
