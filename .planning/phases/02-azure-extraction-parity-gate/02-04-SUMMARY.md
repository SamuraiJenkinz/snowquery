---
phase: 02-azure-extraction-parity-gate
plan: "04"
subsystem: testing
tags: [pytest, fixtures, parity-gate, azure-openai, logging, mocking]

# Dependency graph
requires:
  - phase: 02-01
    provides: AzureOpenAIClient with complete(), typed errors, _log_llm_call()
  - phase: 02-02
    provides: llm_to_query_error() context-manager error-translation seam
  - phase: 02-03
    provides: All three call sites (classify_intent, generate_sql, generate_executive_summary) wired through the seam
provides:
  - "tests/test_phase2_parity.py — 12-test Phase 2 acceptance gate (pytest)"
  - "tests/fixtures/parity/ — five synthetic Azure response fixtures (q1-q5)"
  - "Executable proof of all four Phase 2 ROADMAP success criteria"
affects: [03-anthropic-mgti-adapter, future-phases]

# Tech tracking
tech-stack:
  added: [chromadb (installed — required by src/query_router transitive import chain)]
  patterns:
    - "Five-fixture parity gate: synthetic Azure response JSON fixtures + requests.post mock = offline byte-identity assertion"
    - "Level A patching (requests.post) for adapter-direct parity; Level B (factory cache injection) for call-site error-translation isolation"
    - "logging.Handler subclass (_RecordCapturer) to capture structured log events without mutating global logger state"

key-files:
  created:
    - tests/test_phase2_parity.py
    - tests/fixtures/parity/q1_structured_classification.json
    - tests/fixtures/parity/q2_semantic_classification.json
    - tests/fixtures/parity/q3_hybrid_classification.json
    - tests/fixtures/parity/q4_sql_generation.json
    - tests/fixtures/parity/q5_exec_summary.json
  modified: []

key-decisions:
  - "Test module is self-contained — no conftest.py or pytest.ini added (matches Phase 1 gate pattern)"
  - "Level A (requests.post mock) used for adapter-direct parity tests; Level B (factory cache injection) used for error-translation tests — separation of concerns"
  - "CS3 (generate_executive_summary) tested to silently return None on LLM error — INTENTIONAL invariant (RESEARCH.md Pitfall 4), not a bug"
  - "chromadb installed (Rule 3 blocker: src/query_router imports src.semantic_search which imports chromadb at module level)"

patterns-established:
  - "Acceptance gate pattern: one pytest module per phase, each test maps to one numbered ROADMAP success criterion"
  - "Parity fixture pattern: JSON files in tests/fixtures/parity/ contain request_messages (docs) + response_json (mock body); Q1-Q4 have JSON-parseable content, Q5 free text"

# Metrics
duration: 6min
completed: 2026-05-20
---

# Phase 2 Plan 4: Acceptance Gate Summary

**Pytest acceptance gate proving Azure adapter extraction is byte-identical across five representative queries (structured/semantic/hybrid/SQL/summary) plus error translation and structured log event shape**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-20T18:14:41Z
- **Completed:** 2026-05-20T18:20:40Z
- **Tasks:** 2
- **Files created:** 6 (1 test module + 5 fixture files)
- **Files modified:** 0 (LOCKED — test-only plan)

## Accomplishments

- Created five synthetic Azure response fixtures covering all three call-site paths (CS1 classify_intent, CS2 generate_sql, CS3 generate_executive_summary)
- Built 12-test acceptance gate with zero live HTTP calls — all `requests.post` calls mocked via `unittest.mock.patch`
- All four Phase 2 ROADMAP success criteria proven by executable tests — Phase 2 is DONE

## Test Results

### Phase 2 acceptance gate
```
pytest tests/test_phase2_parity.py -v
============================= 12 passed in 8.40s =============================
```

All 12 tests passed:
```
tests/test_phase2_parity.py::test_call_azure_openai_eliminated PASSED
tests/test_phase2_parity.py::test_parity_q1_structured PASSED
tests/test_phase2_parity.py::test_parity_q2_semantic PASSED
tests/test_phase2_parity.py::test_parity_q3_hybrid PASSED
tests/test_phase2_parity.py::test_parity_q4_sql_generation PASSED
tests/test_phase2_parity.py::test_parity_q5_exec_summary PASSED
tests/test_phase2_parity.py::test_parity_end_to_end_classify_intent PASSED
tests/test_phase2_parity.py::test_parity_end_to_end_generate_sql PASSED
tests/test_phase2_parity.py::test_parity_end_to_end_exec_summary PASSED
tests/test_phase2_parity.py::test_error_translation_at_call_site PASSED
tests/test_phase2_parity.py::test_log_event_shape PASSED
tests/test_phase2_parity.py::test_log_event_on_error_path PASSED
```

