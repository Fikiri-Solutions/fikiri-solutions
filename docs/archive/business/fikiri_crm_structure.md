# Fikiri Solutions — CRM / Lead Database Structure

**Purpose:** One Notion database (or equivalent) to track prospects from first touch through close, aligned with **Input → Decision → Execution → Follow-Up → Money**.

**Solo-founder default:** One database named **Leads** (or **Pipeline**). Use views—not duplicate databases.

---

## Database: `Leads` — property specification

### How to read this table

- **Type** = Notion property type to use.  
- **Options** = select/multi-select choices where relevant.  
- **Notes** = optional formulas or conventions.

---

### 1. Lead information

| Property name | Type | Options / format | Notes |
|---------------|------|------------------|--------|
| **Name** | Title | — | Use **Business Name** as the title for scanning; see Lead ID below. |
| **Lead ID** | Text | `FIK-YYYY-###` | Manual or formula prefix + counter; keeps exports clean. |
| **Business Name** | Text | — | Duplicate from title if you prefer title = contact name—pick one convention and stick to it. |
| **Contact Name** | Text | — | Primary contact. |
| **Email** | Email | — | |
| **Phone** | Phone | — | |
| **Website** | URL | — | |
| **Industry** | Select | See starter list below | Add freely. |
| **Location** | Text | City, ST | |
| **Source** | Select | Website · Referral · LinkedIn · Event · Cold outreach · Partner · Inbound form · Other | Tracks marketing ROI. |

**Industry (starter selects):** Transportation / logistics · Construction / trades · Home services · Real estate · Healthcare / wellness · Beauty · Retail / ecommerce · Hospitality · Professional services · Manufacturing · Other

---

### 2. Lead status

| Property name | Type | Options | Notes |
|---------------|------|---------|--------|
| **Lead Status** | Select | **New Lead** · **Intake Submitted** · **Consultation Scheduled** · **Consultation Completed** · **Proposal Sent** · **Follow-Up Needed** · **Won** · **Lost** · **Not Qualified** | Single source of truth for pipeline. |

**Recommended order in select settings** (drag to match funnel): New Lead → Intake Submitted → Consultation Scheduled → Consultation Completed → Proposal Sent → Follow-Up Needed → Won / Lost / Not Qualified

---

### 3. Business profile

| Property name | Type | Options / format | Notes |
|---------------|------|------------------|--------|
| **Business Size** | Select | Solo · 2–5 · 6–15 · 16–50 · 51+ | |
| **Monthly Revenue Range** | Select | Under $10K · $10K–$25K · … · Prefer not to say | Match intake form bands. |
| **Number of Employees** | Number | Integer | Optional if redundant with Business Size. |
| **Weekly Lead Job Volume** | Select | Fewer than 5 · 5–15 · 16–50 · 51–150 · 151+ · Unknown | |
| **Current Tools** | Text | Long | Comma-separated or short prose from intake/call. |
| **Digital Infrastructure Score** | Number | 1–5 | Subjective; see `./fikiri_lead_scoring.md` for calibration. |

---

### 4. Workflow diagnosis

| Property name | Type | Notes |
|---------------|------|--------|
| **Input Summary** | Text | Where work enters. |
| **Decision Bottleneck** | Text | Who decides, delay, rules unclear. |
| **Execution Process** | Text | Who does the work after yes. |
| **Follow-Up Process** | Text | Confirmations, reminders, reviews. |
| **Money Revenue Impact** | Text | How cash ties in; leakage notes. |
| **Main Pain Point** | Text | One line + detail OK. |
| **Automation Opportunity** | Text | What you’d build first. |

---

### 5. Deal information

| Property name | Type | Options / format | Notes |
|---------------|------|------------------|--------|
| **Recommended Service Tier** | Select | Entry · Standard · Complex | Align with [`./fikiri_consultation_framework.md`](./fikiri_consultation_framework.md). |
| **Setup Fee** | Number | USD | |
| **Monthly Fee** | Number | USD | |
| **Estimated Value to Client** | Text | Or Number if you prefer annual $ | Qualitative OK for solo (“med-high time save”). |
| **Proposal Link** | URL | Google Doc / PandaDoc / PDF link | |
| **Contract Sent** | Checkbox | | |
| **Contract Signed** | Checkbox | | |
| **Payment Received** | Checkbox | | |

