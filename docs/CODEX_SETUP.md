# Codex Setup Guide - Matching Cursor's Access Level

**Purpose**: Configure Codex to have the same level of access and context as Cursor AI assistant.

---

## Quick Setup

**Important**: Codex does NOT automatically ingest `.cursorrules` or other rule files. You must explicitly ask Codex to read them.

### 1. Point Codex to the Same Rule Files

**Action Required**: Explicitly ask Codex to read these files at the start of each session:

Codex should read the same rule files that Cursor uses:

**Primary Rules:**
- `.cursorrules` - Main rulepack (architecture, AI pipelines, security, performance)
- `COORDINATION.md` - Multi-tool coordination guidelines
- `SIMPLICITY_RULE.md` - Code simplicity guidelines

**Additional Context:**
- `.cursor/rules` - Cursor-specific operational rules (Codex can reference these)
- `docs/SYSTEM_ARCHITECTURE.md` - System architecture overview
- `docs/CRUD_RAG_ARCHITECTURE.md` - CRUD and RAG flow documentation

### 2. Configure Codex Workspace Context

**Note**: Codex may not support `config.json` files. The most reliable approach is explicit file reads.

#### Option A: Explicit File Reads (Recommended)

At the start of each Codex session, explicitly ask Codex to read:

```
Please read these files to understand the project:
1. .cursorrules - Main rulepack
2. COORDINATION.md - Multi-tool coordination  
3. SIMPLICITY_RULE.md - Code simplicity guidelines
4. docs/SYSTEM_ARCHITECTURE.md - System architecture
```

#### Option B: Codex Configuration File (if supported)

Create `.codex/config.json` or similar (may not be read automatically):

```json
{
  "workspace": {
    "root": "/Users/mac/Downloads/Fikiri",
    "rules": [
      ".cursorrules",
      "COORDINATION.md",
      "SIMPLICITY_RULE.md"
    ],
    "contextFiles": [
      "docs/SYSTEM_ARCHITECTURE.md",
      "docs/CRUD_RAG_ARCHITECTURE.md",
      "docs/PRODUCTION_READINESS_GAPS.md",
      "README.md"
    ]
  }
}
```

#### Option C: Codex Initial Prompt/Context

When starting a Codex session, provide this context:

```
You are working on the Fikiri Solutions codebase. 

CRITICAL: Read these files first:
1. .cursorrules - Full rulepack (architecture, AI pipelines, security)
2. COORDINATION.md - Multi-tool coordination (Cursor + Codex)
3. SIMPLICITY_RULE.md - Code simplicity guidelines

Before making changes:
- Check git status to see recent changes
- Read existing files before editing
- Follow existing patterns
- Coordinate on API contract changes

Domain boundaries:
- core/ → shared utilities
- services/ → business logic  
- integrations/ → external connectors
- crm/ → CRM models (crm/service.py is canonical)
- email_automation/ → email pipeline
- frontend/ → React app

Both Codex and Cursor work on this codebase. Always check git status before editing.
```

### 3. Ensure Codex Has File Access

Codex needs read/write access to:

**All Code Directories:**
- `core/` - Shared utilities
- `services/` - Business logic
- `integrations/` - External connectors
- `crm/` - CRM models
- `email_automation/` - Email pipeline
- `analytics/` - Reporting
- `routes/` - API routes
- `frontend/src/` - React frontend
- `tests/` - Test files

**Documentation:**
- `docs/` - All documentation files
- `.cursorrules` - Main rules
- `COORDINATION.md` - Coordination guide

**Configuration:**
- `app.py` - Flask app entry
- `requirements.txt` - Python dependencies
- `package.json` - Frontend dependencies
- `.env` (if Codex needs to read env template)

### 4. Codex-Specific Configuration

#### If Codex Uses a Config File

Create `.codexrules` (similar to `.cursorrules`):

```markdown
# Codex Configuration for Fikiri Solutions

This file ensures Codex follows the same rules as Cursor.

## Source of Truth
- Read .cursorrules first (main rulepack)
- Read COORDINATION.md for multi-tool coordination
- Read SIMPLICITY_RULE.md for code guidelines

## Before Every Edit
1. Run: git status (check recent changes)
2. Read the file you're about to edit
3. Follow existing patterns
4. Minimal scope changes

## Domain Boundaries
- core/ → shared utilities
- services/ → business logic
- integrations/ → external connectors
- crm/ → CRM (crm/service.py is canonical)
- email_automation/ → email pipeline
- frontend/ → React app

## Coordination
- Check git status before editing
- Coordinate on API contract changes
- Don't overwrite in-progress work
```

