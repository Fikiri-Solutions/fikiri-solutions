# Export & Import Data Formats

Reference for what data clients can **export** (and in what format) and what they can **upload/import** into Fikiri.

---

## 1. Exports (what clients get when they export)

| Where | Data | Format | Notes |
|-------|------|--------|--------|
| **Account Management → Export Data** | Profile, security prefs, notification prefs | **JSON** | Downloaded as `fikiri-account-data-YYYY-MM-DD.json`. Built client-side from current form state. |
| **Backend GDPR export** `POST /api/user/export-data` | User profile + CRM leads | **JSON** | Response is JSON (profile + `user_data.leads`). Not CSV or PDF. |
| **Workflow table export** `POST /api/workflows/tables/export` | Table/sheet (columns + rows) | **CSV** or **JSON** | User chooses format. Returns file download (`name.csv` or `name.json`). |
| **Dashboard export** (Dashboard controls) | Dashboard data | **PDF** or **CSV** | UI offers "Export PDF" / "Export CSV"; actual implementation is in the parent component that uses `DashboardControls`. |
| **Document analytics** | Analytics data | **JSON** or **CSV** | Via `DocumentAnalyticsSystem.export_analytics_data(days, format)`. |
| **CRM leads** | **CSV** | **GET /api/crm/leads/export** | One-click from CRM page. Filename `leads.csv`. Columns: id, name, email, phone, company, source, stage, score, created_at. |

**Summary:**  
- **CRM leads** can be exported as **CSV** via **GET /api/crm/leads/export** (button on CRM page). Also available in user/GDPR export (JSON) and workflow table export (CSV/JSON).  
- **Account/Privacy “export my data”** is JSON only (backend and Account Management download).  
- **PDF** is only offered for dashboard export (and possibly document/workflow outputs), not for account or CRM data.

---

## 2. Imports / uploads (what clients can send us)

### Chatbot knowledge base (Chatbot Builder)

| Method | Format | Allowed types | Notes |
|--------|--------|----------------|-------|
| **UI file upload** | File | **.pdf, .doc, .docx, .txt, .csv, .xlsx, .xls** | `accept` includes CSV and Excel. File is processed (text extracted), then content can be added to KB. |
| **API single** `POST /api/chatbot/knowledge/import` | JSON body | **Text only** | `content` or `question`+`answer`; no file upload in this endpoint. |
| **API bulk** `POST /api/chatbot/knowledge/import/bulk` | JSON body | **Text only** | `documents: [{ title?, content? \| question?, answer?, category?, ... }]`. |

### Document processor (backend)

The backend `AIDocumentProcessor` supports more types than the Chatbot Builder UI exposes:

| Category | Extensions | Notes |
|----------|------------|--------|
| **PDF** | .pdf | Text extraction (PyPDF2). |
| **Document** | .docx, .doc | Word. |
| **Spreadsheet** | .xlsx, .xls, .csv | Excel/CSV. |
| **Text** | .txt, .md, .rtf | Plain text / Markdown / RTF. |
| **Image** | .jpg, .jpeg, .png, .gif, .bmp, .tiff | OCR (if Tesseract available). |

So: **chatbot “upload” in the UI is currently PDF, DOC, DOCX, TXT only.** Spreadsheets (CSV/XLSX) and images are supported by the processor but not wired in the Chatbot Builder file input.

### CRM leads import

| Method | Format | Allowed types | Notes |
|--------|--------|----------------|-------|
| **API** `POST /api/crm/leads/import` | **JSON only** | N/A | Body: `{ "leads": [ { "email", "name", ... } ] }`. |
| **API** `POST /api/crm/leads/import/csv` | **CSV file** | .csv | Multipart `file`. See CSV requirements and duplicate handling below. UI: Import CSV button + Download template on CRM page. |

So: **clients can upload a CSV of leads** via the CRM page ("Import CSV") or `POST /api/crm/leads/import/csv`. A "Download template" button provides the expected format.

#### Duplicate handling (CSV import)

Query or form param **`on_duplicate`**: `skip` | `update` | `merge` (default: `update`). If a lead with the **same email** already exists:

- **update** — existing lead is overwritten (name, phone, source, company updated).
- **skip** — existing lead is left unchanged; row is counted in `skipped_duplicate`.
- **merge** — existing lead is updated only for non-empty fields from the CSV row.

Response includes:

- `imported` — total rows that resulted in a create or update (i.e. `created + updated`)
- `created` — new leads added
- `updated` — existing leads updated (same as **duplicate_count** for “already had this email”)
- `skipped` — rows not imported (missing or invalid email)
- `skipped_duplicate` — rows skipped (duplicate email with on_duplicate=skip, or merge had no non-empty fields)
- `skipped_details` — up to 50 entries: `{ "row": <1-based>, "reason": "missing email" | "invalid email", "email": "<value>"? }`
- `total_rows` — total rows in the file (valid + skipped)

Duplicate = existing email; behavior depends on `on_duplicate`. Skipped = validation failure (missing/invalid email).

#### Import response format (CSV import)

