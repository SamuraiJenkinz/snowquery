---
phase: quick-260621-cgp
plan: "01"
subsystem: sql_generator
tags: [bug-fix, llm, sql, column-hallucination, self-repair, regression]
dependency_graph:
  requires: []
  provides: [column-fidelity-prompt, number-column-few-shot, _is_column_error, one-shot-repair-retry]
  affects: [src/sql_generator.py]
tech_stack:
  added: []
  patterns: [prompt-hardening, few-shot-examples, one-shot-self-repair]
key_files:
  created:
    - tests/test_sql_repair.py
  modified:
    - src/sql_generator.py
decisions:
  - "Narrow column-error classifier (_is_column_error) — only Binder/'not found in FROM clause'/'referenced column'; excludes syntax/type errors — keeps retry surface minimal"
  - "Exactly one retry (not a loop) to avoid runaway LLM calls on persistent hallucination"
  - "repair_context tuple injected as optional arg to generate_sql/_build_prompt rather than a separate code path, keeping surface area small"
metrics:
  duration: "~5 min (capture + verify + commit)"
  completed: "2026-06-21"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 2
---

# Phase quick-260621-cgp Plan 01: SQL Column Hallucination Fix + Self-Repair Retry Summary

**One-liner:** Three-layer defence against NL→SQL column hallucination (prompt rules + `number`-column few-shot + one-shot Binder-error self-repair retry) captured in git with 8 regression tests; full suite 118/118 green.

## What Was Done

This was a **capture task** — the fix already existed as uncommitted working-tree changes. The executor's job was to verify both test targets pass green, then commit atomically.

### Root Cause

A query like "Show me information about incident INC10154562" caused the LLM to emit invented columns (`incident_number` / `incident_id`) instead of the real ServiceNow ID column `number`. DuckDB raised a Binder Error: "Referenced column ... not found in FROM clause."

### Three-Layer Defence (already in working tree, now committed)

1. **SYSTEM_PROMPT rules 9-11 (prompt hardening)**
   - Rule 9 — COLUMN FIDELITY: use ONLY columns present in the Schema; never invent or guess.
   - Rule 10 — Incident IDs (INC...) live in the `number` column (`number = '<ID>'`).
   - Rule 11 — Quote identifiers that contain uppercase, spaces, or dots.

2. **FEW_SHOT_EXAMPLES (number-lookup example prepended)**
   - Added `SELECT * FROM incidents WHERE number = 'INC0010001' LIMIT 1` as the first few-shot pair.

3. **One-shot self-repair retry in `query_with_sql`**
   - `_is_column_error(msg)` — narrow classifier: matches Binder Error + "not found in FROM clause" / "referenced column"; explicitly excludes syntax errors and type errors.
   - `generate_sql` and `_build_prompt` accept an optional `repair_context=(failed_sql, error)` tuple. When present, a repair turn is appended instructing the LLM to use ONLY Schema columns.
   - `query_with_sql` retries ONCE on a column error. On success: clears the error, returns the repaired SQL. On failure: surfaces the corrected-attempt error. Does NOT retry on success or non-column errors.

## Task Execution

| Step | Action | Result |
|------|--------|--------|
| 1 | `PYTHONPATH=. python -m pytest tests/test_sql_repair.py -q` | 8 passed |
| 2 | `PYTHONPATH=. python -m pytest tests/ -q` | 118 passed |
| 3 | `git add src/sql_generator.py tests/test_sql_repair.py && git commit` | commit `a8d7ba0` |

## Commit

**SHA:** `a8d7ba0`
**Message:** `fix(sql): guard against column hallucination + self-repair retry on Binder errors`
**Files:** `src/sql_generator.py` (+97 lines), `tests/test_sql_repair.py` (new, 179 lines)

## Test Coverage

`tests/test_sql_repair.py` — 8 regression tests:
- `_is_column_error` classifier (positive and negative cases)
- Prompt/few-shot guards (COLUMN FIDELITY rule present, `number` few-shot present)
- `repair_context` plumbing in `_build_prompt` and `generate_sql`
- Retry orchestration in `query_with_sql` (repairs on column error, does not retry on success, does not retry on syntax error)

## Deviations from Plan

None — plan executed exactly as written. The fix pre-existed; no code was modified during this task.

## Self-Check: PASSED

- `tests/test_sql_repair.py` exists: FOUND
- `src/sql_generator.py` modified: FOUND
- Commit `a8d7ba0` exists: FOUND (`git show --stat HEAD` confirms 2 files, correct message, correct Co-Authored-By trailer)
- Full suite: 118 passed
- Regression file: 8 passed
- No unrelated files in commit: CONFIRMED (only the 2 named files)
