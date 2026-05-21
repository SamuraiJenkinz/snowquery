---
phase: 03-anthropic-mgti-adapter
plan: "02"
subsystem: llm
tags: [error-translation, provider-dispatch, contextmanager, QueryError, LLMError, anthropic, azure_openai]

# Dependency graph
requires:
  - phase: 02-azure-extraction-parity-gate
    provides: "src/llm/_compat.py llm_to_query_error() context manager with five LLMError except branches; tests/test_phase2_parity.py regression-guards the Azure user-visible wording"
  - phase: 01-abstraction-seam
    provides: "LLMError subclass hierarchy with .provider attribute (errors.py)"
provides:
  - "src/llm/_compat.py llm_to_query_error() with per-provider dispatch on LLMAuthError, LLMTimeoutError, LLMTransientError, and catch-all LLMError"
  - "Anthropic-named QueryError wording for provider='anthropic_mgti': 'Anthropic API key not configured or not authorised' / 'Anthropic API call failed'"
  - "Azure path (and unknown-provider fallback) preserved BYTE-IDENTICAL to Phase 2 wording"
affects:
  - 03-plan-03  # AnthropicMGTIClient must raise LLMError subclasses with provider='anthropic_mgti' so the dispatch fires
  - 03-plan-04  # Phase 3 acceptance gate adds Anthropic-named error-translation assertions on top of the existing Azure ones
  - 05-router-and-defaults  # Phase 5 UI is now unblocked from showing the wrong product name on Anthropic errors

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provider dispatch via getattr(e, 'provider', None) == 'anthropic_mgti' inside the except branch"
    - "Defensive getattr() over e.provider so third-party LLMError subclasses without a provider= kwarg still fall back to the Azure path"
    - "Azure path remains the unconditional fallback in every dispatched branch (regression guard for Phase 2 acceptance gate)"

key-files:
  created: []
  modified:
    - src/llm/_compat.py

key-decisions:
  - "Used getattr(e, 'provider', None) (not e.provider) — defensive against future third-party LLMError raised without the provider kwarg; three lines, no cost"
  - "Azure path is the unconditional fallback in every dispatched branch — covers unknown providers and any future adapter that has not yet been wired into _compat.py dispatch"
  - "LLMConfigError branch UNCHANGED — Phase 2 OQ-1 lock holds: provider embeds remediation at raise time, _compat passes str(e) through verbatim, Plan 03 follows the same pattern for AnthropicMGTIClient pre-flight checks"
  - "Extended dispatch to LLMTimeoutError, LLMTransientError, and catch-all LLMError (per orchestrator OQ-2) — without this, a Phase 3 Anthropic timeout would surface as 'Azure OpenAI API call failed' which is a wrong-product-label UX bug; ~12 additional lines"
  - "One try with five excepts shape preserved (no helper extraction) — the file's value is exactly that it is a single, readable translation table"
  - "Order of except clauses preserved: LLMConfigError → LLMAuthError → LLMTimeoutError → LLMTransientError → LLMError (catch-all must stay last; siblings ordered for readability, not Python semantics)"

patterns-established:
  - "Per-provider dispatch lives inside the except branch — not extracted to a helper, not done via a dict — keeps the translation table readable as a single block"
  - "Provider-named QueryError wording ('Anthropic API call failed' vs 'Azure OpenAI API call failed') — every future adapter follows this naming convention so the UI never shows the wrong product label"
  - "KNOWN-DEBT debt-down pattern: Phase 2 recorded the debt in STATE.md + docstring with explicit Phase 3 trigger; Phase 3 paid it down + updated the docstring to reflect closure"

# Metrics
duration: 2min
completed: 2026-05-21
---

# Phase 3 Plan 02: Compat Provider Dispatch Summary

**src/llm/_compat.py now dispatches the LLMAuthError / LLMTimeoutError / LLMTransientError / catch-all LLMError branches on `e.provider` so Anthropic errors surface as 'Anthropic API call failed' / 'Anthropic API key not configured or not authorised' while the Azure path preserves Phase 2 wording byte-identically**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-21T14:58:21Z
- **Completed:** 2026-05-21T15:00:28Z
- **Tasks:** 1/1
- **Files modified:** 1

## Accomplishments

- Paid down the Phase 2 KNOWN DEBT recorded in STATE.md ("LLMAuthError branch hardcodes Azure remediation text — Phase 3 known debt: revisit when Anthropic adapter lands to dispatch on e.provider")
- Extended dispatch beyond the originally-debted LLMAuthError branch to also cover LLMTimeoutError, LLMTransientError, and the catch-all LLMError (per orchestrator OQ-2) — prevents an Anthropic timeout from showing "Azure OpenAI API call failed" to the user
- Azure path (and any unknown / None provider) preserved BYTE-IDENTICAL to Phase 2 — the Phase 2 acceptance gate at `tests/test_phase2_parity.py` `test_error_translation_at_call_site` still asserts the historic Azure strings and still passes
- LLMConfigError branch UNCHANGED — Phase 2 OQ-1 lock holds; Plan 03 will follow the same "provider embeds remediation text in the message" pattern for AnthropicMGTIClient pre-flight checks
- Module docstring updated to reflect that the Phase 3 debt is now closed: "LLMAuthError / LLMTimeoutError / LLMTransientError / catch-all LLMError dispatch on e.provider so Anthropic errors get Anthropic-named remediation"
- Phase 1 (6) + Phase 2 (12) acceptance gates = 18 tests still green in 8.68s

