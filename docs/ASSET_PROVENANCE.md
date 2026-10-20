# Asset Provenance Inventory (Marketing / Production)

**Last updated:** 2026-10-19  
**Purpose:** Track license/provenance for production visual assets. Incomplete rows need **owner verification** — do not delete client-owned assets automatically.

## Fonts (bundled)

| Asset | Path / package | Source | License | Commercial OK? | Attribution | Evidence |
|-------|----------------|--------|---------|----------------|-------------|----------|
| Plus Jakarta Sans | `@fontsource-variable/plus-jakarta-sans` | Fontsource / Google Fonts family | SIL OFL 1.1 (per Fontsource) | Yes | Usually not required for OFL webfont use | npm package README |
| Source Serif 4 | `@fontsource/source-serif-4` | Fontsource / Adobe | SIL OFL 1.1 (per Fontsource) | Yes | Usually not required | npm package README |
| Inter | removed from `package.json` (unused) | — | — | — | — | Cleanup Pass 2B |

## Client partnership logos

| Asset | Path | Source | License | Commercial OK? | Evidence | Risk |
|-------|------|--------|---------|----------------|----------|------|
| ColorScalez | `frontend/public/images/clients/colorscalez-logo.svg` | Owner-created / prepared for partnership display | First-party (owner confirmation 2026-09-23) | Yes | Owner: self-created | Low |
| Symbolics Technology | `frontend/public/images/clients/symbolics-technology-logo.png` | Owner-created / prepared for partnership display | First-party (owner confirmation 2026-09-23) | Yes | Owner: self-created | Low |
| Shinkei Nettowaku | `frontend/public/images/clients/shinkei-nettowaku-logo.svg` | Owner-created / prepared for partnership display | First-party (owner confirmation 2026-09-23) | Yes | Owner: self-created | Low |
| Aim High Hit Higher | `frontend/public/images/clients/aim-high-hit-higher-logo.webp` | Owner-created / prepared for partnership display | First-party (owner confirmation 2026-09-23) | Yes | Owner: self-created | Low |
| Circa Educational Services | `frontend/public/images/clients/circa-educational-services-logo.webp` | Client site mark (`circaeducationalservices.com`) prepared for partnership display | Client brand use with partnership consent | Yes (display only) | Owner confirmation 2026-10-19 | Low |
| Creating Good Problems | `frontend/public/images/clients/creating-good-problems-logo.png` | Client site mark (`creatinggoodproblems.com`) prepared for partnership display | Client brand use with partnership consent | Yes (display only) | Owner confirmation 2026-10-19 | Low |

## Landing / marketing stills

| Asset | Path | Source | License | Evidence | Risk |
|-------|------|--------|---------|----------|------|
| Landing bento CRM | `frontend/public/images/landing-bento-crm.png` | Higgsfield GPT Image 2.5 refresh (job `4254fc3a-4c54-4f06-bd6b-a9d1a6dbe7b0`, 2026-10-19); black/amber Tier A visual | First-party commission | Rollback: `_backup-pre-higgsfield-2026-10-19/landing-bento-crm.png` | Low |

## Hero / brand media

| Asset | Path | Source | License | Evidence | Risk |
|-------|------|--------|---------|----------|------|
| Baobab hero video | `frontend/public/media/baobab-growth-hero.mp4` (and related) | Owner-created | First-party (owner confirmation 2026-09-23) | Owner: self-created | Low |
| Brand logos | `frontend/public` / Vite assets | First-party | Fikiri-owned | Brand use | Low |

## Removed / disabled in Pass 2B

| Asset | Action |
|-------|--------|
| Google BigBuckBunny sample MP4 URL | Removed as default from `DemoVideoModal`; removed from `/landing-classic` usage |
| `@fontsource/inter` | Removed unused dependency |
| `cta-mockup.svg` / `.html` | Deleted (unused; contained fake 500+/4.9 copy) |
| `email-automation-mockup.html` | Deleted (unused demo metrics) |

## Unused mock assets remaining (not imported by routes)

| Path | Note |
|------|------|
| `frontend/src/assets/cta-mockup.png` | Optional later delete |
| `frontend/src/assets/email-automation-mockup.png` / `.svg` | Optional later delete |
| `frontend/src/assets/dashboard-mockup.*` | Not live-route imports |

## Owner actions

1. ~~Confirm written permission or license for each client logo.~~ **Done 2026-09-23 — owner-created.**
2. ~~Confirm hero video commission/license.~~ **Done 2026-09-23 — owner-created.**
3. Optionally delete remaining unused `*-mockup*` PNGs/SVGs if nothing external hotlinks them.
