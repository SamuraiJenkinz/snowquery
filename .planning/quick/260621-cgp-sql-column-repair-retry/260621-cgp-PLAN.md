---
phase: quick-260621-cgp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [src/sql_generator.py, tests/test_sql_repair.py]
autonomous: true
requirements: [QUICK-260621-CGP]
must_haves:
  truths:
    - "A query naming an incident ID (INC...) generates SQL matching the `number` column, not an invented column"
    - "When the LLM emits a non-existent column, the DuckDB Binder Error triggers exactly ONE self-repair retry"
    - "Syntax/type errors and successful queries do NOT trigger a retry"
    - "tests/test_sql_repair.py passes (8 tests) and the full suite stays green at 118"
  artifacts:
    - path: "src/sql_generator.py"
      provides: "Column-fidelity prompt rules (9-11), number-lookup few-shot, _is_column_error classifier, repair_context plumbing, one-shot retry in query_with_sql"
      contains: "_is_column_error"
    - path: "tests/test_sql_repair.py"
      provides: "8 regression tests: classifier, prompt/few-shot guards, repair-prompt construction, retry orchestration"
      contains: "test_query_with_sql_repairs_on_column_error"
  key_links:
    - from: "src/sql_generator.py query_with_sql"
      to: "_is_column_error + generate_sql(repair_context=...)"
      via: "one-shot retry on column error"
      pattern: "_is_column_error\\(error\\)"
---

<objective>
Capture and commit the already-applied fix for NL→SQL column-name hallucination.

Root cause: A query like "Show me information about incident INC10154562" led the LLM to invent non-existent columns (`incident_number` / `incident_id`), producing a DuckDB "Binder Error: Referenced column ... not found in FROM clause". The real ServiceNow ID column is `number`.

The fix is a three-layer defence, ALREADY present and uncommitted in the working tree:
1. **Prompt hardening** — SYSTEM_PROMPT rules 9-11: COLUMN FIDELITY (use ONLY columns in the Schema; never invent/guess), ServiceNow incident IDs (INC...) live in `number` (`number = '<ID>'`), and quote identifiers with uppercase/spaces/dots.
2. **Few-shot** — prepended a `number` lookup example (`SELECT * FROM incidents WHERE number = 'INC0010001' LIMIT 1`).
3. **One-shot self-repair retry** — `_is_column_error(msg)` (narrow: Binder / "not found in FROM clause" / "referenced column"; excludes syntax/type errors); `generate_sql` + `_build_prompt` accept optional `repair_context=(failed_sql, error)` that appends a repair turn instructing ONLY-Schema columns; `query_with_sql` retries ONCE on a column error, adopts the repaired SQL (clears error on success, surfaces the corrected-attempt error on failure), and does NOT retry on success or non-column errors.

Purpose: Lock the regression with tests and record the fix in git history. This is a CAPTURE task — do NOT re-implement.
Output: Verified green suite + one atomic commit.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@src/sql_generator.py
@tests/test_sql_repair.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify the regression suite, then commit the fix atomically</name>
  <files>src/sql_generator.py, tests/test_sql_repair.py</files>
  <action>
The fix and tests already exist in the working tree — do NOT modify src/sql_generator.py or tests/test_sql_repair.py.

Step 1 — run the new regression file in isolation:
`PYTHONPATH=. python -m pytest tests/test_sql_repair.py -q`
Expect 8 passed. If any fail, STOP and report the failure — do not edit to force green; the as-built behavior is the source of truth.

Step 2 — run the full suite to confirm no parity/other regressions (the SYSTEM_PROMPT and FEW_SHOT_EXAMPLES changed, but Phase 2 parity fixtures under tests/fixtures/parity/ still pass):
`PYTHONPATH=. python -m pytest tests/ -q`
Expect 118 passed.

Step 3 — commit ONLY the two changed files atomically (do not sweep unrelated working-tree noise such as the new top-level .pdf/.xlsx/.html/.py scratch files, deploy/, docs/, or .planning/design-mockups/). Stage explicitly by path:
`git add src/sql_generator.py tests/test_sql_repair.py`
Then commit with a message capturing root cause + the 3-layer defence:

  fix(sql): stop NL->SQL column hallucination via prompt + few-shot + one-shot repair retry

  A query naming an incident ID (e.g. INC10154562) made the LLM invent
  non-existent columns (incident_number/incident_id) -> DuckDB Binder Error
  "Referenced column ... not found in FROM clause". The real ServiceNow ID
  column is `number`.

  Three-layer defence:
  - SYSTEM_PROMPT rules 9-11: COLUMN FIDELITY (use ONLY Schema columns,
    never invent/guess), incident IDs live in `number` (number = '<ID>'),
    quote identifiers with uppercase/spaces/dots.
  - FEW_SHOT_EXAMPLES: prepend a `number` lookup example.
  - One-shot self-repair: _is_column_error() classifies retryable Binder/
    column errors (excludes syntax/type); generate_sql/_build_prompt accept
    repair_context=(failed_sql, error); query_with_sql retries ONCE on a
    column error, adopts the repaired SQL, and does NOT retry on success or
    non-column errors.

  Regression: tests/test_sql_repair.py (8 tests). Full suite 118/118 green.

  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  </action>
  <verify>
    <automated>PYTHONPATH=. python -m pytest tests/test_sql_repair.py tests/ -q</automated>
  </verify>
  <done>tests/test_sql_repair.py shows 8 passed; full suite shows 118 passed; a single commit contains exactly src/sql_generator.py and tests/test_sql_repair.py with the root-cause + 3-layer message.</done>
</task>

</tasks>

<verification>
- `PYTHONPATH=. python -m pytest tests/test_sql_repair.py -q` → 8 passed
- `PYTHONPATH=. python -m pytest tests/ -q` → 118 passed
- `git show --stat HEAD` lists only src/sql_generator.py and tests/test_sql_repair.py
</verification>

<success_criteria>
- Regression file passes (8 tests); full suite green at 118.
- One atomic commit captures the root cause (column hallucination; real column is `number`) and the 3-layer defence (prompt + few-shot + one-shot repair retry).
- No unrelated working-tree files swept into the commit.
</success_criteria>

<output>
Create `.planning/quick/260621-cgp-sql-column-repair-retry/260621-cgp-SUMMARY.md` when done.
</output>
