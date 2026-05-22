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

## Actions (simple-first, not weak)

| Queue | Primary actions |
|-------|-----------------|
| Opportunities | Save lead, Open (Read), Mark done |
| Needs reply | Open, Mark done, File away (confirmed) |
| Clear out | File away, Apply recommendations, Mark done; guarded Report spam / Move to trash |
| Not sure | Review (Read), Apply safe cleanup, Move to Clear out, Mark done |

- **Mark done** → backend `dismiss` (hidden from Organize; Gmail unchanged; undo available)
- **Apply recommendations** → groups existing `cleanup_action` per row; confirms before Gmail bulk API
- **Report spam / Move to trash** → only on Clear out; require `confirm_destructive` on API
- User-facing copy never exposes `cleanup_action`, taxonomy slugs, or scores

## Trust copy (Organize footer)

- Fikiri organizes your inbox. You stay in control.
- Nothing leaves Gmail without your approval.
- Filed mail stays in Gmail All Mail.

## Code map

- Queue groupings: `frontend/src/constants/inboxSimpleFirst.ts`
- Queue actions: `frontend/src/constants/organizeQueueActions.ts`
- Recommendation copy: `frontend/src/constants/organizeRecommendations.ts`
- Shell: `frontend/src/pages/InboxPage.tsx`
- Organize UI: `frontend/src/pages/EmailCommandCenter.tsx`
- Read + open-from-Organize: `frontend/src/pages/EmailInbox.tsx`
- Read badges: `frontend/src/components/LiveMailLocalBadges.tsx`
- Bulk API: `services/email_triage_service.py` (`execute_bulk_action`)
- Workflow restore: `email_automation/email_workflow_state.py` (`restore_to_queue`)
