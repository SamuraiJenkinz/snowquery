---
phase: 01-abstraction-seam
plan: "03"
subsystem: testing
tags: [pytest, abc, dataclasses, env-var, repr-safety, acceptance-gate]

# Dependency graph
requires:
  - phase: 01-01
    provides: "LLMClient ABC, error hierarchy, frozen+slots types (ToolSchema, ToolCall, ClassificationResultV1, IntentResult)"
  - phase: 01-02
    provides: "LLMSettings, load_settings, validate_config, get_llm factory, _cache, AzureOpenAIClient stub, AnthropicMGTIClient stub"
provides:
  - "tests/test_llm_seam.py — 6-test pytest acceptance gate proving all 5 Phase 1 success criteria"
  - "Phase 1 sign-off: seam is mechanically verified and stable for Phase 2"
affects: [02-azure-extraction, 03-anthropic-adapter, 04-intent-tool, 05-ui-provider-switch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Autouse fixture clears module-level _cache between tests to prevent state bleed"
    - "Autouse monkeypatch fixture strips all LLM env vars per test for clean slate"
    - "Sentinel strings (DO_NOT_LEAK) pattern for repr-safety regression testing"

key-files:
  created:
    - tests/test_llm_seam.py
  modified: []

key-decisions:
  - "pytest already installed (9.0.2) — no install required, no requirements.txt change needed"
  - "tests/ directory created as first test artifact for the project"
  - "No __init__.py added to tests/ — pytest discovers test_*.py by collection without it"

patterns-established:
  - "Acceptance gate pattern: one pytest module per phase proving each numbered success criterion"
  - "Cache-clear autouse fixture: required whenever module-level singletons persist between tests"

# Metrics
duration: 5min
completed: 2026-05-19
---

# Phase 01 Plan 03: Smoke Verification Summary

**6-test pytest acceptance gate mechanically proving all 5 Phase 1 success criteria: importability, ABC contract, factory resolution order + cache idempotence, validate_config full-list, and repr-safety sentinel guard across LLMSettings/LLMConfigError/stub clients**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-19T23:18:00Z (approx)
- **Completed:** 2026-05-19T23:23:35Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments

- Created `tests/test_llm_seam.py` (294 lines) — the project's first test file
- All 6 tests pass in 0.42s with zero live HTTP calls
- Phase 1 (Abstraction Seam) is mechanically signed off

## Pytest Results

```
Command: python -m pytest tests/test_llm_seam.py -v
Exit code: 0

tests/test_llm_seam.py::test_package_importable                    PASSED
tests/test_llm_seam.py::test_abc_contract_enforced                 PASSED
tests/test_llm_seam.py::test_resolution_order                      PASSED
tests/test_llm_seam.py::test_validate_config_lists_all_missing     PASSED
tests/test_llm_seam.py::test_validate_config_partial_missing       PASSED
tests/test_llm_seam.py::test_no_api_keys_in_repr                   PASSED

============================== 6 passed in 0.42s ==============================
```

## Success Criteria Mapping

| Success Criterion | Test Function | Result |
|---|---|---|
| #1 — package importable (ABS-01) | `test_package_importable` | PASSED |
| #2 — ABC contract enforced (ABS-02) | `test_abc_contract_enforced` | PASSED |
| #3 — factory + cache + resolution order (ABS-04, CFG-05) | `test_resolution_order` | PASSED |
| #4a — validate_config lists ALL missing vars (CFG-03) | `test_validate_config_lists_all_missing` | PASSED |
| #4b — validate_config walks full list, not fail-on-first (CFG-03) | `test_validate_config_partial_missing` | PASSED |
| #5 — no API keys in repr/log output (OBS-03) | `test_no_api_keys_in_repr` | PASSED |

## Task Commits

1. **Task 1: Create tests/test_llm_seam.py** — `8e0d2dc` (test)

## Files Created/Modified

- `tests/test_llm_seam.py` — 6-test Phase 1 acceptance gate (294 lines)

## Offline Verification

The test suite makes zero live external calls. Confirmed by:
- No `import requests` anywhere in the file
- No MGTI URLs referenced
- No HTTP-related imports at all
- All assertions operate on: ABC machinery, `repr()` output, `os.environ` manipulation via `monkeypatch`, and `isinstance` checks

## Locked Files Sanity Check

```
Command: git diff --name-only HEAD src/query_router.py src/sql_generator.py app.py config.py 2>&1 | grep -E '(query_router|sql_generator|^app\.py|^config\.py)$' && echo "LOCKED FILE TOUCHED" || echo "all locked files intact"
Result: all locked files intact
```

No LOCKED file (`app.py`, `config.py`, `src/query_router.py`, `src/sql_generator.py`) was modified by any Phase 1 plan.

## Decisions Made

- pytest 9.0.2 was already installed in the environment — no installation step was needed and no `requirements.txt` change was made (pytest remains dev-only)
- `tests/` directory created without `__init__.py` — pytest discovers `test_*.py` files by collection without it
- Plan file contents were used exactly as specified — no test bodies improvised

## Deviations from Plan

None — plan executed exactly as written. The seam built in Plans 01 and 02 passed all assertions on the first run without any fix commits needed.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. Tests run entirely offline.

## Phase 1 Sign-Off

**Phase 1 (Abstraction Seam) is complete.** All five ROADMAP.md success criteria are now proven by an executable pytest gate that runs in 0.42s with no live dependencies. The seam is stable:

- `LLMClient` ABC enforces the two-method contract at construction time
- `get_llm()` factory resolves provider via kwarg > session > env > `"azure_openai"` default and returns the same cached instance on repeat calls
- `validate_config()` surfaces the complete list of missing env vars in one error, not fail-on-first
- All `api_key` fields are excluded from `repr()` across `LLMSettings`, `LLMConfigError`, and both stub clients
- `ClassificationResultV1` excludes chart fields (heuristic domain), `IntentResult` carries them

The seam is stable for Phase 2 to plug `AzureOpenAIClient` into.

---
*Phase: 01-abstraction-seam*
*Completed: 2026-05-19*
