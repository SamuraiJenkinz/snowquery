# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-24 after v2.2 milestone complete)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** Planning next milestone (v2.3). v2.2 SNOWGREP Visual Revamp shipped 2026-05-24.

## Current Position

Phase: — (no active phase)
Plan: — (no active plan)
Status: v2.2 MILESTONE SHIPPED + ARCHIVED. 36/36 v1 requirements complete; 103/103 tests green; audit passed; archive files in `.planning/milestones/v2.2-{ROADMAP,REQUIREMENTS,MILESTONE-AUDIT}.md`. Ready to start v2.3. (Hotfix Quick-001 + Quick-002 2026-06-03 chased Bedrock contract tightening: Accept header + sampling-param omission.)
Last activity: 2026-06-22 — Quick task 006: added an EXPORT SUMMARY button beside EXPORT CSV / EXPORT HTML in `display_results`. `build_html_report` gained a keyword-only `summary_only` flag that omits the results table and SQL (keeps question + executive summary + provenance; notes absence if no summary). The export row switches to 3 columns only when a summary exists. +3 tests → 121/121 green. Commit `d2f4e2d`, pushed to `samurai`.

Earlier 2026-06-21 — Quick task 005: guarded NL→SQL column hallucination. "Show me information about incident INC10154562" made the LLM invent `incident_number`/`incident_id` (real ID column is `number`), producing a DuckDB Binder Error. Three-layer fix in `src/sql_generator.py`: (1) SYSTEM_PROMPT rules 9-11 — use ONLY Schema columns, incident IDs live in `number`, quote special identifiers; (2) few-shot `number = '<ID>'` lookup example; (3) one-shot self-repair retry — `_is_column_error` + `repair_context` feeds the failed SQL + error back to the model, `query_with_sql` retries once on a column error (not on success/syntax errors). +8 tests → 118/118 green. Commit `a8d7ba0`. (Same day: quick-003 EXPORT HTML `befe0f9`; quick-004 render-parity `3dcd200`.)

Progress:

```
v2.1 ✅ SHIPPED 2026-05-22 (Phases 1-5, 20 plans, 91 tests)
v2.2 ✅ SHIPPED 2026-05-24 (Phases 6-12, 17 plans, +12 visual regression tests → 103 total)
v2.3 📋 Not yet started — run /gsd:new-milestone to define scope and requirements
```

## v2.1 Open Pre-Prod Gates (carried forward)

- **SMK-05 live smoke run against staging gateway** (`python scripts/smoke_llm.py --provider both --verbose`) — pre-authorized operator gate before production deploy. Documented in `.planning/milestones/v2.1-MILESTONE-AUDIT.md` §7. Carries forward into v2.3.

## v2.2 Carry-Forward Reference

For v2.3 planning, the canonical v2.2 references are:

- **Roadmap:** `.planning/milestones/v2.2-ROADMAP.md`
- **Requirements:** `.planning/milestones/v2.2-REQUIREMENTS.md`
- **Audit:** `.planning/milestones/v2.2-MILESTONE-AUDIT.md`
- **Design system:** `loro-piana-aesthetic` skill at `C:\Users\taylo\.claude\skills\loro-piana-aesthetic\`
- **Single source of truth for hex values:** `src/ui/css.py` (`LORO_PIANA_TOKENS` dict + `LORO_PIANA_CSS` string)
- **Single source of truth for chart palette:** `src/ui/altair_theme.py:42-48` (`VIBRANT_PALETTE`)
- **AST-locked v2.1 invariant:** `_render_provenance_caption(provider, model)` MUST NOT read `st.session_state`; regression test in `tests/test_phase5_ui.py`

## v2.3 Candidate Areas (from v2.1 + v2.2 backlogs)

See `PROJECT.md` § Next Milestone Goals for the full list. High-level groupings:

- **v2.1 resilience backlog** — retry-with-backoff on `LLMTransientError`, per-call-site model selection, Opus 4.7 with adaptive thinking (pending Hubble entitlement), connection-test button.
- **v2.2 visual backlog** — THM-01 theme toggle, THM-02 dark-mode luxury, MIC-01/02 microinteractions, CHT-01 sparklines, CHT-02 crossfilter.
- **Tech debt** — add `[tool.pytest.ini_options]\npythonpath = ["."]` to `pyproject.toml` so bare `pytest tests/` works without `PYTHONPATH=.` prefix; migrate three remaining `st.error()` callsites + legacy `class="query-box"` div if richer treatment is desired.

## Accumulated Context

### Decisions (recent — see PROJECT.md Key Decisions table for full log)

- v2.2 final: Phase 12 (`doc-accuracy-cleanup`) closes audit-surfaced doc-drift before archival; re-audit → `passed` promotion. Pattern established for future milestones: audit → close-gaps → re-audit before `/gsd:complete-milestone`.
- v2.2 final: `src/ui/css.py` is the single source of truth for Loro Piana hex values; `src/ui/altair_theme.py:42-48` `VIBRANT_PALETTE` is the canonical chart data palette. All future code reads from these — no hardcoded hex literals elsewhere.
- v2.2 final: pytest invocation contract is `PYTHONPATH=. python -m pytest tests/ -q` until `pyproject.toml` adds `[tool.pytest.ini_options] pythonpath = ["."]`. Documented as tech debt for v2.3.

### Resolved Blockers

(None active — v2.2 audit cleared all 4 doc-drift items via Phase 12)

### Open Blockers/Concerns

(None for v2.3 start)

### Quick Tasks Completed

| #   | Description                                                                       | Date       | Commit    | Directory                                                                                                |
| --- | --------------------------------------------------------------------------------- | ---------- | --------- | -------------------------------------------------------------------------------------------------------- |
| 001 | Add `Accept: application/json` header to Anthropic MGTI (Bedrock req)             | 2026-06-03 | `facfefa` | [001-fix-anthropic-mgti-accept-header](./quick/001-fix-anthropic-mgti-accept-header/)                    |
| 002 | Omit `temperature`/`top_p`/`top_k` for ALL Bedrock models (not just opus-4-7)     | 2026-06-03 | `41869ad` | [002-omit-sampling-params-all-bedrock-models](./quick/002-omit-sampling-params-all-bedrock-models/)      |
| 003 | Add self-contained Loro Piana HTML report export (EXPORT HTML beside EXPORT CSV)   | 2026-06-21 | `befe0f9` | [260621-aj0-html-export-query-report](./quick/260621-aj0-html-export-query-report/)                      |
| 004 | Fix assistant-message HTML render parity (history path missing `unsafe_allow_html`) | 2026-06-21 | `3dcd200` | [260621-c28-fix-assistant-message-html-render-parity](./quick/260621-c28-fix-assistant-message-html-render-parity/) |
| 005 | Guard NL→SQL column hallucination + self-repair retry on DuckDB Binder errors     | 2026-06-21 | `a8d7ba0` | [260621-cgp-sql-column-repair-retry](./quick/260621-cgp-sql-column-repair-retry/)                        |
| 006 | Add summary-only HTML export button (EXPORT SUMMARY beside CSV/HTML)               | 2026-06-22 | `d2f4e2d` | [260622-7t4-summary-only-export-button](./quick/260622-7t4-summary-only-export-button/)                  |

## Session Continuity

Last session: 2026-06-21 — `/gsd:quick` 003 + 004 + 005, all NON-worktree (changes pre-existed in the working tree). Quick-003: EXPORT HTML feature (commit `befe0f9`) — `build_html_report` in `src/utils.py` renders a self-contained Loro Piana report; `generate_export_filename` gained an `extension` arg; `app.py` renders EXPORT CSV + EXPORT HTML in `st.columns(2)`. Quick-004: assistant-message render parity (commit `3dcd200`) — history-render path was missing `unsafe_allow_html=True`, leaking raw `<span>` markup on rerun; AST-lock test added. Quick-005: NL→SQL column-hallucination guard + one-shot self-repair retry (commit `a8d7ba0`) — prompt/few-shot teach the `number` ID column, `query_with_sql` retries once on a DuckDB Binder error. 118/118 tests green. All six commits PUSHED to the personal remote `samurai` (`https://github.com/SamuraiJenkinz/snowquery.git`); `samurai/main` == local `main` == `e666a3b`.
Stopped at: Quick-003/004/005/006 committed on `main` and pushed to `samurai`. The corporate `origin` remote (`mmctech/snow_query`) has been REMOVED from this repo and is no longer a push target — push only to `samurai`. Prior live-smoke gate against MGTI sonnet-4-5 still open — operator gate (untouched; no LLM-contract surface changed).
Resume file: None
Next: `/gsd:new-milestone` for v2.3.

> **Push target:** Personal remote `samurai` (`SamuraiJenkinz/snowquery`) ONLY. The MMC corporate remote was removed — do not re-add or push to it.

---
*Last updated: 2026-06-21 after quick tasks 003 (HTML export) + 004 (render-parity fix) + 005 (SQL column-repair retry). All commits pushed to personal remote `samurai`; corporate remote removed. Ready for `/gsd:new-milestone`.*