## Task Commits

Each task was committed atomically:

1. **Task 1: Add provider dispatch to LLMAuthError, LLMTimeoutError, LLMTransientError, and catch-all LLMError branches in llm_to_query_error()** — `51a2040` (feat)

**Plan metadata:** (docs commit follows this summary)

## Files Created/Modified

- `src/llm/_compat.py` — `llm_to_query_error()` context manager: four except branches now dispatch on `getattr(e, "provider", None) == "anthropic_mgti"`; LLMConfigError branch logic unchanged; docstring updated. Diff: +37 / -17 lines.

## Diff Snippet (src/llm/_compat.py)

The four updated branches plus the unchanged LLMConfigError branch (showing the dispatch pattern is uniform across the four dispatched branches and that LLMConfigError still passes `str(e)` through verbatim):

```python
except LLMConfigError as e:
    # UNCHANGED — provider embeds remediation text at raise time; str(e) is
    # passed through verbatim. This is the "Phase-3-clean" pattern from
    # Phase 2 OQ-1 ...
    raise QueryError(str(e), "Check your .env configuration.") from e

except LLMAuthError as e:
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError(
            "Anthropic API key not configured or not authorised",
            "Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.",
        ) from e
    # Azure path (and any unknown / None provider — preserves Phase 2 behavior)
    raise QueryError(
        "Azure OpenAI API key not configured",
        "Set the AZURE_OPENAI_API_KEY environment variable.",
    ) from e

except LLMTimeoutError as e:
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e

except LLMTransientError as e:
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e

except LLMError as e:
    # Catch-all for LLMSchemaError, LLMGuardrailError, future additions
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
```

## LLMConfigError Branch — Byte-Identical to Phase 2

**Phase 2 (pre-change):**
```python
except LLMConfigError as e:
    # Provider embeds remediation text in the LLMConfigError message
    # at raise time (see AzureOpenAIClient.complete pre-flight check).
    # Pass str(e) through as the QueryError.message so the user sees
    # the same actionable text today and after Phase 3 adds Anthropic.
    raise QueryError(str(e), "Check your .env configuration.") from e
```

**Phase 3 (post-change):**
```python
except LLMConfigError as e:
    # UNCHANGED — provider embeds remediation text at raise time; str(e) is
    # passed through verbatim. This is the "Phase-3-clean" pattern from
    # Phase 2 OQ-1: adding a new provider does NOT require editing this
    # branch (the new adapter just constructs LLMConfigError with its own
    # remediation text — see AnthropicMGTIClient.complete pre-flight check
    # in Phase 3 Plan 03).
    raise QueryError(str(e), "Check your .env configuration.") from e
```

The `raise QueryError(str(e), "Check your .env configuration.") from e` is byte-identical. Only the comment was rewritten to declare the lock explicitly. Phase 2 OQ-1 contract holds.

## Acceptance Gate Status

```
$ python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v
============================= 18 passed in 8.68s ==============================
```

All 18 tests green (6 Phase 1 + 12 Phase 2). The critical regression guard `test_error_translation_at_call_site` (which injects `LLMAuthError(provider="azure_openai")`, `LLMTimeoutError(provider="azure_openai")`, and `LLMTransientError(provider="azure_openai")` and asserts the historic Azure strings) PASSED — confirms the Azure fallback path in each dispatched branch is wired correctly.

## Inline Verification

Beyond the pytest suite, the plan's inline verification block was executed and printed `TASK 1 OK`. It asserts:

- LLMAuthError(azure_openai) → `QueryError("Azure OpenAI API key not configured", "Set the AZURE_OPENAI_API_KEY environment variable.")` (Phase 2 byte-identical)
- LLMAuthError(anthropic_mgti) → `QueryError("Anthropic API key not configured or not authorised", "Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.")` (Phase 3 new wording)
- LLMAuthError(some_new_provider) → falls back to Azure wording (defensive fallback)
- LLMTimeoutError(azure_openai) → `QueryError("Azure OpenAI API call failed", ...)` with timeout text preserved
- LLMTimeoutError(anthropic_mgti) → `QueryError("Anthropic API call failed", ...)` with timeout text preserved
- LLMTransientError(azure_openai) → `"Azure OpenAI API call failed"`
- LLMTransientError(anthropic_mgti) → `"Anthropic API call failed"`
- LLMSchemaError(azure_openai) → catch-all routes to `"Azure OpenAI API call failed"`
- LLMGuardrailError(anthropic_mgti) → catch-all routes to `"Anthropic API call failed"`
- LLMSchemaError(anthropic_mgti) → catch-all routes to `"Anthropic API call failed"`
- LLMConfigError(anthropic_mgti, "Anthropic model must start with eu.anthropic.claude-") → `QueryError("Anthropic model must start with eu.anthropic.claude-", "Check your .env configuration.")` — provider's embedded text passes through verbatim, no _compat-level "Anthropic" string injection

