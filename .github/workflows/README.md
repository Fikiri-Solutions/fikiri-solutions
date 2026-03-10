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
