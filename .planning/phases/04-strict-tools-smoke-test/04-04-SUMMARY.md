---
phase: 04-strict-tools-smoke-test
plan: "04"
subsystem: testing
tags: [pytest, anthropic-mgti, strict-tools, tool-use, jsonschema, compat-dispatch, smoke-script]

# Dependency graph
requires:
  - phase: 04-01
    provides: INTENT_TOOL constant + ClassificationResultV1 + query_router classify_intent migration
  - phase: 04-02
    provides: AnthropicMGTIClient.classify_with_tool + _post_messages + text-mode fallback
  - phase: 04-03
    provides: scripts/smoke_llm.py operator smoke gate
provides:
  - tests/test_phase4_strict_tools.py — 30-test self-contained pytest module proving all 5 Phase 4 SCs
  - SC #1–5 fully proven by named test functions; Phase 4 gate is green
  - COMPAT-DISPATCH pair locking LLMSchemaError + LLMGuardrailError → Anthropic-named QueryError
  - 9-row error matrix fully covered by test_errmatrix_* + SC-overlap tests
affects:
  - phase-05-sidebar-ui (unblocked by this gate)
  - future adapter additions (COMPAT-DISPATCH pattern established for catch-all LLMError dispatch)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_RecordCapturer pattern (Phase 3/4 idiom): subclass logging.Handler, override emit(), addHandler in test body, removeHandler in finally — no global logger mutation"
    - "Inline mock-response builder pattern: _make_tool_use_response, _make_text_response, _make_guardrail_response, _make_error_envelope_response — NO fixture files"
    - "COMPAT-DISPATCH test pattern: raise typed LLMError inside llm_to_query_error() context, assert QueryError.message == provider-specific label"
    - "SC #5 verification: os.path.exists + py_compile.compile(doraise=True) — never subprocess.run the script"
    - "Level A patching: patch('src.llm.anthropic_mgti.requests.post', return_value=mock) for adapter-direct tests"

key-files:
  created:
    - tests/test_phase4_strict_tools.py
  modified: []

key-decisions:
  - "Test module is self-contained — NO conftest.py, NO pytest.ini, NO new tests/fixtures/ files (matches Phase 1/2/3 acceptance-gate pattern across all four phases)"
  - "Inline mock-response builders used INSTEAD of fixture files — Phase 4 has no parity baseline; RESEARCH.md 'Mock Response Builder Pattern' applied"
  - "_RecordCapturer mirrors tests/test_phase3_adapter.py:412-420 VERBATIM — subclass logging.Handler, override emit()"
  - "COMPAT-DISPATCH covers LLMSchemaError + LLMGuardrailError (Phase 3 covered LLMAuthError + LLMTimeoutError); no _compat.py edits needed — catch-all LLMError branch already dispatches by e.provider"
  - "SC #4 test patches classify_with_tool to inject chart_requested=True into call.input, then asserts classify_intent's output reads from heuristic locals (False) not call.input — TOOL-04 regression guard"
  - "precondition test test_precondition_jsonschema_version is first non-fixture test — self-documenting dev-box pin guard"
  - "Combined suite: 39 (prior phases) + 30 (Phase 4) = 69 tests, all passing"

patterns-established:
  - "Phase acceptance gate: one self-contained pytest module per phase, no shared fixtures, all mocks inline"
  - "Per-plan commitment: one atomic commit per task with format test(XX-YY): {description}"

# Metrics
duration: 4min
completed: 2026-05-21
---

# Phase 4 Plan 04: Acceptance Gate Summary

**30-test self-contained pytest module proving all 5 Phase 4 SCs: INTENT_TOOL derivation invariants, strict-tools request shape + response handling, text-mode fallback path, heuristic-merge regression lock, and smoke script syntax gate**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-21T19:03:56Z
- **Completed:** 2026-05-21T19:08:39Z
- **Tasks:** 1 (1 task, 1 atomic commit)
- **Files modified:** 1

## Accomplishments

