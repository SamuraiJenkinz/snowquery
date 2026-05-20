---
phase: 02-azure-extraction-parity-gate
plan: "02"
subsystem: llm
tags: [contextmanager, error-translation, QueryError, LLMError, exception-chaining]

# Dependency graph
requires:
  - phase: 01-abstraction-seam
    provides: "LLMError subclass hierarchy (errors.py), QueryError in src/utils.py"
provides:
  - "src/llm/_compat.py — single LLMError->QueryError translation seam (contextmanager)"
  - "llm_to_query_error() — the ONLY place in the codebase that maps LLMError subclasses to QueryError"
affects:
  - 02-plan-03  # call sites in query_router.py and sql_generator.py import this
  - 02-plan-04  # parity gate verifies the translation seam end-to-end
  - 03-anthropic-adapter  # Phase 3 may revisit LLMAuthError branch for provider dispatch

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "contextlib.contextmanager for single-point exception translation"
    - "raise ... from e (PEP 3134) preserving LLMError as __cause__ for debugging"
    - "Ordered except clauses — subclasses before base class to prevent shadowing"

key-files:
  created:
    - src/llm/_compat.py
  modified: []

key-decisions:
  - "LLMConfigError branch passes str(e) through to QueryError.message — provider embeds remediation text in the error at raise time; compat layer stays provider-agnostic (Phase-3-clean)"
  - "LLMAuthError branch hardcodes Azure remediation text ('Set the AZURE_OPENAI_API_KEY environment variable.') for byte-identical Phase 2 parity — KNOWN Phase 3 debt, revisit when Anthropic adapter lands"
  - "_compat.py NOT re-exported from src/llm/__init__.py — leading underscore is the signal; call sites import directly from src.llm._compat"
  - "Catch-all except LLMError branch ensures future subclasses (LLMGuardrailError, etc.) never leak past the seam"

patterns-established:
  - "Translation table lives in exactly one file: any Phase 3+ changes to error mapping edit src/llm/_compat.py only"
  - "context manager pattern: call sites use 'with llm_to_query_error():' wrapping client.complete()"

# Metrics
duration: 2min
completed: 2026-05-20
---

# Phase 2 Plan 02: Error Translation Seam Summary

**Single contextlib.contextmanager (_compat.py) translating all five LLMError subclasses to QueryError with preserved __cause__ chain and byte-identical Azure parity text**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-20T00:03:31Z
- **Completed:** 2026-05-20T00:05:19Z
- **Tasks:** 1/1
- **Files modified:** 1 (created)

## Accomplishments

- Created `src/llm/_compat.py` (97 lines) — the single LLMError->QueryError translation point (ERR-04, success criterion #3)
- All five except branches in correct subclass-first order: LLMConfigError, LLMAuthError, LLMTimeoutError, LLMTransientError, catch-all LLMError
- Exception chain preserved via `raise ... from e` on every branch (PEP 3134)
- Non-LLM exceptions and pre-existing QueryErrors pass through unchanged (no over-catching)
- Phase 1 acceptance gate held: 6/6 passing, zero locked files modified

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/llm/_compat.py with the llm_to_query_error() context manager** - `4b541c1` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/llm/_compat.py` — contextmanager translating LLMError subclasses to QueryError; 97 lines; single public function `llm_to_query_error()`

## Decisions Made

1. **LLMConfigError passes str(e) through as QueryError.message.** Provider (AzureOpenAIClient in Plan 01, AnthropicMGTIClient in Phase 3) embeds its own remediation text in the LLMConfigError message at raise time. The compat layer stays provider-agnostic — no "Azure" or "Anthropic" in this branch. Phase 3 adds Anthropic without touching _compat.py.

2. **LLMAuthError hardcodes Azure remediation text.** The historic `_call_azure_openai` raised `QueryError("Azure OpenAI API key not configured", "Set the AZURE_OPENAI_API_KEY environment variable.")`. This branch preserves that exact user-visible text for byte-identical parity. Marked as KNOWN Phase 3 debt — when Anthropic adapter lands, this branch can dispatch on `e.provider`.

3. **No re-export from `src/llm/__init__.py`.** The leading underscore signals package-internal. Call sites import directly from `src.llm._compat`. Re-exporting would invite use from app code that should hold LLMError directly.

4. **Catch-all `except LLMError` as the final branch.** Guarantees no LLMError subclass can ever leak past this context manager, even future ones (LLMGuardrailError, LLMSchemaError). Phase 3 can either rely on the catch-all (zero edits here) or add a dedicated branch above it (one-line edit).

## Deviations from Plan

None - plan executed exactly as written.

## Verify Script Output

All 8 behavioral assertions passed:
1. Empty block works (no exception, no translation).
2. LLMConfigError -> QueryError(str(e), 'Check your .env configuration.') with __cause__ preserved.
3. LLMAuthError -> QueryError('Azure OpenAI API key not configured', 'Set the AZURE_OPENAI_API_KEY environment variable.').
4. LLMTimeoutError -> QueryError('Azure OpenAI API call failed', str(e)).
5. LLMTransientError -> same first-arg as timeout.
6. LLMSchemaError (catch-all) -> QueryError('Azure OpenAI API call failed', str(e)) with __cause__ preserved.
7. KeyError passes through unchanged (no over-catching).
8. QueryError raised inside the block is NOT re-wrapped.

Final output: `PLAN 02-02 VERIFICATION OK`

## Additional Verification

- `inspect.getmembers` confirms `llm_to_query_error` is the only public function in `src.llm._compat`.
- `git diff --name-only HEAD` on all locked files: zero output (no locked file touched).
- Phase 1 acceptance gate `tests/test_llm_seam.py`: 6/6 passed in 0.91s.

## Phase 3 Evolution Path

When Phase 3 adds `LLMGuardrailError` from Anthropic, two paths are available:

- **(a) Rely on catch-all (zero edits to _compat.py):** `LLMGuardrailError` inherits from `LLMError` and is caught by the final `except LLMError` branch, translating to `QueryError("Azure OpenAI API call failed", str(e))`. Works immediately with no file changes here.
- **(b) Add dedicated branch (one-line edit to _compat.py):** Insert `except LLMGuardrailError as e:` above the catch-all with a guardrail-specific message. Gives Phase 3 full control over the user-visible text for guardrail hits.

Both paths are supported by this design. The `LLMAuthError` branch is the one most likely to need Phase 3 attention: when Anthropic lands, that branch should dispatch on `e.provider` to emit `"Set the ANTHROPIC_API_KEY environment variable."` for Anthropic auth failures.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `src/llm/_compat.py` is ready for Plan 03 call sites (`query_router.py`, `sql_generator.py`) to import `llm_to_query_error` and wrap their `client.complete(...)` calls.
- Plan 04 parity gate can import the seam and verify end-to-end error paths.
- No blockers.

---
*Phase: 02-azure-extraction-parity-gate*
*Completed: 2026-05-20*
