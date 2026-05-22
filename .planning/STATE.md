# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** v2.1 milestone shipped 2026-05-22. Planning next milestone — run `/gsd:new-milestone` to define scope.

## Current Position

Phase: None active
Plan: Not started
Status: Ready to plan next milestone
Last activity: 2026-05-22 — v2.1 milestone complete (5 phases, 20 plans, 91 tests). All requirements shipped. Only pre-prod gate is operator-run smoke against staging MGTI gateway.

Progress: v2.1 complete — [██████████] 100% (20/20 plans across all 5 phases)

## Open Pre-Prod Gates

- **SMK-05 live smoke run against staging gateway** (`python scripts/smoke_llm.py --provider both --verbose`) — artifact is structurally verified; live execution requires staging Anthropic + Azure credentials operator-side. Must run before production deploy. Documented in `.planning/milestones/v2.1-MILESTONE-AUDIT.md` §7, `README.md` (Smoke Test section), and `USER_GUIDE.md` (First-Time Anthropic Setup Checklist).
- **Manual UI sanity click-through** — 30-second operator ritual (sidebar selectbox + caption + warning + disabled chat_input). Covered programmatically by Phase 5 acceptance gate; manual standard PR-review responsibility.
- **X-Correlation-Id echo observation** (`tests/manual/observe_correlation_echo.py`) — observation step, not runtime dependency. To be combined with the smoke gate run when staging credentials are available.

## Accumulated Context

### Decisions

Full decision log in PROJECT.md "Key Decisions" table (15 decisions with outcomes marked ✓ Good / ⚠️ Pending / — Pending).

Per-plan decisions logged in `.planning/milestones/v2.1-ROADMAP.md` (archived) and phase-level SUMMARY.md files at `.planning/phases/01-*/...` through `05-*/...`.

### Resolved Blockers

All Phase 1-5 blockers resolved at milestone close:
- Phase 2 KNOWN DEBT (LLMAuthError hardcoded Azure remediation) → resolved by Phase 3 per-provider dispatch in `_compat.py`
- Phase 4 SC #5 (live smoke run) → deferred to operator pre-prod gate (pre-authorized; not a milestone blocker)
- Phase 5 mid-session-switch provenance loss → resolved by `_render_provenance_caption` reading from stored dict (AST-locked invariant)

### Open Blockers/Concerns

None for the milestone. Only the operator-run pre-prod smoke gate remains (above).

## Session Continuity

Last session: 2026-05-22 — v2.1 milestone completion ritual.
Stopped at: Milestone v2.1 archived, ROADMAP.md collapsed, REQUIREMENTS.md deleted (fresh for next milestone), PROJECT.md evolved to brownfield format with Current State + Next Milestone Goals, git tag v2.1 created.
Resume file: None — next session starts with `/gsd:new-milestone`.

---
*Last updated: 2026-05-22 after v2.1 milestone completion*
