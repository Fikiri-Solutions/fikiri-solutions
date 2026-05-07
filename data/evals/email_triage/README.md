# Email Triage Eval Dataset

Versioned baseline dataset for inbound email triage offline evaluation.

- Dataset file: `email-triage-v1.jsonl`
- Record shape:
  - `gold_intent`, `pred_intent`
  - `gold_urgency`, `pred_urgency`
  - `schema_valid` (bool)
  - `unsafe_recommendation` (bool)
  - `latency_ms` (number)
  - `cost_usd` (number)

Run:

`python3 scripts/run_email_triage_eval.py`