#### If Codex Uses Environment Variables

Set these in Codex's environment:

```bash
CODEX_WORKSPACE_ROOT=/Users/mac/Downloads/Fikiri
CODEX_RULES_FILE=.cursorrules
CODEX_COORDINATION_FILE=COORDINATION.md
CODEX_ARCHITECTURE_FILE=docs/SYSTEM_ARCHITECTURE.md
```

### 5. Verify Codex Access

Test that Codex can:

✅ **Read rule files:**
```bash
# Codex should be able to read:
- .cursorrules
- COORDINATION.md
- SIMPLICITY_RULE.md
```

✅ **Read code files:**
```bash
# Codex should access:
- core/*.py
- services/*.py
- routes/*.py
- frontend/src/**/*
- tests/**/*
```

✅ **Read documentation:**
```bash
# Codex should access:
- docs/**/*.md
- README.md
```

✅ **Check git status:**
```bash
# Codex should run:
git status
git diff
```

### 6. Codex Initialization Checklist

When starting a Codex session:

- [ ] Codex can read `.cursorrules`
- [ ] Codex can read `COORDINATION.md`
- [ ] Codex can read `docs/SYSTEM_ARCHITECTURE.md`
- [ ] Codex can access all code directories
- [ ] Codex can run `git status`
- [ ] Codex understands domain boundaries
- [ ] Codex knows to coordinate with Cursor

### 7. Codex-Specific Best Practices

**Before Making Changes:**
1. **Always check git status first:**
   ```
   git status
   git diff
   ```

2. **Read the file you're editing:**
   - Understand existing patterns
   - Follow the same style
   - Don't introduce new patterns

3. **Check COORDINATION.md:**
   - See if Cursor is working on related files
   - Coordinate on API changes
   - Avoid conflicts

**When Editing:**
- Minimal scope (1-3 files per task)
- Preserve API contracts
- Follow `.cursorrules` guidelines
- Match existing code style

**After Making Changes:**
- Verify tests still pass
- Check for breaking changes
- Document if needed

---

## Troubleshooting

### Codex Can't Read Rule Files

**Solution:**
- Ensure Codex workspace root is set correctly
- Check file permissions
- Verify file paths are relative to workspace root

### Codex Doesn't Follow Rules

**Solution:**
- Explicitly reference `.cursorrules` in Codex prompt
- Provide rule file contents in initial context
- Use Codex's "include file" feature if available

### Codex Conflicts with Cursor

**Solution:**
- Always check `git status` before editing
- Coordinate via comments or documentation
- Use feature branches for larger changes

### Codex Missing Context

**Solution:**
- Include key documentation files in Codex context
- Reference architecture docs when needed
- Use Codex's file inclusion features

---

## Example: Codex Session Setup

**Initial Prompt for Codex (Copy-Paste This):**

```
I'm working on the Fikiri Solutions codebase. 

CRITICAL: Please read these files first (I need you to explicitly read them):
1. .cursorrules - Main rulepack (architecture, security, performance rules)
2. COORDINATION.md - Multi-tool coordination (Cursor + Codex)
3. SIMPLICITY_RULE.md - Code simplicity guidelines
4. docs/SYSTEM_ARCHITECTURE.md - System architecture overview

After reading, please:
1. Run: git status (to see recent changes)
2. Read: core/minimal_config.py (to verify file access)

Key rules from .cursorrules:
- Check git status before editing
- Follow .cursorrules guidelines
- Coordinate with Cursor on API changes
- Minimal scope changes (1-3 files per task)
- Preserve existing patterns

Domain boundaries:
- core/ → shared utilities
- services/ → business logic
- integrations/ → external connectors
- crm/ → CRM (crm/service.py canonical)
- email_automation/ → email pipeline
- frontend/ → React app

Before making any changes, always:
1. Run: git status
2. Read the file(s) you'll edit
3. Follow existing patterns
```

---

## Summary

To give Codex the same access as Cursor:

1. ✅ **Point Codex to `.cursorrules`** - Main rulepack
2. ✅ **Point Codex to `COORDINATION.md`** - Multi-tool coordination
3. ✅ **Give Codex access to all code directories** - Same as Cursor
4. ✅ **Enable git status checks** - Avoid conflicts
5. ✅ **Include architecture docs** - System context
6. ✅ **Set workspace root correctly** - File path resolution

**Key Difference:** Codex may need explicit file paths/references, while Cursor automatically reads `.cursorrules` and workspace context.

---

*Last updated: Feb 2026*
