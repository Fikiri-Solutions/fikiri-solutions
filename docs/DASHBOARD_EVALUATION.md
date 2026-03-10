# Dashboard Evaluation

Evaluation of the Dashboard page: does it function fully, do features work as promised, and does it update in line with user actions?

---

## Summary

| Area | Status | Notes |
|------|--------|------|
| **Health check / Priority actions** | ✅ Works | Uses real APIs (Gmail, leads, timeseries, automations); scores and recommendations are computed from real data. |
| **Metrics cards (Leads, Emails, AI, Response time)** | ✅ Works | apiClient normalizes backend shape to activeLeads, totalEmails, aiResponses, avgResponseTime; backend includes ai.total. |
| **Charts (Email Trends, Service Performance, Distribution)** | ✅ Works | Use timeseries API (or fallback); data shape is compatible. |
| **Active Services** | ✅ Works | Uses `/services` (or health fallback). |
| **Recent Activity** | ✅ Works | getActivity() calls GET /api/dashboard/activity and maps to list; falls back to mock on 401/error. |
| **Real-time updates** | ⚠️ Polling only | TanStack Query refetch on interval (and window focus); WebSocket is connected but backend never emits dashboard events. |

---

## 1. Does it function fully?

- **Partially.** The page loads and renders. Health check, services, and charts use real or fallback data. Metrics cards can show zeros because the frontend expects fields like `activeLeads`, `totalEmails`, `aiResponses`, `avgResponseTime` while the backend returns a nested structure (`leads.total`, `email.total_emails`, etc.) and does not send AI/response-time in the same form. Recent Activity is always mock data because the frontend does not call `GET /api/dashboard/activity`.

---

## 2. Do features work as promised?

- **Health check / “Your Business Health Check”**  
  - Uses real data: Gmail status, leads count, email counts from timeseries, automation rules.  
  - Scores and recommendations are computed in the frontend from that data.  
  - **Refresh Data** and **Show Debug Info** work.

- **Metric cards**  
  - Backend `/api/dashboard/metrics` returns: `leads.total`, `email.total_emails`, `integrations.gmail_connected`, `performance.response_time`, etc.  
  - It does **not** return `activeLeads`, `totalEmails`, `aiResponses`, or `avgResponseTime` in the shape the Dashboard uses.  
  - So unless the frontend (or apiClient) normalizes this, the cards can show 0 or wrong values.

- **Charts**  
  - Fed by `getDashboardTimeseries()`. Backend returns `timeseries` (e.g. 14 days) with `day`, `leads`, `emails`, `revenue`.  
  - Backend implementation currently uses **random mock** data; no real DB timeseries yet.  
  - Frontend transforms and displays it correctly.

- **Active Services**  
  - Uses `getServices()` → `GET /services` (with health fallback).  
  - Works as intended.

- **Recent Activity**  
  - `getActivity()` in the frontend **does not call the API**; it returns a fixed array.  
  - So the list does **not** reflect real activity, even though `GET /api/dashboard/activity` exists and returns activity (currently mock on backend too).

---

## 3. Does it update in real time / constantly with user actions?

- **Not true real-time.**  
  - **WebSocket:** The frontend connects via Socket.IO and subscribes to `metrics_update`, `services_update`, `activity_update`. The backend **never emits** these events (only `connect` and `subscribe_dashboard` are implemented). So WebSocket does not drive live updates.

- **Polling (TanStack Query):**  
  - Metrics: `refetchInterval: 60 * 1000` (every 1 min).  
  - Activity: every 1 min.  
  - Services: every 5 min.  
  - Refetch on window focus (default) also applies.  
  So the Dashboard **does** update periodically and when the user comes back to the tab, but not instantly when the user performs an action elsewhere (e.g. adding a lead). To feel “constant,” you’d need shorter intervals or server-driven updates (WebSocket/SSE).

---

## Recommended fixes (implemented)

1. **Metrics:** In `apiClient.getMetrics()` the backend response is now normalized to the shape the UI expects: `activeLeads` ← `leads.total`, `totalEmails` ← `email.total_emails`, `avgResponseTime` parsed from `performance.response_time`, and `aiResponses` from `ai.total`. Backend was updated to include `ai.total` from `analytics_events` when available.
2. **Activity:** `getActivity()` now calls `GET /api/dashboard/activity` and maps the response to `ActivityItem[]`; on 401 or error it falls back to mock data.
3. **Real-time (optional):** Either implement backend emits for `metrics_update` / `services_update` / `activity_update` when data changes, or rely on polling (current: every 1–5 min + refetch on window focus).

After these changes, the Dashboard shows real metrics and activity from the API and updates on the configured refetch intervals and on window focus.
