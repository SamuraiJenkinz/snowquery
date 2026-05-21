---
phase: 03-anthropic-mgti-adapter
plan: 04
subsystem: testing
tags: [pytest, acceptance-gate, anthropic, mgti, mock, unittest, requests, llm]

# Dependency graph
requires:
  - phase: 03-anthropic-mgti-adapter
    provides: AnthropicMGTIClient (Plan 03), env+startup-log (Plan 01), per-provider QueryError dispatch (Plan 02)
provides:
  - tests/test_phase3_adapter.py — 21-test acceptance gate covering all 5 Phase 3 ROADMAP SCs plus end-to-end LLMError→QueryError dispatch through Plan 02
  - Combined Phase 1+2+3 green run (39 tests) — user-facing "Phase 3 complete" signal
  - Regression guards for the order-sensitive guardrail-before-emptiness check (RESEARCH.md Pitfall 4)
  - Regression guard for empty-model no-raise at __init__ (Phase 1 no-op pattern preservation)
  - Regression guard against tool-wrapping appearing at generate_sql / generate_executive_summary call sites
affects: [04-strict-tools-and-smoke, 05-ui-toggle-and-final-cutover]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Self-contained pytest module (no conftest.py, no pytest.ini) — Phase 1/Phase 2 acceptance-gate convention extended to Phase 3"
    - "Inline mock-response builder helpers (_make_anthropic_response, _make_error_response) — RESEARCH.md Mock Response Builder Pattern; no fixture files (Phase 3 has no parity baseline)"
    - "Logging-handler capture for structured-log SC verification (_RecordCapturer adds/removes a Handler in finally per test — no global mutation)"
    - "Level A patching: unittest.mock.patch('requests.post', ...) — exercises the real adapter against inline-dict mocked responses"
    - "Factory cache isolation via autouse fixture (_clear_factory_cache clears src.llm._cache between tests)"
    - "Env-var isolation via autouse fixture (_strip_llm_env strips all 12 LLM env vars including Phase 3 additions)"

key-files:
  created:
    - tests/test_phase3_adapter.py
  modified: []

key-decisions:
  - "_RecordCapturer is a class-level helper (defined once near SC #5 group) rather than a fixture — adds a fresh handler in each test and removes it in finally; does NOT mutate global logger level/formatters"
  - "anthropic_env and opus_env are SEPARATE fixtures (not parameterized) — opus path needs distinct response body model field and triggers a different code branch; keeping them apart makes the SC #2 test names self-documenting"
  - "test_no_tool_wrapping_in_call_sites uses inspect.getsource (mirror of Phase 2 test_call_azure_openai_eliminated) — no live call to the call sites; just a static assertion that classify_with_tool string is absent and complete( is present"
  - "Empty-model no-raise verified TWICE: at __init__ (constructs) AND at complete() pre-flight (raises LLMConfigError) — proves both halves of the Phase 1 no-op pattern intact in Phase 3"
  - "Guardrail/Schema-error pair (test_guardrail_intervened_raises_guardrail_error + test_empty_content_non_guardrail_raises_schema_error) together prove the order is correct — if checks are reversed, only the latter passes"

patterns-established:
  - "Phase acceptance-gate file naming + structure: tests/test_phase{N}_{name}.py — self-contained pytest module, 1 test function per SC dimension, docstrings cite the SC, autouse fixtures for cache/env isolation, inline mock helpers above the SC groups"
  - "Combined-suite signal: pytest tests/ at the end of each phase shows cumulative passing count (Phase 1: 6, +Phase 2: 18, +Phase 3: 39) — the canonical 'phase complete' check"
  - "COMPAT-DISPATCH test group at the end of each adapter-phase gate — exercises the prior phase's _compat dispatch end-to-end with the new adapter's provider tag, locks against the 'wrong product label in UI' regression class"

# Metrics
duration: 3min
completed: 2026-05-21
---

# Phase 3 Plan 04: Acceptance Gate Summary

**Phase 3 acceptance gate landed — 21-test pytest module proves all 5 Phase 3 ROADMAP success criteria offline plus end-to-end Anthropic LLMError→QueryError dispatch through Plan 02; combined Phase 1+2+3 run is 39/39 green.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-21T15:16:19Z
- **Completed:** 2026-05-21T15:19:33Z
- **Tasks:** 1
- **Files created:** 1 (tests/test_phase3_adapter.py)
- **Files modified:** 0

## Accomplishments

