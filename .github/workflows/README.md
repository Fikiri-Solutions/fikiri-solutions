# GitHub Environments (staging / production)

The **CI/CD Pipeline** workflow (`ci-cd.yml`) uses `environment: staging` and `environment: production` on deploy, Docker, and rollback jobs so you can attach **environment-scoped secrets** and **protection rules** (e.g. required reviewers for production).

**Before first deploy:** In the repo go to **Settings → Environments → New environment** and create names **`staging`** and **`production`** (names must match the workflow exactly; GitHub is case-sensitive). Repository-level secrets continue to work; environment secrets override the same name when both exist.

- **staging:** Prefer a dedicated Vercel project; set `VERCEL_PROJECT_ID` in the **staging** environment (or rely on repo secrets until you split). Optional: `RENDER_STAGING_URL` for the post-deploy health check.
- **production:** `VERCEL_PROJECT_ID`, Render IDs, `PRODUCTION_BASE_URL`, `BACKEND_URL`, `FRONTEND_URL`, etc., can live in the **production** environment when you want them scoped there.

Deploys are centralized in `ci-cd.yml`; `backend.yml` and `frontend.yml` run tests (and PR Vercel previews) only.

---

# Workflow Linter Warnings

The **"Context access might be invalid"** (and similar) warnings in `.github/workflows/*.yml` come from the **GitHub Actions** VS Code/Cursor extension. It flags every use of `secrets.*` and `env.*` because it can't verify secret names exist. The workflows are valid; these are false positives.

## Make the warnings go away

**Option A – Disable the extension for this workspace (recommended)**  
1. Open the Extensions view (`Cmd+Shift+X` / `Ctrl+Shift+X`).  
2. Find **"GitHub Actions"** (publisher: GitHub).  
3. Click **Disable (Workspace)**.  
Workflow files will still be valid YAML and run correctly in GitHub; you only turn off this extension’s validation for this repo.

**Option B – Treat workflows as plain YAML**  
`settings.json` already has:

```json
"files.associations": {
  ".github/workflows/*.yml": "yaml",
  "**/.github/workflows/**/*.yml": "yaml"
}
```

If the extension still runs, use **Developer: Reload Window**, or when a workflow file is open click the language label in the status bar (e.g. "GitHub Actions") and switch it to **YAML**.

## Why they “weren’t there before”

- The **GitHub Actions** extension may have been updated and started reporting these checks more often, or  
- It wasn’t installed/enabled before, or  
- Workflow files were previously opened with language mode set to **YAML** instead of **GitHub Actions**.

Your workflows are fine; the 31 items are almost all these extension warnings.
