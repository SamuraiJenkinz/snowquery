# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** Phase 2 — Azure Extraction

## Current Position

Phase: 2 of 5 (Azure Extraction + Parity Gate) — In progress
Plan: 2 of 4 in Phase 2 (02-01 and 02-02 complete)
Status: In progress — 02-02 complete (error-translation seam done)
Last activity: 2026-05-20 — Completed 02-PLAN-02-error-translation-seam.md

Progress: [███░░░░░░░] 27% (4/15 plans estimated — counting 02-01 + 02-02 in wave 1)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 4 min
- Total execution time: 11 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Abstraction Seam | 3 | 11 min | ~4 min |

**Recent Trend:**
- Last 5 plans: 01-01 (3 min), 01-02 (3 min), 01-03 (5 min), 02-02 (2 min)
- Trend: consistent 2-5 min/plan

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

Decisions from 01-02 (config + factory + stubs):
- Factory does NOT call validate_config() itself — explicit call at app.py startup (Phase 5)
- Cache key is provider string only — no api_key fingerprint until Phase 5 needs mid-session reload
- Adapter __init__ is no-op in Phase 1 (no raise) so factory cache can store instance
- st.session_state wrapped in try/except Exception (not hasattr) per RESEARCH.md verified pattern

Decisions from 01-03 (smoke verification):
- pytest 9.0.2 already installed — no requirements.txt change needed (dev-only)
- tests/ directory created without __init__.py (pytest discovers by collection)
- Acceptance gate pattern established: one pytest module per phase proves each numbered success criterion
- Cache-clear autouse fixture required for module-level singletons in get_llm

Decisions from 02-02 (error-translation seam):
- LLMConfigError branch passes str(e) through to QueryError.message — provider embeds remediation text at raise time; compat layer stays provider-agnostic (Phase-3-clean, no "Azure"/"Anthropic" text here)
- LLMAuthError branch hardcodes Azure remediation text for byte-identical Phase 2 parity — KNOWN Phase 3 debt: revisit when Anthropic adapter lands to dispatch on e.provider
- src/llm/_compat.py NOT re-exported from src/llm/__init__.py — call sites import directly from src.llm._compat (leading underscore = package-internal signal)
- Catch-all except LLMError is final branch — future subclasses (LLMGuardrailError etc.) never leak past the seam; Phase 3 can add dedicated branch above catch-all or rely on it

### Phase 1 Sign-Off

Phase 1 (Abstraction Seam) is complete. All 5 ROADMAP.md success criteria are proven by the acceptance gate at tests/test_llm_seam.py (6 tests, 0.42s, zero live HTTP calls). The seam is stable for Phase 2 to plug AzureOpenAIClient into.

### Pending Todos

None.

### Blockers/Concerns

- Phase 4: MGTI proxy strict-tools support is "works as of 2026-05-12 but undocumented" — `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch must be verified against staging before relying on tools in prod
- Phase 3: MGTI `usage` block pass-through and `X-Correlation-Id` echo unverified — capture a real stage response during Phase 3 to inform observability design

## Session Continuity

Last session: 2026-05-20T00:05:19Z
Stopped at: Completed 02-PLAN-02-error-translation-seam.md (Plan 2 of 4 in Phase 2 — wave 1 of 2 in progress)
Resume file: None
