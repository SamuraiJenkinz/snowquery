---
phase: "02"
status: passed
score: "4/4"
date: 2026-05-20
---

# Phase 2: Azure Extraction + Parity Gate -- Verification Report
**Phase Goal:** Extract the duplicated _call_azure_openai logic into AzureOpenAIClient
and route the three call sites through LLMClient, with a hard verification step that
5-10 representative queries produce byte-identical output to the pre-refactor baseline.

**Verified:** 2026-05-20
**Status:** PASSED
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | _call_azure_openai gone; all 3 call sites use get_llm() + llm_to_query_error() | VERIFIED | grep returns zero hits; DI imports confirmed in query_router.py (lines 13-14, 137-138, 501-502) and sql_generator.py (lines 18-19, 142-143) |
| 2 | 5 parity fixtures exist and 12/12 acceptance tests pass | VERIFIED | pytest tests/test_phase2_parity.py -v -> 12 passed in 8.57s |
| 3 | LLMError subclasses translate to QueryError at call-site boundary | VERIFIED | _compat.py covers all 5 error types; test_error_translation_at_call_site passes |
| 4 | Adapter emits one structured log event per call with all OBS-02 fields | VERIFIED | _log_llm_call() at azure_openai.py:52; test_log_event_shape and test_log_event_on_error_path pass |

**Score: 4/4 truths verified**

---

## Per-Criterion Verification

### SC#1 -- Deletion + Dependency Injection (ABS-06)

What was checked:

- grep -n _call_azure_openai against src/query_router.py and src/sql_generator.py -> zero hits
- src/query_router.py lines 13-14: from src.llm import get_llm and from src.llm._compat import llm_to_query_error present
- src/sql_generator.py lines 18-19: same imports present
- Call site 1 (classify_intent, query_router.py:137-139): client = get_llm() / with llm_to_query_error(): / client.complete(messages, max_tokens=500).strip()
- Call site 2 (generate_executive_summary, query_router.py:501-503): same DI pattern, max_tokens=500
- Call site 3 (generate_sql, sql_generator.py:142-144): same DI pattern, max_tokens=1000
- test_call_azure_openai_eliminated asserts source-level absence and DI presence via inspect.getsource; passes

**Status: PASS**

---
### SC#2 -- Five-Fixture Parity Gate (ADP-01)

What was checked:

- Five fixture files confirmed present: q1_structured_classification.json, q2_semantic_classification.json, q3_hybrid_classification.json, q4_sql_generation.json, q5_exec_summary.json in tests/fixtures/parity/
- Fixtures cover all three call-site paths: structured/semantic/hybrid classification (CS1, max_tokens=500), SQL generation (CS2, max_tokens=1000), executive summary (CS3, free text)
- Adapter-level parity: client.complete() returns choices[0].message.content verbatim without stripping for all five fixtures
- Call-site-level parity: three end-to-end tests verify that .strip() + JSON parse downstream produces byte-identical results
- test_parity_q4_sql_generation additionally asserts request body max_tokens == 1000 (load-bearing CS1/CS2 difference)
- All 8 parity tests pass

**Status: PASS**

---
### SC#3 -- Error Contract Preserved (ERR-04)

What was checked:

- src/llm/_compat.py read in full: catches LLMConfigError (passes str(e) through as QueryError.message), LLMAuthError (historic Azure key-not-configured text), LLMTimeoutError -> QueryError(Azure OpenAI API call failed, str(e)), LLMTransientError -> same, LLMError catch-all -> same; subclass order is correct
- with llm_to_query_error(): confirmed wrapping client.complete() at all three call sites
- test_error_translation_at_call_site verifies all four LLMError variants at CS1 plus LLMTimeoutError and LLMTransientError at CS2 produce Azure OpenAI API call failed (NOT Failed to generate SQL, confirming no leak past compat into CS2 broad-except); CS3 returns None silently
- All sub-assertions pass

**Status: PASS**

---
### SC#4 -- Structured Logging (OBS-02)

