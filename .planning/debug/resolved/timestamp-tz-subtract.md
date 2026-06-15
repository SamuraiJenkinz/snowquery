---
slug: timestamp-tz-subtract
status: resolved
resolved: 2026-06-15
trigger: |
  SQL execution error: Binder Error: No function matches '-(TIMESTAMP WITH TIME ZONE, TIMESTAMP_NS)'.
  LLM-generated SQL on natural-language query "For incidents that are open is there a pattern that might help to resolve those incidents".
  CSV loaded: C:\Users\taylo\Downloads\ctover30.csv (first time).
created: 2026-06-15
updated: 2026-06-15
---

# Debug Session: timestamp-tz-subtract

## Symptoms

- **expected**: NL question "For incidents that are open is there a pattern that might help to resolve those incidents" should be translated by the LLM into SQL, executed by DuckDB against the loaded incidents table, and return results.
- **actual**: DuckDB rejects the generated SQL with a binder error before execution.
- **error**:
  ```
  SQL execution error: Binder Error: No function matches the given name and argument types
  '-(TIMESTAMP WITH TIME ZONE, TIMESTAMP_NS)'. You might need to add explicit type casts.

  Candidate functions: ... -(TIMESTAMP, TIMESTAMP) -> INTERVAL,
  -(TIMESTAMP WITH TIME ZONE, INTERVAL) -> TIMESTAMP WITH TIME ZONE,
  -(TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE) -> INTERVAL, ...

  LINE 1: ...COUNT(*) as open_count,
          AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - opened_at)) / 86400) as avg_days_open,
          MAX(opened_at)...
  ```
- **timeline**: First time loading `C:\Users\taylo\Downloads\ctover30.csv`; query failed on first run. No prior success on this CSV.
- **reproduction**:
  1. Launch the snow_query app.
  2. Load CSV: `C:\Users\taylo\Downloads\ctover30.csv`.
  3. In the NL chat box, ask: *"For incidents that are open is there a pattern that might help to resolve those incidents"*.
  4. LLM generates SQL containing `EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - opened_at)) / 86400`.
  5. DuckDB binder rejects before execution with the type-mismatch error above.

## Initial Hypothesis Pool (for the debugger to test)

1. **CSV-driven type inference**: DuckDB auto-detected the `opened_at` column as `TIMESTAMP_NS` (nanosecond precision, no TZ) from the CSV format. `CURRENT_TIMESTAMP` returns `TIMESTAMP WITH TIME ZONE`. DuckDB lacks an overload for `TIMESTAMPTZ - TIMESTAMP_NS`. Fix would be at the SQL execution / prompt layer — cast one side, or coerce the loaded column to a TZ-aware timestamp.
2. **LLM prompt issue**: The LLM is told the column is a `TIMESTAMP` but doesn't know it's `TIMESTAMP_NS`. A schema-aware prompt update could help the LLM generate `now()::TIMESTAMP - opened_at::TIMESTAMP` or use `date_diff('day', opened_at, CURRENT_TIMESTAMP)`.
3. **CSV loader configuration**: snow_query may be using `read_csv_auto` without forcing a TZ-aware timestamp type for date columns. A `types={'opened_at': 'TIMESTAMP WITH TIME ZONE'}` override at load time would prevent the mismatch.
4. **Combination**: Best fix is likely a defense-in-depth approach — coerce at load OR rewrite generated SQL via a post-processing pass OR teach the LLM about the precise column type.

## Current Focus

- **hypothesis**: CONFIRMED & RESOLVED — Hypothesis #1 (CSV-driven type inference produces `TIMESTAMP_NS` storage in DuckDB). Fix (A) applied and verified.
- **next_action**: None — session closed. Operator gate: re-upload `ctover30.csv` in the running Streamlit app and re-run the original NL question to confirm in-app.
- **expecting**: In-app NL query "For incidents that are open is there a pattern that might help to resolve those incidents" succeeds end-to-end.
- **reasoning_checkpoint**: Verified by (1) direct DuckDB repro pre-fix → identical Binder Error; (2) full test suite post-fix → 103/103 PASS; (3) end-to-end ctover30.csv repro post-fix → query returns numeric result with no error.
- **tdd_checkpoint**: (TDD mode is OFF per config)