- `tests/test_phase3_adapter.py` created — 552 lines, 21 standalone test functions, self-contained pytest module (no conftest.py, no pytest.ini)
- All 5 Phase 3 ROADMAP success criteria mapped to ≥1 executable test (see SC→test mapping table below)
- COMPAT-DISPATCH group (2 tests) proves Plan 02's per-provider QueryError dispatch end-to-end — Anthropic auth + timeout errors surface with Anthropic-labelled QueryError, not Azure-labelled
- Combined Phase 1+2+3 acceptance gates ALL green: `pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py -q` reports 39 passed (6 + 12 + 21)
- Test gate runs OFFLINE — zero live HTTP; all `requests.post` patched via `unittest.mock.patch`; response bodies are inline Python dicts (no fixture files — Phase 3 has no parity baseline)
- Order-sensitive guardrail-before-emptiness regression guards installed (RESEARCH.md Pitfall 4) — `test_guardrail_intervened_raises_guardrail_error` + `test_empty_content_non_guardrail_raises_schema_error` are a load-bearing pair

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/test_phase3_adapter.py — Phase 3 acceptance gate covering all 5 SCs + end-to-end compat dispatch** — `30f4b58` (test)

## Files Created/Modified

- `tests/test_phase3_adapter.py` (NEW, 552 lines) — Phase 3 acceptance gate pytest module. Five SC-grouped test sections (3 + 4 + 7 + 1 + 4 tests) + a sixth COMPAT-DISPATCH group (2 tests) = 21 standalone test functions. Self-contained; no conftest.py or pytest.ini added.

## Verification Results

### Phase 3 acceptance gate (21 tests)

Command: `python -m pytest tests/test_phase3_adapter.py -v`

Exit code: **0**

```
tests/test_phase3_adapter.py::test_url_construction PASSED                            [  4%]
tests/test_phase3_adapter.py::test_required_headers_present PASSED                    [  9%]
tests/test_phase3_adapter.py::test_fresh_correlation_id_per_call PASSED               [ 14%]
tests/test_phase3_adapter.py::test_init_raises_on_bad_model_prefix PASSED             [ 19%]
tests/test_phase3_adapter.py::test_init_no_raise_on_empty_model PASSED                [ 23%]
tests/test_phase3_adapter.py::test_opus_4_7_omits_sampling_params PASSED              [ 28%]
tests/test_phase3_adapter.py::test_non_opus_includes_temperature PASSED               [ 33%]
tests/test_phase3_adapter.py::test_http_401_raises_auth_error PASSED                  [ 38%]
tests/test_phase3_adapter.py::test_http_403_raises_auth_error PASSED                  [ 42%]
tests/test_phase3_adapter.py::test_http_429_raises_transient_error PASSED             [ 47%]
tests/test_phase3_adapter.py::test_http_503_raises_transient_error PASSED             [ 52%]
tests/test_phase3_adapter.py::test_requests_timeout_raises_timeout_error PASSED       [ 57%]
tests/test_phase3_adapter.py::test_guardrail_intervened_raises_guardrail_error PASSED [ 61%]
tests/test_phase3_adapter.py::test_empty_content_non_guardrail_raises_schema_error PASSED [ 66%]
tests/test_phase3_adapter.py::test_env_example_has_all_9_anthropic_vars PASSED        [ 71%]
tests/test_phase3_adapter.py::test_startup_log_anthropic_provider PASSED              [ 76%]
tests/test_phase3_adapter.py::test_startup_log_azure_provider PASSED                  [ 80%]
tests/test_phase3_adapter.py::test_factory_cache_dedupes_startup_log PASSED           [ 85%]
tests/test_phase3_adapter.py::test_no_tool_wrapping_in_call_sites PASSED              [ 90%]
tests/test_phase3_adapter.py::test_anthropic_auth_error_translates_to_anthropic_query_error PASSED [ 95%]
tests/test_phase3_adapter.py::test_anthropic_timeout_translates_to_anthropic_query_error PASSED   [100%]

============================= 21 passed in 7.72s ==============================
```

### Phase 1+2 acceptance gates still green

Command: `python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -q`

Exit code: **0** — 18 passed (6 Phase 1 + 12 Phase 2)

### Combined run — the user-facing "Phase 3 complete" signal

Command: `python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py -q`

Exit code: **0**

```
.......................................                                  [100%]
39 passed in 8.06s
```

**39 tests passing** = 6 (Phase 1 seam) + 12 (Phase 2 parity) + 21 (Phase 3 adapter). This is the user-facing Phase 3 acceptance signal.

### SC → test mapping table

Every Phase 3 ROADMAP success criterion is proven by ≥1 passing executable test:

| ROADMAP SC | Test function(s) | Count |
| --- | --- | --- |
| **SC #1** — POST `{base_url}/model/{model}/messages` with X-Api-Key + Content-Type + fresh X-Correlation-Id UUID per call | `test_url_construction`, `test_required_headers_present`, `test_fresh_correlation_id_per_call` | 3 |
| **SC #2** — Bad model prefix raises LLMConfigError at __init__; opus-4-7 OMITS sampling params; empty model is no-op at __init__; non-opus INCLUDES temperature | `test_init_raises_on_bad_model_prefix`, `test_init_no_raise_on_empty_model`, `test_opus_4_7_omits_sampling_params`, `test_non_opus_includes_temperature` | 4 |
| **SC #3** — Typed-error mapping including order-sensitive guardrail-before-emptiness | `test_http_401_raises_auth_error`, `test_http_403_raises_auth_error`, `test_http_429_raises_transient_error`, `test_http_503_raises_transient_error`, `test_requests_timeout_raises_timeout_error`, `test_guardrail_intervened_raises_guardrail_error`, `test_empty_content_non_guardrail_raises_schema_error` | 7 |
| **SC #4** — `.env.example` has all 9 Anthropic vars with non-empty defaults | `test_env_example_has_all_9_anthropic_vars` | 1 |
| **SC #5** — Startup `llm_provider_loaded` log per loadable provider (Anthropic + Azure), factory cache dedupes to 1 event, no `classify_with_tool` at the call sites | `test_startup_log_anthropic_provider`, `test_startup_log_azure_provider`, `test_factory_cache_dedupes_startup_log`, `test_no_tool_wrapping_in_call_sites` | 4 |
| **COMPAT-DISPATCH** (Plan 02 end-to-end) | `test_anthropic_auth_error_translates_to_anthropic_query_error`, `test_anthropic_timeout_translates_to_anthropic_query_error` | 2 |
| **Total** | | **21** |

### Offline-run confirmation

- All `requests.post` calls are patched via `unittest.mock.patch` in every adapter-direct test.
- All response bodies are constructed inline as Python dicts via `_make_anthropic_response(...)` and `_make_error_response(...)` helpers — NO fixture files exist.
- The only filesystem read is `.env.example` (SC #4 test reads it as text; not a network call).
- No `pytest --collect-only` warnings about missing network deps; `pytest` runs to completion in ~8 seconds with no internet.

### Scope-discipline confirmation

`git diff --name-only HEAD~1 HEAD` (the Plan 04 commit only):

```
tests/test_phase3_adapter.py
```

Exactly one file touched — the test gate. No `src/`, `app.py`, `config.py`, or `.env.example` modifications (those landed in Plans 01–03 and are now LOCKED for Phase 3).

### Cross-cutting verification greps (all PASS)

- `grep -n "X-Correlation-Id\|X-Api-Key\|/messages" src/llm/anthropic_mgti.py` → 10 hits (URL + headers in adapter source)
- `grep -cE "raise LLM(Config|Auth|Transient|Timeout|Guardrail|Schema)Error" src/llm/anthropic_mgti.py` → 13 raises (4 config + 1 auth + 2 transient + 1 timeout + 1 guardrail + 4 schema, covering all SC #3 mapping cases)
- `grep -l "llm_provider_loaded" src/llm/` → 2 files (anthropic_mgti.py + azure_openai.py) — symmetric SC #5 Anthropic+Azure halves

## Decisions Made

None - followed plan as specified. The test module matches the plan's exact `<action>` block byte-for-byte; the only "decision" was confirming all preconditions from the prior plans match what the test file assumes (verified by reading `src/llm/anthropic_mgti.py`, `src/llm/_compat.py`, `src/llm/azure_openai.py`, `src/llm/__init__.py`, and `.env.example` before writing the test).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The Phase 3 acceptance gate is a test-only deliverable that runs offline.

## Next Phase Readiness

**Phase 3 (Anthropic MGTI Adapter) is complete.** The acceptance gate is green — Anthropic adapter is wired against the MGTI Apigee proxy with full typed-error mapping, structured logging, and per-provider QueryError dispatch. The adapter is reachable via `get_llm('anthropic_mgti')` but no UI exposes it yet — Phase 5 owns the sidebar toggle. Phase 4 (Strict-Tools + Smoke Test) is unblocked.

What's locked and reusable downstream:
- `tests/test_phase3_adapter.py` — regression guards for all 5 Phase 3 SCs plus the order-sensitive guardrail-before-emptiness check; Phase 4 must not modify this file (any future changes to `AnthropicMGTIClient.complete()` will be regression-tested by this gate)
- `src/llm/anthropic_mgti.py::classify_with_tool` — still a `NotImplementedError` stub, intentionally; Phase 4 implements strict-tools here and adds its own pytest module
- Combined Phase 1+2+3 baseline: 39 tests, ~8 seconds — Phase 4's gate adds to this and continues the cumulative count pattern

Phase 4 prereqs satisfied:
- AnthropicMGTIClient.complete() returns text reliably (LLMSchemaError/LLMGuardrailError surface, not silent failures)
- LLMSchemaError can be raised from classify_with_tool when strict-tools JSON doesn't validate — error class already wired
- Logging hook (`_log_llm_call`) ready to add `llm_tool_name` extra field when Phase 4 lands

---
*Phase: 03-anthropic-mgti-adapter*
*Completed: 2026-05-21*
