# Regression testing policy

Every change must make the app **strictly better or neutral** — never worse silently.

## Full suite (required before "done")

From repo root:

```bash
pytest tests/ -m "not contract and not integration" -q
cd frontend && npx vitest run
```

Run both on **every** feature, fix, or refactor — not only tests near edited files.

## When a bug is found

1. Reproduce (failing test or minimal steps).
2. Fix root cause.
3. Add a **regression test** in the same change.
4. Re-run full backend + frontend suites.

## Quality gate

For queues, workflows, and automation, also follow [CURSOR_QUALITY_GATE.md](./CURSOR_QUALITY_GATE.md) (contract table, state transitions, failure branches).

## Cursor / agent enforcement

- `.cursor/rules` — section 11
- `.cursorrules` — section 9
- `AGENTS.md` — Regression testing summary