## Evidence

- **2026-06-15 — CSV format confirmed**
  - Checked: `C:\Users\taylo\Downloads\ctover30.csv` row 1–5 `opened_at` values.
  - Found: `"11/14/2025 11:56:00 AM"` style — TZ-naive, MM/DD/YYYY HH:MM:SS AM/PM.
  - Implication: pandas `to_datetime` parses this as TZ-naive `datetime64[ns]`.

- **2026-06-15 — DuckDB version pinned**
  - Checked: `requirements.txt` line `duckdb>=1.1.0`; installed runtime reports `1.4.2`.
  - Found: DuckDB 1.4.2 `typeof(CURRENT_TIMESTAMP)` → `TIMESTAMP WITH TIME ZONE`.
  - Implication: Any version `>=0.9` exhibits this behavior; pinning lower is not a viable workaround.

- **2026-06-15 — Loader path traced**
  - Checked: `src/ingest.py` lines 33–103 (`_detect_column_type`) and 146–266 (`load_csv`).
  - Found: `DATE_FIELDS` in `config.py` (9 entries inc. `opened_at`, `closed_at`, `resolved_at`, etc.) all map to schema string `"TIMESTAMP"`. Line 209 then runs `df[col] = pd.to_datetime(df[col], errors="coerce")` which produces `datetime64[ns]`. Line 246/258 do `CREATE TABLE incidents AS SELECT * FROM temp_df` — no explicit CAST.
  - Implication: DuckDB infers `TIMESTAMP_NS` from `datetime64[ns]` at register time, not the `TIMESTAMP` reported in the schema summary.

- **2026-06-15 — Schema-to-LLM prompt mismatch**
  - Checked: `src/utils.py:120–143` (`format_schema_for_llm`) and `src/sql_generator.py:23–81` (system prompt + few-shot).
  - Found: LLM is told column type is `TIMESTAMP` (the inferred summary value, NOT the actual DuckDB storage type). Few-shot example #4 (line 76) demonstrates the exact failing pattern: `AVG(EXTRACT(EPOCH FROM (resolved_at - opened_at)) / 3600)` — this works between two stored columns, and the LLM generalized it to `CURRENT_TIMESTAMP - opened_at`.
  - Implication: The LLM behaved correctly given the (misleading) schema info. The bug is in the loader, not the prompt.

- **2026-06-15 — Direct reproduction**
  - Checked: minimal repro `pd.to_datetime(['11/14/2025 11:56:00 AM']) → register → CREATE TABLE → SELECT typeof + failing query`.
  - Found:
    - `df['opened_at'].dtype` = `datetime64[ns]`
    - `DESCRIBE incidents` reports column type = `TIMESTAMP_NS`
    - `typeof(CURRENT_TIMESTAMP)` = `TIMESTAMP WITH TIME ZONE`
    - Failing query raises verbatim: `Binder Error: No function matches the given name and argument types '-(TIMESTAMP WITH TIME ZONE, TIMESTAMP_NS)'`
  - Implication: Root cause definitively confirmed.

- **2026-06-15 — Fix (A) validated**
  - Checked: same repro, but `CREATE TABLE incidents AS SELECT * EXCLUDE(opened_at), CAST(opened_at AS TIMESTAMP) AS opened_at FROM temp_df`.
  - Found: `DESCRIBE` reports `TIMESTAMP` (no `_NS`). Failing query now returns `(152.34...,)` successfully.
  - Implication: Casting date columns to plain `TIMESTAMP` at load time fixes the bug with no SQL/LLM changes.

- **2026-06-15 — Fix (D) DISPROVEN**
  - Checked: `SET TimeZone='UTC'` then re-run failing query.
  - Found: `typeof(CURRENT_TIMESTAMP)` is still `TIMESTAMP WITH TIME ZONE`; Binder Error still raised.
  - Implication: Session-level TZ setting cannot rescue this — DuckDB's `CURRENT_TIMESTAMP` always returns TZ-aware.

