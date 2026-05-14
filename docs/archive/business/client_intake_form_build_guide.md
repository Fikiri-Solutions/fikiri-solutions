# Client Intake Form — Google Forms & Typeform Build Guide

Use this guide to build the same intake flow in **Google Forms** or **Typeform**. Question order matches [`./client_intake_form.md`](./client_intake_form.md).

**Legend — answer types**

| Type | Google Forms | Typeform |
|------|----------------|----------|
| Short text | Short answer | Short Text |
| Long text | Paragraph | Long Text |
| Single choice | Multiple choice (one) | Multiple Choice |
| Multi-select | Checkboxes | Multiple Selection |
| Email | Short answer + validation | Email |
| Phone | Short answer | Phone Number |
| URL | Short answer | Website / URL |
| Linear scale | Linear scale | Opinion Scale / Rating |
| Section | Section title + description | Welcome / Statement / Question Group |

**Required policy:** Mark **Required** only where noted. Optional fields reduce abandonment; you can turn more on later.

---

## Form settings (both platforms)

- **Title:** Fikiri Solutions — Client Intake  
- **Description (intro):** Short paragraph: 10–15 minutes, helps prep consultation, honest rough numbers OK, “leads/jobs/orders” interchangeable. Link privacy note if you publish one.  
- **Confirmation message:** Thank you + what happens next (e.g., “We’ll review and confirm your call”).  
- **Collect email (Google Forms):** Either use built-in “collect emails” *or* include an explicit Email question—avoid duplicating.  
- **Typeform:** Enable progress bar; mobile-friendly theme.

---

## Section 1 — Business information

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 1.1 | Business name | Short text | Yes |
| 1.2 | Owner / primary contact name | Short text | Yes |
| 1.3 | Email | Email | Yes |
| 1.4 | Phone | Phone or short text | Yes |
| 1.5 | Website | URL or short text | No |
| 1.6 | Social links (optional) | Long text | No |
| 1.7 | Industry | Short text *or* dropdown with “Other” | Yes |
| 1.8 | Location (city, state) | Short text | Yes |
| 1.9 | Years in business | Single choice: Under 1 / 1–3 / 4–7 / 8–15 / 16+ *or* short text | No *(recommended Yes if you need qualification)* |

**Industry dropdown (optional):** Transportation & logistics; Construction & trades; Home services; Real estate; Healthcare & wellness; Beauty & personal care; Retail & ecommerce; Hospitality & food; Professional services; Manufacturing & wholesale; Other (short text).

---

## Section 2 — Business size

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 2.1 | Number of employees | Single choice: 1 (solo) / 2–5 / 6–15 / 16–50 / 51+ / Prefer not to say | Yes |
| 2.2 | Monthly revenue range | Single choice: Under $10K / $10K–$25K / $25K–$50K / $50K–$100K / $100K–$250K / $250K+ / Prefer not to say | No |
| 2.3 | Average leads, jobs, or orders per week | Single choice: Fewer than 5 / 5–15 / 16–50 / 51–150 / 151+ / Not sure | Yes |
| 2.4 | Brief note on volume (seasonality, etc.) | Long text | No |
| 2.5 | Current growth stage | Single choice: Getting established / Stable / Growing fast / Plateaued / Restructuring or selling | No |

---

## Section 3 — Current workflow (Input → Decision → Execution → Follow-Up → Money)

**Section description:** One sentence: “Walk through how work moves from first contact to payment.”

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 3.1 | How does work come into your business? (channels — email, phone, portals, etc.) | Long text | Yes |
| 3.2 | Where do leads, jobs, or orders usually come from? | Long text | Yes |
| 3.3 | Who reviews or decides what to do next? | Long text | Yes |
| 3.4 | What happens after the decision? (steps until work is complete) | Long text | Yes |
| 3.5 | Who does the work? (roles) | Long text | No |
| 3.6 | How do you follow up with customers or partners? | Long text | No |
| 3.7 | Where do things get delayed, dropped, or missed? | Long text | Yes |

