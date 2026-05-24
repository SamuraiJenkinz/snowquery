# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-24 after v2.2 milestone complete)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** Planning next milestone (v2.3). v2.2 SNOWGREP Visual Revamp shipped 2026-05-24.

## Current Position

Phase: — (no active phase)
Plan: — (no active plan)
Status: v2.2 MILESTONE SHIPPED + ARCHIVED. 36/36 v1 requirements complete; 103/103 tests green; audit passed; archive files in `.planning/milestones/v2.2-{ROADMAP,REQUIREMENTS,MILESTONE-AUDIT}.md`. Ready to start v2.3.
Last activity: 2026-05-24 — `/gsd:complete-milestone v2.2` archived ROADMAP + REQUIREMENTS, updated PROJECT.md + MILESTONES.md, deleted REQUIREMENTS.md (fresh one created by `/gsd:new-milestone`), tagged v2.2.

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

## Session Continuity

Last session: 2026-05-24 — `/gsd:complete-milestone v2.2` archived v2.2 ROADMAP + REQUIREMENTS to `milestones/`, collapsed ROADMAP.md v2.2 entries to `<details>` block, deleted REQUIREMENTS.md (fresh one created by `/gsd:new-milestone`), updated PROJECT.md (Validated requirements + Key Decisions + footer + Codebase state), prepended MILESTONES.md v2.2 entry, reset STATE.md, committed and tagged v2.2.
Stopped at: v2.2 MILESTONE COMPLETE AND ARCHIVED.
Resume file: None
Next: `/gsd:new-milestone` — questioning → research → requirements → roadmap for v2.3.

---
*Last updated: 2026-05-24 after v2.2 milestone archival complete. Ready for `/gsd:new-milestone`.*