### Phase 1 acceptance gate (still green)
```
pytest tests/test_llm_seam.py -v
============================== 6 passed in 0.78s ==============================
```

### Combined run
```
pytest tests/ -v
============================= 18 passed in 8.56s ==============================
```

## Success Criteria Coverage

| Phase 2 ROADMAP Criterion | Test Function(s) | Result |
|--------------------------|-----------------|--------|
| #1 — `_call_azure_openai` eliminated + DI at all 3 call sites (ABS-06) | `test_call_azure_openai_eliminated` | PASS |
| #2 — Byte-identical extraction, adapter-direct (ADP-01) | `test_parity_q1_structured`, `test_parity_q2_semantic`, `test_parity_q3_hybrid`, `test_parity_q4_sql_generation`, `test_parity_q5_exec_summary` | PASS |
| #2 — Byte-identical extraction, full call-site chain | `test_parity_end_to_end_classify_intent`, `test_parity_end_to_end_generate_sql`, `test_parity_end_to_end_exec_summary` | PASS |
| #3 — LLMError → QueryError at call-site boundary (ERR-04); CS1+CS2+CS3 | `test_error_translation_at_call_site` | PASS |
| #4 — One structured log event per call, full OBS-02 field shape | `test_log_event_shape`, `test_log_event_on_error_path` | PASS |

## Task Commits

Each task was committed atomically:

1. **Task 1: Create five parity fixtures** — `e890c43` (test)
2. **Task 2: Create tests/test_phase2_parity.py** — `2a99e2a` (test)

**Plan metadata:** (pending — docs commit)

## Files Created

- `tests/test_phase2_parity.py` — 12-test Phase 2 acceptance gate; 499 lines
- `tests/fixtures/parity/q1_structured_classification.json` — CS1 structured intent fixture (312 prompt_tokens, 52 completion_tokens)
- `tests/fixtures/parity/q2_semantic_classification.json` — CS1 semantic intent fixture
- `tests/fixtures/parity/q3_hybrid_classification.json` — CS1 hybrid intent fixture (P1 filter + similarity)
- `tests/fixtures/parity/q4_sql_generation.json` — CS2 SQL generation fixture (max_tokens=1000 load-bearing)
- `tests/fixtures/parity/q5_exec_summary.json` — CS3 free-text executive summary fixture

## Decisions Made

- Test module is self-contained — no `conftest.py` or `pytest.ini` added, matching Phase 1 gate pattern
- Level A patching (`requests.post`) used for adapter-direct parity tests (exercises real AzureOpenAIClient end-to-end); Level B (factory cache injection via `_cache["azure_openai"] = MagicMock(...)`) used for error-translation tests (isolates call-site `llm_to_query_error()` behavior from adapter HTTP behavior)
- CS3 (`generate_executive_summary`) intentionally tested to return `None` on LLM error — this is the RESEARCH.md Pitfall 4 invariant; the broad `except Exception: return None` was present before Phase 2 and must remain
- `chromadb` installed via `pip install chromadb` — it was already in `requirements.txt` but not present in the test environment (Rule 3 blocking deviation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing chromadb dependency**

- **Found during:** Task 2 (first pytest run)
- **Issue:** `src/query_router.py` imports `from src.semantic_search import semantic_query` at module level; `semantic_search.py` imports `chromadb` at module level; `chromadb` was in `requirements.txt` but not installed in the test environment
- **Fix:** Ran `pip install chromadb` (it was already declared in requirements.txt — this was an environment gap, not a missing declaration)
- **Files modified:** None (environment-only fix)
- **Verification:** `python -c "import chromadb; print('OK')"` → OK; all 4 previously-failing tests subsequently passed
- **Committed in:** Part of Task 2 commit `2a99e2a` (environment fix, not a code change)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing installed dependency)
**Impact on plan:** No source file changes; chromadb was already declared in requirements.txt. Zero scope creep.

## Issues Encountered

- First pytest run showed 4/12 failing with `ModuleNotFoundError: No module named 'chromadb'`. The module is declared in `requirements.txt` but was not present in the test runner environment. Installed via pip; all 4 tests passed after install. The Phase 1 gate tests avoided this because they only import from `src.llm.*`, never `src.query_router`.

## Source Files Modified

None. Confirmed via `git diff --name-only HEAD src/ app.py config.py` → empty output. This plan added ONLY test files.

## Phase 2 Sign-Off

Phase 2 (Azure Extraction + Parity Gate) is complete. The parity gate is green — Azure adapter extraction is verified byte-identical against five representative queries spanning all three call sites (CS1 `classify_intent`, CS2 `generate_sql`, CS3 `generate_executive_summary`). All four ROADMAP success criteria are proven by executable tests that run offline with zero live HTTP calls. Phase 3 (Anthropic MGTI Adapter) is unblocked.

---
*Phase: 02-azure-extraction-parity-gate*
*Completed: 2026-05-20*