---

## Section 4 — Current tools / digital infrastructure

**Option A — Matrix-style (compact)**  
One multi-select or checkbox list: “Which categories do you use?” + **one** long-text field: “List main tool names (optional).”

**Option B — One row per category (matches markdown form)**

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 4.1 | Email platform | Short text *or* single choice (Gmail / Outlook / Microsoft 365 / Other) | No |
| 4.2 | Phone / SMS tools | Short text | No |
| 4.3 | CRM or customer database | Short text + option “None” | No |
| 4.4 | Spreadsheets | Single choice: Yes / No / Not sure | No |
| 4.5 | Website | Short text + None | No |
| 4.6 | Booking / scheduling tools | Short text + None | No |
| 4.7 | Payment / invoicing tools | Short text + None | No |
| 4.8 | Social media (business) | Short text + None | No |
| 4.9 | Industry-specific software (name main ones) | Long text | No |
| 4.10 | Zapier, Make, or other automation | Single choice: Yes / No / Not sure | No |
| 4.11 | AI tools already in use | Long text | No |
| 4.12 | Anything important we didn’t list? | Long text | No |

---

## Section 5 — Pain points

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 5.1 | What tasks are repetitive? | Long text | Yes |
| 5.2 | What takes too long? | Long text | No |
| 5.3 | What gets missed or falls through the cracks? | Long text | Yes |
| 5.4 | Where do you lose money? (time, errors, no-shows, unbilled work, etc.) | Long text | No |
| 5.5 | If you could automate one thing first, what would it be? | Long text | Yes |

---

## Section 6 — Budget and readiness

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 6.1 | Are you currently paying for business software? | Single choice: Yes / No / Minimal | No |
| 6.2 | Rough monthly budget for automation or ongoing support | Single choice: Under $500 / $500–$1,500 / $1,500–$5,000 / $5,000+ / Not sure / Prefer not to say | No |
| 6.3 | What kind of help are you looking for? | Single choice: One-time setup / Monthly service / Both / Not sure | Yes |
| 6.4 | How soon do you want to start? | Single choice: ASAP / Within 30 days / 1–3 months / Exploring | Yes |
| 6.5 | Anything else about timing or budget? | Long text | No |

---

## Section 7 — Consent and follow-up

| # | Question | Answer type | Required? |
|---|-----------|-------------|-----------|
| 7.1 | Consent: I agree that Fikiri Solutions may contact me about my inquiry and related automation services at the email/phone provided. I can opt out anytime. | Single choice: I agree *(one checkbox)* — **use Required validation** | **Yes** |
| 7.2 | How would you like us to follow up? | Single choice: Email / Phone / Text / No preference | No |

**Legal note:** Keep consent language aligned with your published privacy policy and regional rules (e.g., SMS requires appropriate consent). This is operational copy, not legal advice.

---

## Google Forms–specific tips

- Use **Sections** for each numbered section above.  
- Turn on **Response validation** on Email.  
- For consent, use a single required multiple-choice with one option “I agree” or a required Checkbox question (Forms checkbox limitation: often easier as Multiple choice).  
- **Do not** enable “Limit to 1 response” unless respondents must sign in with Google (hurts conversion).

---

## Typeform–specific tips

- Use **Question groups** for sections; add a **Welcome screen** with the intro paragraph.  
- Use **Long Text** for workflow and pain questions; increase character limit if needed.  
- **Logic jumps (optional):** If “Number of employees” = 1, you could skip team-heavy follow-ups later—only if you maintain the form.  
- **Email question** type for 1.3; **Phone** type for 1.4 if available.

---

## Export / integration

- **Google Sheets:** Enable auto Sheet for responses; link from CRM or Notion if needed.  
- **Typeform:** Webhooks or Zapier/Make to Sheet, CRM, or email notification to team@fikiri.com.

---

**Files paired with:** [`./client_intake_form.md`](./client_intake_form.md) · [`./fikiri_consultation_framework.md`](./fikiri_consultation_framework.md)