- **2026-06-15 — Fix (C) viable but fragile**
  - Checked: rewriting the SQL to `now()::TIMESTAMP - opened_at` succeeds.
  - Found: Works, but requires LLM-output post-processing (regex or SQL AST walk) — adds a fragile surface area and only fixes one pattern of many possible mismatches.
  - Implication: Not the lowest-risk fix; would need to handle many variants (`now()`, `current_timestamp`, `transaction_timestamp()`, etc.).

## Eliminated

- **Hypothesis #2 (LLM prompt issue)**: The LLM-generated SQL is reasonable for what it was told. Schema string says `TIMESTAMP` and the few-shot demonstrates `EXTRACT(EPOCH FROM (col1 - col2))`. Even if we improve the prompt to say `TIMESTAMP_NS`, the LLM would still likely emit `CURRENT_TIMESTAMP - col` and we'd still need to teach it about the `now()::TIMESTAMP` workaround. Higher complexity, lower reliability than fixing the loader. Disproven by Evidence #6 (Fix A works in isolation).
- **Hypothesis #4 (Combination defense-in-depth)**: While adding prompt hints + post-processor + loader fix would be most robust, scope creep raises blast radius and yields no additional safety beyond Fix (A) once the underlying storage type is correct. Eliminated for now in favor of single-surface fix.
- **Session-level fix via `SET TimeZone`**: Proven not to help (Evidence #7).

## Resolution

- **root_cause**: `src/ingest.py:209` produces `datetime64[ns]` via `pd.to_datetime(..., errors="coerce")`, which DuckDB 1.4.2 stores as `TIMESTAMP_NS` when the DataFrame is registered and materialized at lines 246/258 (`CREATE TABLE ... AS SELECT * FROM temp_df`). LLM-generated SQL uses `CURRENT_TIMESTAMP - opened_at`, and DuckDB has no `-(TIMESTAMP WITH TIME ZONE, TIMESTAMP_NS)` overload → Binder Error before execution.
- **fix**: Applied Fix (A) — Coerce at load time. Added a `_ctas_select_clause(df, schema)` helper in `src/ingest.py` that builds a SELECT-list wrapping every `TIMESTAMP`-schema column in `CAST("col" AS TIMESTAMP) AS "col"` (downcasts `TIMESTAMP_NS` → microsecond `TIMESTAMP`). Used at both materialisation sites: the replace-mode CTAS (~line 258) and the append-mode CTAS (~line 246). Column identifiers are double-quoted with internal `"` escaped via `""` to be safe across arbitrary CSV headers. No prompt, executor, or LLM changes. `CAST` is idempotent — re-loading a table that's already `TIMESTAMP` is a no-op.
- **verification**: All checks PASS.
  - `PYTHONPATH=. python -m pytest tests/ -q` → **103 passed, 1 warning in 36.84s** (no regressions; matches v2.2 baseline).
  - End-to-end repro against `C:\Users\taylo\Downloads\ctover30.csv`:
    - `DESCRIBE incidents` — every TIMESTAMP column now reports `TIMESTAMP` (previously `TIMESTAMP_NS`).
    - Failing pattern `AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - opened_at)) / 86400)` returns `(open_count=3, avg_days_open≈118.77, most_recent_open=2026-04-29 00:00:41)`. **No Binder Error.**
    - Regression: `opened_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')` → 12 rows, PASS.
    - Regression: `CAST(opened_at AS DATE) = CURRENT_DATE` → 0 rows, PASS (no error).
  - The original NL question "For incidents that are open is there a pattern that might help to resolve those incidents" will now succeed in the running Streamlit app once the user re-uploads ctover30.csv.
- **files_changed**:
  - `src/ingest.py` — added `_ctas_select_clause(...)` helper after `_get_sample_value`; modified both CTAS sites in `load_csv` to use the cast-aware SELECT clause.
