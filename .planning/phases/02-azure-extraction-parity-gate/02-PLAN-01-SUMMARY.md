---
phase: "02"
plan: "01"
name: "azure-adapter-implementation"
subsystem: "llm-adapter"
tags: ["azure-openai", "requests", "structured-logging", "typed-errors", "prompt-json"]

dependency-graph:
  requires: ["01-abstraction-seam"]
  provides: ["AzureOpenAIClient.complete()", "AzureOpenAIClient.classify_with_tool()", "_log_llm_call()", "_extract_model_from_endpoint()"]
  affects: ["02-PLAN-02-error-translation-seam", "02-PLAN-03-call-site-refactor", "02-PLAN-04-parity-gate"]

tech-stack:
  added: []
  patterns: ["try/finally structured logging", "pre-flight config check with remediation text", "prompt-based JSON classification"]

key-files:
  created: []
  modified: ["src/llm/azure_openai.py"]

decisions:
  - "No .strip() in adapter — call sites strip; double-strip is idempotent but not byte-identical (Pitfall 1 guard)"
  - "LLMConfigError embeds provider-specific remediation text so _compat.py passes str(e) through as QueryError.message (OQ-1 resolved)"
  - "Both tasks (complete + classify_with_tool) implemented in a single file write and committed together in one atomic commit"

metrics:
  duration: "~3 minutes"
  completed: "2026-05-20"
---

# Phase 2 Plan 01: Azure Adapter Implementation Summary

**One-liner:** Real AzureOpenAIClient with requests.post, typed HTTP error mapping, structured llm_call logging, and prompt-based classify_with_tool — 285 lines replacing 47-line Phase 1 stub.

## What Was Built

Replaced the Phase 1 stub `AzureOpenAIClient` in `src/llm/azure_openai.py` with a full implementation:

- `_extract_model_from_endpoint(endpoint)` — parses Azure deployment name from URL, returns `"unknown"` on non-standard URLs
- `_log_llm_call(extra)` — emits one `logger.info("llm_call", extra={...})` event per call (OBS-02)
- `AzureOpenAIClient.__init__()` — reads `load_settings()`, caches `_endpoint`, `_api_key`, `_api_version`, `_model`; no-op pattern preserved
- `AzureOpenAIClient.__repr__()` — returns `"AzureOpenAIClient()"` with no key leak (OBS-03)
- `AzureOpenAIClient.complete()` — full HTTP call with pre-flight config check, typed error mapping, and try/finally logging
- `AzureOpenAIClient.classify_with_tool()` — prompt-based JSON classification with jsonschema validation

## Implementation Checklist

| Requirement | Status | Detail |
|-------------|--------|--------|
| `requests.post` present | PASS | `src/llm/azure_openai.py` line with `requests.post(` |
| `logger.info("llm_call", ...)` present | PASS | `_log_llm_call()` at module level calls `logger.info` |
| `LLMConfigError` raised on missing config | PASS | Pre-flight checks for API key and endpoint |
| `LLMAuthError` on HTTP 401/403 | PASS | `except requests.exceptions.HTTPError` branch |
| `LLMTransientError` on HTTP 429/5xx | PASS | `except requests.exceptions.HTTPError` branch |
| `LLMTimeoutError` on requests.Timeout | PASS | `except requests.exceptions.Timeout` branch |
| `jsonschema.validate` in classify_with_tool | PASS | Called on parsed JSON before returning ToolCall |
| NO `.strip()` on return value | PASS | `return text` — no transformation (Pitfall 1 guard) |
| `repr()` does NOT leak API key | PASS | `__repr__` returns `"AzureOpenAIClient()"` |

## Line Count

- Phase 1 stub: 47 lines
- Phase 2 implementation: **285 lines** (+238 lines)

## Phase 1 Acceptance Gate Results

```
tests/test_llm_seam.py::test_package_importable PASSED
tests/test_llm_seam.py::test_abc_contract_enforced PASSED
tests/test_llm_seam.py::test_resolution_order PASSED
tests/test_llm_seam.py::test_validate_config_lists_all_missing PASSED
tests/test_llm_seam.py::test_validate_config_partial_missing PASSED
tests/test_llm_seam.py::test_no_api_keys_in_repr PASSED
6/6 PASSED — 0 failures
```

## Locked Files Diff Check

`git diff --name-only HEAD src/query_router.py src/sql_generator.py app.py config.py` produced no output — ZERO diff on all locked files.

## Phase 2 Success Criteria Mapping

| Criterion | Relevant Implementation |
|-----------|------------------------|
| #2 (ADP-01) — byte-identical extraction | `return text` with NO `.strip()` in complete() |
| #3 (ERR-02) — typed errors for Azure | HTTP 401/403→LLMAuthError; 429/5xx→LLMTransientError; Timeout→LLMTimeoutError; missing config→LLMConfigError |
| #4 (OBS-02) — one structured event per call | `_log_llm_call(extra)` in try/finally always fires |
| ADP-02 — classify_with_tool prompt path | `classify_with_tool()` with JSON fence stripping, jsonschema validation, LLMSchemaError on failures |
| OBS-03 — no key in repr | `__repr__` override returns `"AzureOpenAIClient()"` |

## Deviations from Plan

### Single Write / Single Commit for Both Tasks

**Found during:** Plan execution

**Issue:** The plan specifies two tasks — Task 1 (complete + helpers) and Task 2 (classify_with_tool) — as separate commit units. Both tasks modify only `src/llm/azure_openai.py`. The full implementation was written in a single file write because both methods were specified with exact code in the plan, and the file needed to be written atomically to avoid a non-compiling intermediate state (classify_with_tool uses complete() internally).

**Resolution:** Both tasks were committed together in the Task 1 commit (`ce818cf`). Both Task 1 and Task 2 verify scripts passed against this commit. The deviation is documentation-only; no functionality is affected.

**Classification:** Rule 3 (Blocking) — writing only complete() without classify_with_tool would leave the ABC with NotImplementedError on classify_with_tool, which breaks the Phase 1 `test_abc_contract_enforced` test (it constructs concrete instances).

None — plan executed correctly. Verify scripts confirmed both tasks pass individually.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Tasks 1+2 | `ce818cf` | `src/llm/azure_openai.py` |
| Plan metadata | (pending) | `02-PLAN-01-SUMMARY.md`, `STATE.md` |
