---
phase: 01-abstraction-seam
plan: 01
subsystem: api
tags: [python, abc, dataclasses, error-taxonomy, llm, abstraction]

# Dependency graph
requires: []
provides:
  - src/llm/ package skeleton: LLMClient ABC, 7 error classes, 4 frozen+slots dataclasses
  - LLMError flat hierarchy (ERR-01) ready for Phases 2-4 to raise
  - LLMClient two-method contract enforced at construction time (ABS-02)
  - ClassificationResultV1 chart-field-free (TOOL-03 precondition)
affects:
  - 01-02-config-factory-stubs (imports from errors, types, base)
  - 01-03-smoke-verification (imports from src.llm package)
  - Phase 2 Azure extraction (implements LLMClient interface)
  - Phase 3 Anthropic adapter (implements LLMClient interface)
  - Phase 4 strict-tools (derives INTENT_TOOL from ClassificationResultV1)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "abc.ABC with @abstractmethod for adapter contract enforcement"
    - "frozen=True, slots=True dataclasses at adapter boundary (Python 3.10+ floor)"
    - "flat error hierarchy under LLMError — catchable by family or by name"

key-files:
  created:
    - src/llm/__init__.py
    - src/llm/base.py
    - src/llm/errors.py
    - src/llm/types.py
  modified: []

key-decisions:
  - "Flat error hierarchy (no retryable subtree) — Phase 5 can add if retry logic lands"
  - "messages: list[dict] on complete() — Azure-native shape, zero Phase 2 diff at call sites; Anthropic adapter extracts system internally"
  - "ClassificationResultV1 excludes chart_requested/chart_type — heuristic fields merged post-LLM in Phase 4"
  - "ToolCall.raw_response uses field(repr=False) — debug payload never leaks into log messages"
  - "No get_llm factory in __init__.py — Plan 02 owns that; this plan is seam-only"

patterns-established:
  - "from __future__ import annotations at top of every src/llm/*.py (matches project style)"
  - "Absolute imports (from src.llm.x import Y) matching utils.py/query_router.py convention"

# Metrics
duration: 3min
completed: 2026-05-19
---

# Phase 1 Plan 01: Package Skeleton Summary

**`src/llm/` package skeleton: LLMClient ABC with two-method contract, 7-class flat error hierarchy, and 4 frozen+slots boundary dataclasses — all importable, no call sites modified**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-19T23:09:29Z
- **Completed:** 2026-05-19T23:12:08Z
- **Tasks:** 3
- **Files modified:** 4 created

## Accomplishments

- Created `src/llm/` as a real importable Python package (ABS-01 partial)
- `LLMClient(abc.ABC)` enforces `complete` and `classify_with_tool` at construction — incomplete subclass raises `TypeError` at instantiation time (ABS-02)
- Seven error classes in a flat hierarchy under `LLMError`, all carrying `provider/status_code/correlation_id` kwargs — only `LLMConfigError` raised in Phase 1, rest ready for Phases 2-4 (ERR-01)
- Four `frozen=True, slots=True` dataclasses at the adapter boundary: `ToolSchema`, `ToolCall`, `ClassificationResultV1`, `IntentResult` — `ClassificationResultV1` intentionally excludes `chart_requested`/`chart_type` (TOOL-03 precondition)
- `ToolCall.raw_response` excluded from `repr()` — debug payloads never appear in log messages (success criterion #5 partial)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create errors.py with the full LLM error taxonomy** - `f3cc42e` (feat)
2. **Task 2: Create types.py with the four boundary dataclasses** - `247318f` (feat)
3. **Task 3: Create base.py with LLMClient ABC, and __init__.py as a minimal package marker** - `bb7913a` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `src/llm/errors.py` — 51 lines: LLMError base + 6 typed subclasses, all with provider/status_code/correlation_id kwargs
- `src/llm/types.py` — 75 lines: ToolSchema, ToolCall (raw_response repr=False), ClassificationResultV1 (no chart fields), IntentResult (chart fields from heuristic)
- `src/llm/base.py` — 84 lines: LLMClient(abc.ABC) with @abstractmethod complete and classify_with_tool, exact signatures from RESEARCH.md
- `src/llm/__init__.py` — 40 lines: re-exports all 12 public names; documents Phase 1-5 roadmap in module docstring

## Decisions Made

- **Flat error hierarchy** — no retryable vs non-retryable grouping. Call sites catch by name (`except LLMAuthError`); grouping can be added in Phase 5 if a retry strategy lands. Adding `retryable: bool` now would be misleading with no retry logic.
- **`messages: list[dict]` on `complete()`** — matches today's Azure call sites exactly (zero Phase 2 diff). Anthropic adapter (Phase 3) extracts the system-role message and promotes it to top-level `system` internally; the interface doesn't need to know.
- **`ClassificationResultV1` excludes `chart_requested`/`chart_type`** — these are heuristic fields populated by `_detect_chart_request()` in `query_router.py` before the LLM call, and merged into the final dict afterward. The LLM schema must not include them (TOOL-03).
- **`ToolCall.raw_response = field(default_factory=dict, repr=False)`** — debug-only; frozen prevents slot reassignment but dict contents remain mutable (acceptable for Phase 1).
- **No `get_llm` factory in this plan** — Plan 02 owns the factory, registry, settings, and adapter stubs. This plan is seam-only per the plan's objective.

## Deviations from Plan

None - plan executed exactly as written. All four files match the recommended shapes from RESEARCH.md section by section, with no structural differences.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Plan Verification

Full verification passed:

```
PLAN 01 VERIFICATION OK
```

### Confirmations

- **ABC enforcement confirmed:** `LLMClient.__abstractmethods__ == frozenset({'complete', 'classify_with_tool'})`; instantiating an incomplete subclass raises `TypeError`
- **`ClassificationResultV1` is chart-field-free:** `'chart_requested' not in ClassificationResultV1.__dataclass_fields__` and `'chart_type' not in ClassificationResultV1.__dataclass_fields__`
- **All 7 error classes exist:** `LLMError`, `LLMAuthError`, `LLMTransientError`, `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMConfigError` — all flat subclasses of `LLMError`
- **frozen+slots confirmed:** All 4 types have `__slots__`, `FrozenInstanceError` raised on slot reassignment
- **repr safety confirmed:** `ToolCall.raw_response` excluded from `repr()` output

### Python Interpreter

Used `python` (resolves to Python 3.13.3 at project root). All verifications ran without activating a venv — the project's standard interpreter resolved correctly.

## Next Phase Readiness

Plan 02 (`01-PLAN-02-config-factory-stubs.md`) can proceed immediately:
- `src/llm/` exists and is importable
- `LLMClient`, all error classes, and all dataclasses are available via `from src.llm import ...`
- Plan 02 will add: `get_llm` factory, `LLMSettings`/`validate_config` in `config.py`, adapter stubs (`azure_openai.py`, `anthropic_mgti.py`), and `jsonschema` to `requirements.txt`

No blockers or concerns from this plan.

---
*Phase: 01-abstraction-seam*
*Completed: 2026-05-19*
