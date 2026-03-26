# CRM Lead Scoring: Process, Code, and Techniques

## Overview

Lead scoring in Fikiri is a **rule-based, weighted model** that produces a 0–100 score and a quality band (A/B/C/D). The score is stored on the lead and used for prioritization and automation (e.g. auto-moving high-scoring leads to "qualified").

---

## 1. Architecture

| Layer | Role |
|-------|------|
| **`core/lead_scoring_service.py`** | Pure scoring logic: inputs → score + quality + breakdown. No DB. |
| **`crm/service.py`** | When to score: on create, on update, and via explicit recalc. Fetches activity metrics and persists score + metadata. |
| **Automation** | `lead_scoring` preset: when a lead is created and `score >= min_score`, stage is updated (e.g. to `qualified`). |

**Data flow**

1. **Create lead** → CRM calls `_score_lead_data(lead_data, 0, None)` → score written to `leads.score`, breakdown to `leads.metadata` → `LEAD_CREATED` automation runs (can move stage if score ≥ threshold).
2. **Update lead** → CRM reloads lead, gets `activity_count` and `last_activity`, calls `_score_lead_data` → score and metadata updated.
3. **Explicit recalc** → `POST /api/crm/leads/<id>/score` → `recalculate_lead_score()` → same as update path but no field changes.

---

## 2. Scoring Formula (Technique)

**Weighted sum of five components**, each normalized to 0–100, then clamped to 0–100:

```
score = round( clamp(
    source_score      * w_source      +
    recency_score     * w_recency     +
    stage_score       * w_stage       +
    engagement_score  * w_engagement   +
    attributes_score  * w_attributes
, 0, 100) )
```

**Default weights** (configurable via `LEAD_SCORING_WEIGHTS` env JSON):

- `source`: 0.25  
- `recency`: 0.20  
- `stage`: 0.20  
- `engagement`: 0.20  
- `attributes`: 0.15  

### 2.1 Component Definitions

- **Source** (0–100): Lookup from a fixed map (e.g. referral=100, partner=90, gmail=75, website=65, manual=40). Unknown source → 50.
- **Recency** (0–100): Newer = higher. `100 - min(age_days, 60) * 1.5`; if no `created_at`, treat as 30 days old.
- **Stage** (0–100): Lookup (e.g. new=40, contacted=55, replied=65, qualified=80, closed=95).
- **Engagement** (0–100):  
  - Up to 60 from activity count: `min(activity_count * 10, 60)`.  
  - Up to 40 from last activity recency: `40 - min(days_since_activity, 30) * 1.3`.  
  - Sum capped at 100.
- **Attributes** (0–100): Completeness. company +30, phone +25, valid email +25, name +20; total capped at 100.

### 2.2 Quality Bands

- **A**: score ≥ 80  
- **B**: score ≥ 60  
- **C**: score ≥ 40  
- **D**: &lt; 40  

Stored in `metadata.lead_quality`; breakdown in `metadata.score_breakdown`.

---

## 3. Code Locations

| What | Where |
|------|--------|
| Scoring logic (weights, components, formula) | `core/lead_scoring_service.py` → `LeadScoringService.score_lead()` |
| When score is computed on create | `crm/service.py` → `create_lead()` → `_score_lead_data()` before INSERT |
| When score is recomputed on update | `crm/service.py` → `update_lead()` → `_get_lead_activity_metrics()` then `_score_lead_data()` then UPDATE |
| Activity metrics for engagement | `crm/service.py` → `_get_lead_activity_metrics(lead_id)` (count + last activity time) |
| Bridge from CRM to scorer | `crm/service.py` → `_score_lead_data(lead_data, activity_count, last_activity)` → `get_lead_scoring_service().score_lead(...)` |
| Manual recalc API | `routes/business.py` → `POST /api/crm/leads/<lead_id>/score` → `enhanced_crm_service.recalculate_lead_score()` |
| Automation: score ≥ threshold → stage | `core/automation_engine.py` → `_execute_update_crm_field()` when `action_parameters.slug == 'lead_scoring'` |
| Trigger for lead_scoring automation | `crm/service.py` → `create_lead()` fires `TriggerType.LEAD_CREATED` with `lead_id`, `score`, etc. |

---

## 4. Techniques in Use

1. **Single responsibility**  
   `LeadScoringService` only computes score; CRM decides when to call it and where to store the result.

2. **Configurable weights**  
   Env var `LEAD_SCORING_WEIGHTS` (JSON) overrides default weights so the same code can be tuned without code change.

3. **Transparency**  
   Every score comes with a `breakdown` (per-component scores and weights) stored in `metadata.score_breakdown` for debugging and UI.

4. **Deterministic and testable**  
   `score_lead(lead_data, activity_count, last_activity, now=None)` is pure (no DB); optional `now` for tests.

5. **Quality band**  
   A/B/C/D derived from score and stored in `metadata.lead_quality` for filtering and reporting.

6. **Engagement from activity**  
   Engagement uses `lead_activities`: count and last activity timestamp. Score is recomputed on lead update so engagement changes are reflected when any lead field is updated; it is **not** recomputed automatically when a new activity is added (see below).

---

## 5. When Score Is (Not) Updated

- **Updated:** On lead create, on lead update (any allowed field), and on explicit `POST .../score`.
- **Not updated automatically:** When only a new activity is added (e.g. email_received, call_made). So engagement can lag until the next lead update or manual recalc. Optional improvement: call a lightweight recalc after `add_lead_activity` for contact-type activities.

---

## 6. Automation: Lead Scoring Preset

- **Trigger:** `lead_created`.  
- **Action:** `update_crm_field` with `slug: 'lead_scoring'`.  
- **Parameters:** `min_score` (default 60), optional `target_stage` (default `qualified`).  
- **Behaviour:** After a lead is created, the engine runs; if `lead.score >= min_score`, it sets `stage = target_stage` and adds a lead activity note.  
- **Implementation:** In `_execute_update_crm_field` (core and services engines), when `slug == 'lead_scoring'`, read lead from DB, compare `score` to `min_score`, then update stage and add activity.

---

## 7. Other Scoring Paths (Context Only)

- **Webhook intake** (`core/webhook_intake_service.py`) has a simpler `_calculate_lead_score()` (attribute bonuses only); used for webhook-originated leads before they may be merged into CRM.
- **Minimal ML scoring** (`core/minimal_ml_scoring.py`) is a separate, optional path (e.g. email-based features, ML model); not wired into the main CRM create/update flow above.

The **canonical** CRM score for leads in the CRM DB is the one produced by `LeadScoringService` and persisted by `crm/service.py`.