What was checked:

- src/llm/azure_openai.py:52-64: _log_llm_call() helper exists, calls logger.info(llm_call, extra=extra)
- extra dict at lines 143-152 contains: llm_provider, llm_model, llm_latency_ms, llm_outcome, llm_error_type, llm_prompt_tokens, llm_completion_tokens, llm_correlation_id
- finally block at lines 210-212 guarantees emission on both success and error paths
- test_log_event_shape asserts exactly 1 llm_call event with all OBS-02 fields at correct values (llm_prompt_tokens==312, llm_completion_tokens==52, llm_model==gpt-4o-mini from q1 fixture, llm_correlation_id is None)
- test_log_event_on_error_path asserts llm_outcome==error, llm_error_type==LLMTimeoutError, token counts None on timeout
- Both tests pass

**Status: PASS**

---
## Test Results

### Phase 2 Acceptance Gate

```
pytest tests/test_phase2_parity.py -v
============================= 12 passed in 8.57s ==============================

test_call_azure_openai_eliminated       PASSED
test_parity_q1_structured               PASSED
test_parity_q2_semantic                 PASSED
test_parity_q3_hybrid                   PASSED
test_parity_q4_sql_generation           PASSED
test_parity_q5_exec_summary             PASSED
test_parity_end_to_end_classify_intent  PASSED
test_parity_end_to_end_generate_sql     PASSED
test_parity_end_to_end_exec_summary     PASSED
test_error_translation_at_call_site     PASSED
test_log_event_shape                    PASSED
test_log_event_on_error_path            PASSED
```

---

## Phase 1 Regression Check

```
pytest tests/test_llm_seam.py -v
============================== 6 passed in 0.82s ==============================

test_package_importable                 PASSED
test_abc_contract_enforced              PASSED
test_resolution_order                   PASSED
test_validate_config_lists_all_missing  PASSED
test_validate_config_partial_missing    PASSED
test_no_api_keys_in_repr                PASSED
```

No regressions. Phase 1 gate holds 6/6.

---
## Locked Files Check

Files locked in Phase 1: src/llm/__init__.py, src/llm/base.py, src/llm/errors.py, src/llm/types.py, src/llm/config.py. Note: factory.py was integrated into __init__.py in Phase 1; no separate factory.py file exists.

git log b4e1022..HEAD against all locked files -> empty output. None of the locked Phase 1 files were modified by any Phase 2 commit.

**Status: CLEAN**

---

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ABS-06 | SATISFIED | _call_azure_openai eliminated; all 3 call sites use get_llm() |
| ADP-01 | SATISFIED | 5 fixture parity tests pass; adapter returns content verbatim |
| ADP-02 | SATISFIED | classify_with_tool() implemented in azure_openai.py:214-285 (prompt-based JSON) |
| ERR-04 | SATISFIED | llm_to_query_error() translates all 5 LLMError subclasses to QueryError |
| OBS-02 | SATISFIED | _log_llm_call() emits one structured event per call with all required fields |

---

## Status and Rationale

**Status: PASSED**

All four success criteria are demonstrably delivered:

1. _call_azure_openai is confirmed absent from both call-site modules via grep and source inspection; all three call sites use get_llm() + with llm_to_query_error(): with correct max_tokens per call site.
2. Five hand-authored parity fixtures exist covering all three call-site paths; 12/12 acceptance tests pass including both adapter-level and call-site-level parity assertions with the CS1/CS2 max_tokens difference locked down.
3. The error translation seam in _compat.py covers all five LLMError subclasses with the correct historic user-visible message text; the CS2 broad-except regression path is explicitly tested and confirmed sealed.
4. The structured logging helper emits exactly one llm_call event per complete() invocation via the finally block, with all OBS-02 fields present on both success and error paths.

Phase 1 gate holds (6/6). Locked files untouched by Phase 2 commits. Phase 2 is complete and verified.

---

_Verified: 2026-05-20_
_Verifier: Claude (gsd-verifier)_