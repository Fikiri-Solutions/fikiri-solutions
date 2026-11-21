# Codex setup

Codex does not load `.cursorrules`, `AGENTS.md`, or `.cursor/rules/*.mdc` by itself. Cursor does load `.cursorrules` and `AGENTS.md`. Paste the prompt below at the start of a Codex session.

Workspace root is this repository. Do not use `/Users/mac/Downloads/Fikiri`.

## Session prompt

```
Read these files before editing:
1. .cursorrules
2. AGENTS.md
3. COORDINATION.md
4. docs/REGRESSION_TESTING.md

Then read the one .cursor/rules/*.mdc file COORDINATION.md lists for the area you will edit.
Do not read every rule file.

Check git status before editing. Follow the existing code.
Codex does not auto-attach Cursor globs. Open the subsystem file yourself.
```

## What each file is for

| File | Why Codex reads it |
|---|---|
| `.cursorrules` | Security, boundaries, production database, links to subsystem rules |
| `AGENTS.md` | How this app starts and the unit-gate command |
| `COORDINATION.md` | Which subsystem file to open, and how not to collide with Cursor |
| `docs/REGRESSION_TESTING.md` | Quick fix, feature, critical change, release |
| `.cursor/rules/<area>.mdc` | The area being edited |

`docs/SYSTEM_ARCHITECTURE.md` is optional background. It is not required for every session.

## Check

- Codex can read `.cursorrules`, `AGENTS.md`, and `COORDINATION.md`.
- The subsystem file for the task was read.
- `git status` was checked before the edit.
