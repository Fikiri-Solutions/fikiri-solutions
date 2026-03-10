# Coming Soon / Not Guaranteed

Single reference for features that are not fully implemented or cannot be guaranteed. Use this to label UI consistently and align Cursor/Codex audits.

## Convention

- **Frontend:** Disable the control and show "Coming soon" (or "(coming soon)" in label). Use `FeatureStatus` with `coming-soon` where a status badge is shown. Use `title="Coming soon"` on disabled buttons.
- **Backend:** No user-facing "coming soon"; document here so UI can stay in sync.

## Frontend

| Location | Item | Label |
|----------|------|--------|
| **Login** | GitHub button | Disabled, "GitHub (soon)", title "Coming soon" |
| **Signup** | Gmail, GitHub social signup | Disabled, "Gmail (coming soon)" / "GitHub (coming soon)", title "Coming soon" |
| **EmailInbox** | "More options" (additional actions) | Toast: "Additional options coming soon." |
| **FeatureStatus / getFeatureStatus** | Analytics | `coming-soon` |
| **FeatureStatus / getFeatureStatus** | Integrations | `coming-soon` |
| **ServicesLanding** | Some pricing/CTA copy | "Coming soon" where applicable |

## Backend / Capabilities

- **Analytics dashboard:** Partial; not all metrics guaranteed.
- **Integrations:** Gmail and Outlook OAuth are implemented; other providers (e.g. Notion) may be stubs or not implemented.
- **Multi-channel / channel handlers:** Abstract base raises `NotImplementedError`; concrete handlers must implement.
- **Integration framework:** Providers must implement `get_auth_url`, `exchange_code_for_tokens`, `refresh_access_token`, `revoke_token`.

## Consistency

When adding or changing "coming soon" items:

1. Update this doc.
2. In the UI: disable the control and show "Coming soon" (or use `FeatureStatus` / `getFeatureStatus` with `coming-soon`).
3. Do not show raw errors like "not yet implemented" to users.
