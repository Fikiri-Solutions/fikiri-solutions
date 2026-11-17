# Fikiri work lookbook (dev / source)

Production path: **`frontend/public/work/`** → `https://fikirisolutions.com/work/`

Edit here or under `frontend/public/work/`, then keep both in sync before deploy.

Production routing: `/work` redirects to `/work/` (needed for relative assets); middleware treats `/work` as static so it is not SPA-404’d.

## Local preview

```bash
python3 -m http.server 8765 --directory static/lookbook
# or: cd frontend && npm run dev → http://localhost:5174/work/
```
