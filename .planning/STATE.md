# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** Phase 1 — Abstraction Seam

## Current Position

Phase: 1 of 5 (Abstraction Seam)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-05-19 — Completed 01-01-PLAN-01-package-skeleton.md

Progress: [█░░░░░░░░░] 7% (1/15 plans estimated)

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 3 min
- Total execution time: 3 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Abstraction Seam | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 01-01 (3 min)
- Trend: baseline established

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 1: Provider abstraction layer (`abc.ABC` + two adapters) over per-call `if` branches — interface drift is the dominant pitfall to prevent
- Phase 2: Parity-first refactor — Azure extraction must produce byte-identical output to today before Anthropic is introduced
- Phase 3: Anthropic adapter speaks native MGTI shape, no OpenAI-translation middleware
- Phase 4: Strict-tools mode for `classify_intent` only — `chart_requested`/`chart_type` stay out of the LLM schema (heuristic-populated)
- Phase 5: Default provider stays `azure_openai` so upgrade is byte-identical for existing deployments

Decisions from 01-01 (package skeleton):
- Flat error hierarchy (no retryable grouping) — add in Phase 5 if retry logic lands
- `complete()` takes `messages: list[dict]` (Azure-native shape) — Anthropic adapter extracts system internally
- `ClassificationResultV1` excludes `chart_requested`/`chart_type` — heuristic-only fields (TOOL-03)
- `ToolCall.raw_response` uses `field(repr=False)` — debug payload never leaks into repr/logs

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 4: MGTI proxy strict-tools support is "works as of 2026-05-12 but undocumented" — `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch must be verified against staging before relying on tools in prod
- Phase 3: MGTI `usage` block pass-through and `X-Correlation-Id` echo unverified — capture a real stage response during Phase 3 to inform observability design

## Session Continuity

Last session: 2026-05-19T23:12:08Z
Stopped at: Completed 01-01-PLAN-01-package-skeleton.md (Plan 1 of 3 in Phase 1)
Resume file: None
