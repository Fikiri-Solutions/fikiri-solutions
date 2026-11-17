# Deploy configs

Deployment-related files that are not day-to-day app source.

| Path | Purpose |
|------|---------|
| [env.staging](env.staging) | Staging environment variable reference (do not commit real secrets) |
| [legacy/app.yaml](legacy/app.yaml) | Legacy Google App Engine config (unused; production is Render + Vercel) |

Keep at repo root (tooling convention): `Dockerfile`, `render.yaml`, `requirements.txt`, `wsgi.py`.