---

### 6. Follow-up tracking

| Property name | Type | Options / format | Notes |
|---------------|------|------------------|--------|
| **Last Contact Date** | Date | Include date only or datetime | |
| **Next Follow-Up Date** | Date | | Drives reminders. |
| **Follow-Up Notes** | Text | | Last promise / context. |
| **Priority Level** | Select | Low · Medium · High · Urgent | |
| **Close Probability** | Number | 0–100 | Quick gut check; optional vs formula from score. |
| **Next Action** | Select | Call · Email · Send proposal · Schedule · Waiting on client · Internal prep · Nurture · Closed | |

---

### 7. Internal notes

| Property name | Type | Notes |
|---------------|------|--------|
| **Call Notes** | Text | Long; embed bullets from consultation. |
| **Objections** | Text | |
| **Decision Maker** | Text | Name + role if known. |
| **Budget Concerns** | Text | |
| **Custom Requirements** | Text | Compliance, integrations, weird edge cases. |

---

### Recommended extras (optional)

| Property name | Type | Purpose |
|---------------|------|--------|
| **Lead Score** | Number | 0–100 from [`./fikiri_lead_scoring.md`](./fikiri_lead_scoring.md) |
| **Created time** | Created time | Auto |
| **Consultation Date** | Date | Scheduled session |
| **Owner** | Person | If you add a VA later |

---

## Notion database setup guide

### Step 1 — Create the database

1. In Notion, create a new page: **Fikiri CRM** (or add to your workspace hub).  
2. Type `/database` → **Table – Full page** (or inline if you prefer).  
3. Name the database **Leads**.

### Step 2 — Set the title column

- Default first column is **Name**. Use it for **Business Name** (fast scanning).  
- Add **Contact Name** as a separate text property.

### Step 3 — Add properties in batches

1. Add properties from section **1. Lead information** (avoid duplicates—**Email** type exists in Notion).  
2. Add **Lead Status** (Select) with all options—paste options one by one or add multi later.  
3. Add **Business profile** fields.  
4. Add long **Text** fields for **Workflow diagnosis** and **Internal notes**—toggle **Wrap** on for readability.  
5. Add **Deal** fields: numbers, checkboxes, URL.  
6. Add **Follow-up** dates and selects.  
7. Add **Lead Score** as number (0–100).

### Step 4 — Forms (optional)

- **Create form** from database (Notion Forms): map Business Name, Email, Phone, Industry, Source, short pain—default new rows to **New Lead** or **Intake Submitted**.  
- Keep internal fields (scores, deal checkboxes) off the public form.

### Step 5 — Templates (optional)

- Database → **⋯** → **Templates** → New template: pre-fill **Lead Status** = Consultation Scheduled when you use it from calendar-driven adds.

### Step 6 — Permissions

- Solo: full access.  
- If sharing: Guest **cannot access internal pages** unless invited—keep proposal links permissioned at source (Google Doc).

---

## Simple pipeline view (Board)

### View name: `Pipeline`

| Setting | Value |
|---------|--------|
| **Layout** | Board |
| **Group by** | Lead Status |
| **Sort** | Next Follow-Up Date → ascending (empty last), or Priority → descending |
| **Card preview** | Show: Contact Name, Industry, Next Follow-Up Date, Lead Score |
| **Filter** (optional) | Lead Status **is not** Won **and** **is not** Lost **and** **is not** Not Qualified — *or* show all and use status columns |

**Tip:** Drag cards across columns when status changes—fastest update during the week.

---

## Secondary views (quick adds)

| View name | Type | Filter / sort |
|-----------|------|----------------|
| **This week** | Table | Next Follow-Up Date **on or before** 7 days from now; Status not Won/Lost/NQ |
| **Hot** | Table | Lead Score **≥** 70 **or** Priority **is** High/Urgent |
| **Consultation prep** | Table | Status **is** Consultation Scheduled · Sort by Consultation Date |
| **Proposals out** | Table | Status **is** Proposal Sent **or** Follow-Up Needed |

---

## Links to other docs

- Scoring: `./fikiri_lead_scoring.md`
- Consultation notes: `./fikiri_consultation_notes_template.md`
- Follow-up & proposal blurbs: `./fikiri_follow_up_templates.md`
- Framework: `./fikiri_consultation_framework.md`

---

**Version:** 1.0
