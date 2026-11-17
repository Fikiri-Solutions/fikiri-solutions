# Fikiri work lookbook

Static portfolio at **`/work/`** on fikirisolutions.com.

Share URL: `https://fikirisolutions.com/work/`

Keep in sync with `static/lookbook/`.

Routing:
- `frontend/vercel.json`: `/work` → `/work/`; `/work/` → `/work/index.html` (SPA catch-all excluded)
- `frontend/middleware.ts` + `spaKnownPaths`: `/work` is a static surface, not an SPA 404
