# Email Triage Engine (Inbox Command Center)

## Architecture

```
Gmail Sync → synced_emails
           → Email Triage (rules first)
           → email_classifications table
           → CRM lead creation (user-approved bulk)
           → Gmail actions (archive/label/read/trash/spam only after approval)
```

## Categories

| ID | Command Center tab |
|----|-------------------|
| `business_lead` | Leads |
| `action_needed` | Action Needed |
| `existing_client` | Clients |
| `vendor_partner` | Vendors |
| `newsletter_marketing` | Marketing/Newsletters |
| `spam_risk` | Spam/Risk |
| `personal_non_business` | Personal/Non-Business |
| `review_needed` | Review Queue |

## Structured fields

- `category`, `lead_score`, `business_relevance_score`, `urgency_score`
- `cleanup_action`: `keep` \| `archive` \| `label` \| `delete_candidate` \| `spam_candidate`
- `confidence`, `reason`, `suggested_labels`

**Never auto-deletes.** Destructive cleanup actions require `confirm_destructive: true` on bulk API.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/email/triage?category=&limit=&offset=` | List classified emails + tab metadata |
| POST | `/api/email/triage/classify` | Batch classify synced rows (rules; uses AI analysis if already run) |
| POST | `/api/email/triage/bulk-action` | `archive`, `mark_read`, `mark_unread`, `label`, `create_leads`, `delete_candidate`, `spam_candidate` |

## Code map

- Taxonomy: `core/ai/email_triage_taxonomy.py`
- Engine: `email_automation/email_triage_engine.py`
- Store: `core/email_triage_store.py`
- Service + bulk: `services/email_triage_service.py`
- Routes: `routes/email_triage.py`
- Hooks: `email_automation/gmail_sync_jobs.py` (rules on sync), `email_automation/pipeline.py` (enrich after mailbox AI)

## Tests

- `tests/test_email_triage_engine.py`
- `tests/test_email_triage_routes.py`