- Created `tests/test_phase4_strict_tools.py` (869 lines, 30 tests) proving all 5 Phase 4 ROADMAP success criteria
- Covered all 9 CONTEXT.md classify_with_tool error matrix rows via named test functions
- Established COMPAT-DISPATCH pair for LLMSchemaError + LLMGuardrailError (complementing Phase 3's LLMAuthError + LLMTimeoutError pair)
- Combined Phase 1+2+3+4 suite: 69 tests, all green, 8.05s, zero live HTTP

## Task Commits

1. **Task 4.1: Write tests/test_phase4_strict_tools.py** - `9bc5e49` (test)

**Plan metadata:** (docs commit below)

## SC-to-Test Mapping

| SC | Test functions | Count |
|----|---------------|-------|
| SC #1 — INTENT_TOOL derivation | test_sc1_intent_tool_is_a_toolschema_with_correct_name, test_sc1_intent_tool_properties_match_dataclass_fields, test_sc1_intent_tool_intent_is_enum_constraint, test_sc1_intent_tool_version_is_plain_string, test_sc1_intent_tool_excludes_chart_fields, test_sc1_intent_tool_locks_down_additional_properties | 6 |
| SC #2 — strict-tools path | test_sc2_strict_tools_request_body_shape, test_sc2_strict_tools_valid_response_returns_toolcall, test_sc2_mixed_text_and_tool_use_blocks_handled | 3 |
| SC #3 — text-mode fallback | test_sc3_tools_supported_false_triggers_text_mode, test_sc3_text_mode_strips_markdown_fences, test_sc3_text_mode_invalid_json_raises_schema_error | 3 |
| SC #4 — heuristic merge | test_sc4_heuristic_chart_request_not_overwritten_by_llm | 1 |
| SC #5 — smoke script | test_sc5_smoke_script_exists, test_sc5_smoke_script_syntax_valid | 2 |

## Error Matrix Coverage

| Row | Test function |
|-----|--------------|
| HTTP 401/403 → LLMAuthError | test_errmatrix_http_401_raises_auth_error |
| guardrail_intervened → LLMGuardrailError | test_errmatrix_guardrail_intervened_raises_guardrail_error |
| HTTP 500 → LLMTransientError | test_errmatrix_http_500_raises_transient_error |
| missing tool_use block → LLMSchemaError | test_errmatrix_no_tool_use_block_raises_schema_error |
| wrong tool name → LLMSchemaError | test_errmatrix_wrong_tool_name_raises_schema_error |
| malformed input not dict → LLMSchemaError | test_errmatrix_malformed_input_not_dict_raises_schema_error |
| jsonschema validation failure → LLMSchemaError | test_errmatrix_schema_validation_failure_raises_schema_error |
| max_tokens during tool_use → LLMSchemaError | test_errmatrix_max_tokens_during_tool_use_raises_schema_error |
| unknown stop_reason → LLMSchemaError | test_errmatrix_unknown_stop_reason_raises_schema_error |

## COMPAT-DISPATCH Coverage

| Error type | Test function | Expected QueryError.message |
|-----------|--------------|----------------------------|
| LLMSchemaError(provider='anthropic_mgti') | test_compat_dispatch_schema_error_translates_to_anthropic_query_error | "Anthropic API call failed" |
| LLMGuardrailError(provider='anthropic_mgti') | test_compat_dispatch_guardrail_error_translates_to_anthropic_query_error | "Anthropic API call failed" |

Both test the catch-all `except LLMError` branch in `_compat.py` dispatching by `e.provider`. Phase 3's COMPAT-DISPATCH covered LLMAuthError and LLMTimeoutError (dedicated branches). Phase 4's pair exercises the same regression guard — neither surfaces as "Azure OpenAI API call failed".

## Log-Event Assertions

| Test function | What is asserted |
|--------------|-----------------|
| test_logs_startup_log_contains_tools_supported | llm_provider_loaded event has tools_supported: True for TOOLS_SUPPORTED=true env |
| test_logs_classify_with_tool_strict_path_emits_one_event_with_llm_tool_mode_strict | strict path emits exactly 1 llm_call with llm_tool_mode='strict' |
| test_logs_classify_with_tool_text_fallback_emits_one_event_with_llm_tool_mode_text_fallback | text-fallback path emits exactly 1 llm_call with llm_tool_mode='text_fallback' (delegate's complete() suppressed via _emit_log=False) |

## Files Created/Modified

- `tests/test_phase4_strict_tools.py` — Phase 4 acceptance gate, 30 tests, 869 lines, self-contained

## Decisions Made

- Test module self-contained — no conftest.py, no pytest.ini, no new tests/fixtures/ files (matches Phase 1/2/3 acceptance-gate pattern; four phases consistent now)
- Inline mock-response builders used INSTEAD of fixture files — RESEARCH.md "Mock Response Builder Pattern" applied
- _RecordCapturer mirrors test_phase3_adapter.py:412-420 VERBATIM — locked decision §3 (subclass logging.Handler, override emit())
- COMPAT-DISPATCH tests cover LLMSchemaError + LLMGuardrailError — no _compat.py edits needed; the catch-all `except LLMError` branch already dispatches by e.provider since Phase 3
- SC #4 test patches `get_llm` and `classify_with_tool` to inject chart_requested=True into ToolCall.input, then asserts classify_intent reads from heuristic locals — strongest possible TOOL-04 regression test without live HTTP
- jsonschema 4.26.0 confirmed installed before writing (precondition verified)

## Deviations from Plan

None — plan executed exactly as written. All 30 tests passed on first run.

## Issues Encountered

None.

## Combined Suite Result

```
39 (Phase 1+2+3) + 30 (Phase 4) = 69 passed in 8.05s
```

Zero live HTTP. Zero conftest.py. Zero pytest.ini. Zero fixture files in tests/fixtures/.

## Phase 4 Sign-Off

All 5 ROADMAP success criteria proven. Anthropic strict-tools + text-mode fallback + operator-run smoke gate shipped. `classify_intent` uses provider-side strict tools when `ANTHROPIC_TOOLS_SUPPORTED=true` and JSON-parse fallback when `false`; heuristic-merge regression locked by SC #4 test; COMPAT-DISPATCH pair guarantees Anthropic errors carry the correct product label through the UI layer. **Phase 5 (Sidebar UI Toggle) is unblocked pending operator-run smoke gate against stage gateway.**

## Pending Operator Action

Set `.env` with stage gateway URLs + valid keys, then run:

```bash
python scripts/smoke_llm.py --provider both --verbose
```

Paste the transcript into the Phase 4 verification PR. Without this, Phase 5 work should not begin (per SMK-05 / CONTEXT.md §Smoke script credential).

---
*Phase: 04-strict-tools-smoke-test*
*Completed: 2026-05-21*
