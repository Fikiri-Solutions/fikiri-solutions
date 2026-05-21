# Inbox UX — Simple-first philosophy

North star: **Business Gmail that quietly sorts your mail—you stay in control.**

## Mental model

| Surface | User phrase | Purpose |
|---------|-------------|---------|
| **Read** | “My inbox” | Real Gmail: read, search, reply |
| **Organize** | “My sorted piles” | Synced mail in business queues; bulk actions |
| **Update & sort** | “Refresh my piles” | Pull mail + run triage (no “sync/classify” jargon) |

## Organize queues (UI)

- **Opportunities** — new business (`business_lead`)
- **Needs reply** — `action_needed`, `existing_client`
- **Clear out** — marketing, personal, spam/risk, vendors
- **Not sure** — chip for `review_needed` (not a fourth equal tab)

## Actions (simple mode)

| Queue | Primary actions |
|-------|-----------------|
| Opportunities | Save lead, Mark done |
| Needs reply | Mark done |
| Clear out | Mark done, File away in Gmail (confirmed) |

- **Mark done** → backend `dismiss` (hidden from Organize; Gmail unchanged)
- **Undo** → backend `restore_to_queue` (workflow `active`, visible again)
- Delete/spam/labels/re-classify are not shown in simple mode

## Trust copy (Organize footer)

- Fikiri organizes your inbox. You stay in control.
- Nothing leaves Gmail without your approval.
- Filed mail stays in Gmail All Mail.

## Code map

- Constants: `frontend/src/constants/inboxSimpleFirst.ts`
- Shell: `frontend/src/pages/InboxPage.tsx`
- Organize UI: `frontend/src/pages/EmailCommandCenter.tsx`
- Read badges: `frontend/src/components/LiveMailLocalBadges.tsx`
- Workflow restore: `email_automation/email_workflow_state.py` (`restore_to_queue`)