## Files Modified — Verification

```
$ git diff --name-only HEAD~1 HEAD
src/llm/_compat.py
```

Exactly one file. Plan 01 runs in parallel (Wave 1) and edits `.env.example` + `src/llm/azure_openai.py`; this plan touched neither.

## Decisions Made

1. **Used `getattr(e, "provider", None)` rather than `e.provider`.** `LLMError.__init__` always sets `self.provider` (defaulting to `None`), but using `getattr` is defensive against any third-party / external library exception that subclasses LLMError and bypasses our `__init__`. Three extra characters, no cost, lower future-debugging surface area.

2. **Azure path is the unconditional fallback in every dispatched branch.** Rather than dispatching on `provider == "azure_openai"`, the code reads `if provider == "anthropic_mgti": …` then unconditionally raises the Azure-named QueryError. This means: (a) provider=None falls to Azure path (Phase 2 behavior preserved), (b) any future adapter that hasn't been wired into _compat.py yet falls to Azure path (safe default while migration is in progress), and (c) the Phase 2 acceptance gate test_error_translation_at_call_site still passes byte-identically because its `provider="azure_openai"` injection hits the same code path it did before.

3. **Extended dispatch to LLMTimeoutError, LLMTransientError, and catch-all LLMError beyond the originally-debted LLMAuthError branch.** Per orchestrator OQ-2 — without these three, a Phase 3 Anthropic timeout shows the user "Azure OpenAI API call failed" which is a wrong-product-label UX bug Phase 5 would have to chase. The dispatch is additive (~3 lines per branch, 12 lines total) and no Phase 2 test asserts the exact text for non-Azure providers, so it is safe to land in Phase 3.

4. **LLMConfigError branch left untouched.** Phase 2 OQ-1 locked the pattern: provider embeds remediation text at raise time, _compat passes `str(e)` through verbatim. Plan 03 will follow the same pattern for AnthropicMGTIClient pre-flight checks. Touching this branch in Phase 3 would reopen OQ-1.

5. **No helper extraction.** A helper like `_dispatch_provider(e, anthropic_msg, azure_msg, default_details)` was rejected — the file's value is being a single, readable translation table. The repetition is the point.

6. **Module docstring updated.** The Phase 2 docstring explicitly carried the debt forward: "Phase 3 may revisit this branch when the Anthropic adapter lands — at that point the branch can dispatch on e.provider." Replaced with the post-resolution wording: "LLMAuthError / LLMTimeoutError / LLMTransientError / catch-all LLMError dispatch on e.provider so Anthropic errors get Anthropic-named remediation. The Azure path (and unknown-provider path) preserves the exact Phase 2 wording byte-identically. See the if-branches below." A future reader will not think the debt is still open.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Phase 2 Known Debt Resolution

**Phase 2 known debt resolved:** LLMAuthError + LLMTimeoutError + LLMTransientError + catch-all LLMError now dispatch on e.provider. Phase 5 UI is unblocked from showing wrong product names on Anthropic errors.

The STATE.md "Accumulated Context" entry recording the debt ("LLMAuthError branch hardcodes Azure remediation text for byte-identical Phase 2 parity — KNOWN Phase 3 debt: revisit when Anthropic adapter lands to dispatch on e.provider") and the corresponding docstring comment in `src/llm/_compat.py` are now closed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 (`03-PLAN-03-anthropic-adapter.md`) can now build `AnthropicMGTIClient` knowing that:
  - Raising `LLMAuthError(provider="anthropic_mgti", ...)` will surface as `"Anthropic API key not configured or not authorised"` at the call site
  - Raising `LLMTimeoutError(provider="anthropic_mgti", ...)` / `LLMTransientError(provider="anthropic_mgti", ...)` will surface as `"Anthropic API call failed"`
  - Raising `LLMConfigError(<remediation_text>, provider="anthropic_mgti")` will surface the embedded text verbatim with `"Check your .env configuration."` as details — same OQ-1 pattern as Azure
- Plan 04 (Phase 3 acceptance gate) can grep-assert the new Anthropic-named QueryError strings ("Anthropic API call failed", "Anthropic API key not configured or not authorised") in addition to keeping the Azure assertions from Phase 2
- No blockers. Wave 1 unblocked — Plan 01 (`.env.example` + `src/llm/azure_openai.py` startup-log) can land in parallel without conflict; Plan 03 can land immediately after both Wave 1 plans

---
*Phase: 03-anthropic-mgti-adapter*
*Completed: 2026-05-21*