Success response (wrapped in your standard API envelope, e.g. `data`):

```json
{
  "success": true,
  "imported": 120,
  "created": 100,
  "updated": 20,
  "skipped": 10,
  "skipped_duplicate": 0,
  "skipped_details": [
    { "row": 5, "reason": "invalid email", "email": "bad" },
    { "row": 12, "reason": "missing email" }
  ],
  "total_rows": 130
}
```

Error response (e.g. no file, wrong type, empty file, no valid rows):

- `error`: human-readable message  
- `code`: e.g. `NO_FILE`, `INVALID_FILE_TYPE`, `INVALID_CSV`, `MISSING_FIELDS`

Frontend should show: **imported** (and optionally created/updated/skipped) so the user sees clear feedback; use `skipped_details` for “row X failed: reason”.

#### CSV requirements (CRM import)

- **Header row required** — first line must contain column names.
- **Column names case-insensitive** — `Email`, `email`, `EMAIL` all map to `email`; same for `name`, `phone`, `source`, `company`.
- **Required columns:** `email`, `name`. Missing or invalid email → row skipped and counted in `skipped` / `skipped_details`.
- **Optional columns:** `phone`, `source`, `company`. Extra columns are ignored.
- **Max file size / max rows:** Enforced: **5 MB** max file size, **10,000 rows** max per file. Requests over the limit return `FILE_TOO_LARGE` or `TOO_MANY_ROWS`. See CRM import safeguards below.

#### Import preview (implemented)

**POST /api/crm/leads/import/csv/preview** — same file and auth as import; validates only (no insert). Returns `preview: true`, `total_rows`, `valid_rows`, `invalid_rows`, `summary: { ok, duplicate, invalid }`, and `rows` (up to 500) with `{ row, email, name, status: "ok" | "duplicate" | "invalid", reason? }`. Frontend can do: Upload → Preview → Confirm → Import.

Previous target flow (for reference):

1. **Upload CSV** → backend validates only (no insert).
2. **Validate** → per-row checks: required columns, email format, optional duplicate detection.
3. **Show preview** → table of rows with status: OK / Duplicate / Invalid, and error message per row.
4. **Confirm** → user chooses “Import all” or “Skip duplicates” / “Update duplicates”, then backend performs import.

Current flow is **upload → direct insert** (with validation failures skipped and reported in the response). Adding a dedicated “preview” step and confirm would reduce risk and feel like a serious SaaS product.

#### CRM import safeguards

- **Max rows per request** — **Implemented:** 10,000 rows per CSV import; returns `TOO_MANY_ROWS` if exceeded.
- **Max file size** — **Implemented:** 5 MB; returns `FILE_TOO_LARGE` if exceeded.
- **Rate limiting** — **Implemented:** 30 CSV imports per user per hour; 429 `RATE_LIMIT_EXCEEDED` with `retry_after`, `limit`, `remaining`.
- **Idempotency** — **Implemented:** optional `Idempotency-Key` header (or form `idempotency_key`). Same key returns cached 200; in-flight same key returns 409 `IDEMPOTENCY_CONFLICT`. TTL 24h.

---

### Chatbot upload

Chatbot Builder UI now accepts **.pdf, .doc, .docx, .txt, .csv, .xlsx, .xls**. Images (OCR) are supported by the backend processor but not yet in the Chatbot Builder file input.

---

## 3. Summary table

| Question | Answer |
|----------|--------|
| When exporting account or CRM data, what format? | **Account/Privacy export:** JSON only. **CRM leads:** CSV via GET /api/crm/leads/export, and also included in GDPR export JSON. Workflow tables: CSV or JSON. |
| Can clients export as CSV? | Yes for **CRM leads** and **workflow tables**. |
| Can clients export as PDF? | Only where implemented (e.g. dashboard export). Not for account or CRM data currently. |
| What can clients upload for **chatbot**? | **UI:** PDF, DOC, DOCX, TXT, CSV, XLSX, XLS. **API:** JSON text (content or Q&A). Backend processor also supports images (OCR); UI does not expose images yet. |
| What can clients upload for **CRM**? | **JSON** via POST /api/crm/leads/import and **CSV file upload** via POST /api/crm/leads/import/csv (also available in CRM UI). |

---

## 4. Possible improvements (no code changes in this doc)

- **CRM:** Optional **PDF export** of leads. **Duplicate-handling modes** (skip / update / merge) and **import preview** are implemented.
- **Chatbot:** CSV/XLSX are now allowed in the UI file upload.
- **Account/Privacy export:** Optional **CSV/PDF** for profile and leads (in addition to JSON).
- **CRM import:** Support **XLSX** in addition to CSV (e.g. POST /api/crm/leads/import/csv extended or a separate XLSX endpoint).

---

## 5. Product position

CSV import/export, GDPR-style export, and documented API endpoints move Fikiri from “AI tool” to **business infrastructure**: clear **ingestion** (import), **storage** (CRM), **retrieval** (export), and **integration** (webhooks + SDK). That’s real product territory and removes a major adoption blocker for SMBs: they can bring their data in and take it out.