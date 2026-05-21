---
phase: 04-strict-tools-smoke-test
plan: "02"
subsystem: llm
tags: [anthropic, strict-tools, jsonschema, tool_use, logging, fallback]

# Dependency graph
requires:
  - phase: 03-anthropic-mgti-adapter
    provides: AnthropicMGTIClient with complete() and NotImplementedError classify_with_tool stub
  - phase: 04-strict-tools-smoke-test/04-01
    provides: INTENT_TOOL constant in src/llm/types.py, classify_intent migrated to classify_with_tool

provides:
  - AnthropicMGTIClient.classify_with_tool — full strict-tools implementation (tools + tool_choice)
  - AnthropicMGTIClient._classify_via_text_mode — env-flag-gated text-mode fallback
  - AnthropicMGTIClient._post_messages — shared HTTP + typed-error-mapping helper
  - _emit_log kwarg on complete() for log suppression by text-mode wrapper
  - tools_supported field in llm_provider_loaded startup log

affects:
  - 04-03 (Azure parity plan — may reference _emit_log pattern)
  - 04-04 (acceptance gate — add one test per error-matrix row; delete NotImplementedError-stub test)
  - 05 (smoke test will call classify_with_tool against live MGTI proxy)

# Tech tracking
tech-stack:
  added:
    - "jsonschema>=4.26.0,<5 (upgraded from 4.25.1 — RESEARCH.md Pitfall 4 precondition)"
  patterns:
    - "_post_messages intra-module helper: owns HTTP + 4xx/5xx envelope; shared by both adapter methods"
    - "env-flag-only fallback: self._tools_supported False -> _classify_via_text_mode; NO try-strict-then-retry"
    - "_emit_log: bool = True kwarg on complete() for one-event-per-call in text-mode wrapper path"
    - "Guardrail check BEFORE missing-tool_use check (RESEARCH.md Pitfall 4 order locked)"
    - "Defensive tool_use block iteration (first type==tool_use AND name==tool_name wins)"

key-files:
  created: []
  modified:
    - src/llm/anthropic_mgti.py

key-decisions:
  - "Env-flag-only fallback at entry: self._tools_supported True->strict, False->_classify_via_text_mode; NO try-strict-then-retry"
  - "_post_messages extracted intra-module (NOT to src/llm/_log.py); owns HTTP+errors; does NOT own timing or log emission"
  - "max_tokens during tool_use raises LLMSchemaError (DIVERGES from complete()'s truncated-as-success); message mentions raise ANTHROPIC_MAX_TOKENS"
  - "Guardrail check BEFORE missing-tool_use check: order is guardrail -> max_tokens -> tool_use extraction -> input validation -> schema validation"
  - "Defensive iteration for tool_use blocks even with disable_parallel_tool_use=True; first block with type=='tool_use' AND name==tool_name"
  - "_classify_via_text_mode self-contained in AnthropicMGTIClient; NO cross-adapter import from azure_openai.py"
  - "Log emission asymmetry: _emit_log=False on complete() from text-mode wrapper; wrapper emits ONE event tagged llm_tool_mode='text_fallback'"
  - "tools_supported added at END of llm_provider_loaded extra dict (order-of-definition lock)"

patterns-established:
  - "HTTP helper pattern: _post_messages mutates extra dict in-place so caller's finally block sees enriched log state"
  - "Method-local jsonschema import: lazy import inside classify_with_tool and _classify_via_text_mode (not top-of-module)"

# Metrics
duration: 7min
completed: 2026-05-21
---

# Phase 4 Plan 02: classify-with-tool-strict-tools-and-fallback Summary

**AnthropicMGTIClient.classify_with_tool implemented with Anthropic strict-tools body (tools + tool_choice + disable_parallel_tool_use), 9-row error-matrix coverage, env-flag-gated text-mode fallback, intra-module _post_messages HTTP helper, and one-event-per-call log accounting**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-21T18:45:28Z
- **Completed:** 2026-05-21T18:52:10Z
- **Tasks:** 2 (implemented together in single write; committed as one atomic commit)
- **Files modified:** 1 (src/llm/anthropic_mgti.py)

## Accomplishments

- `_post_messages` private method extracted at line 192: owns `requests.post` + `Timeout`/`RequestException`/`4xx`/`5xx` MGTI envelope parsing + all typed error raises; `complete()` and `classify_with_tool()` both call it (grep -c returns 2)
- `classify_with_tool` (line 462) fully implemented: strict-tools body shape with `tools=[{name,description,input_schema}]` + `tool_choice={type:tool,name,disable_parallel_tool_use:True}`; all 9 error-matrix rows covered with locked check order
- `_classify_via_text_mode` (line 705) implemented: system-prompt injection mirrors `azure_openai.py:254-264`; fence-stripping mirrors `query_router.py:144-148`; produces `ToolCall` indistinguishable from strict path
- `_emit_log: bool = True` kwarg added to `complete()` signature (line 292); gated in `finally:` at line 459; text-mode wrapper passes `_emit_log=False` to suppress delegate's event
- `tools_supported: self._tools_supported` added to `llm_provider_loaded` extra dict (line 184)
- jsonschema upgraded from 4.25.1 → 4.26.0 (requirements.txt pin `>=4.26.0,<5` satisfied)
- Phase 3 acceptance gate: 21/21 tests green; combined suite: 39/39 tests green

## _post_messages helper extraction: line counts

**Before refactor:** `complete()` lines 268-315 (~50 lines) = `requests.post` call + `4xx`/`5xx` envelope block + `LLMAuthError`/`LLMTransientError`/`LLMError` raises; plus lines 405-424 = `Timeout`/`RequestException` except branches on outer try. Total: ~70 lines inline.

**After refactor:** `_post_messages` method at lines 192-285 (~94 lines including docstring). `complete()`'s try block starts with `data = self._post_messages(...)` — removed its Timeout/RequestException except-branches entirely.

## classify_with_tool error-matrix row coverage

| Row | Condition | Error raised | Line approx |
|-----|-----------|-------------|-------------|
| 1 | stop_reason == 'guardrail_intervened' | LLMGuardrailError | ~635 |
| 2 | stop_reason == 'max_tokens' | LLMSchemaError ("raise ANTHROPIC_MAX_TOKENS") | ~645 |
| 3 | No tool_use block with matching name | LLMSchemaError (missing/wrong-name) | ~655 |
| 4 | Wrong tool name returned | LLMSchemaError ("wrong tool name returned") | ~660 |
| 5 | input not a dict | LLMSchemaError ("malformed tool_use input") | ~675 |
| 6 | jsonschema.ValidationError | LLMSchemaError (e.message embedded) | ~685 |
| 7 | unknown stop_reason | LLMSchemaError ("unknown stop_reason") | ~695 |
| 8 | HTTP 401/403 | LLMAuthError | (inside _post_messages) |
| 9 | HTTP 429/5xx / Timeout | LLMTransientError / LLMTimeoutError | (inside _post_messages) |

Critical order lock (locked decision §4): guardrail (1) checked BEFORE missing-tool_use (3). If reversed, guardrail responses (empty content[]) would surface as LLMSchemaError instead of LLMGuardrailError.

## _classify_via_text_mode: mirror points

- System-prompt template (line ~737-744): mirrors `azure_openai.py:254-264` verbatim — "You are calling the tool `{tool.name}`. Respond ONLY with a JSON object matching this schema:..."
- Fence-stripping (lines ~784-791): mirrors `query_router.py:144-148` verbatim — `if content.startswith('```'): content = content.split('```')[1]; if content.startswith('json'): content = content[4:]`
- Both patterns are INTENTIONAL duplication per CONTEXT.md §Fallback strategy; no cross-adapter import

## _emit_log mechanism: exactly one log event per call

- `complete()` signature: `_emit_log: bool = True` (keyword-only, after `temperature`)
- `complete()` finally block: `if _emit_log: _log_llm_call(extra)` — default `True` preserves all existing call-site behavior
- `_classify_via_text_mode` calls `self.complete(enriched, _emit_log=False)` — suppresses delegate's event
- `_classify_via_text_mode` emits its own event in its own `finally:` block with `llm_tool_mode: "text_fallback"`
- `classify_with_tool` strict path emits event in its own `finally:` with `llm_tool_mode: "strict"`
- Result: EXACTLY ONE `llm_call` event per `classify_with_tool` invocation in both paths

## tools_supported log field

Added at END of `llm_provider_loaded` extra dict (line 184), after existing `provider` and `base_url` fields. Order-of-definition lock per RESEARCH.md Q7 — minimizes diff vs tests that assert existing fields.

## Phase 3 test deletion

**None.** Grep of `tests/test_phase3_adapter.py` for "NotImplementedError" returned no test function (only a docstring comment in the module header at line 5). The Phase 3 gate had 21 tests with no NotImplementedError-asserting test function to delete. All 21 tests pass byte-identically after this plan's changes.

## Task Commits

1. **Tasks 2.1+2.2 combined** (written atomically in one pass) — `62da5b4` (feat(04-02))

Note: Task 2.1 (_post_messages + tools_supported) and Task 2.2 (classify_with_tool + _classify_via_text_mode + _emit_log) were implemented in a single file write for safety (refactoring complete()'s try/except while simultaneously adding new methods). Both tasks' done criteria verified before commit.

## Files Created/Modified

- `src/llm/anthropic_mgti.py` — Added `_post_messages` (line 192), refactored `complete()` to use it + added `_emit_log` kwarg (line 292), implemented `classify_with_tool` (line 462), added `_classify_via_text_mode` (line 705), added `tools_supported` to startup log (line 184)

## Decisions Made

All 11 locked decisions from the plan were followed exactly as specified. Key highlights:
- Env-flag-only fallback (decision §1): no runtime auto-fallback; operator gets a loud signal if proxy regresses
- _post_messages intra-module (decision §2): CONTEXT.md §Code structure lock upheld; NOT extracted to src/llm/_log.py
- max_tokens during tool_use = LLMSchemaError (decision §3): locked divergence from complete()'s truncated-as-success
- Guardrail order (decision §4): checked BEFORE missing-tool_use — load-bearing regression guard
- Defensive iteration (decision §5): first type==tool_use AND name==tool_name; indexing content[0] avoided

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The only operational difference was that Task 2.1 and Task 2.2 were implemented in a single file write and committed together (rather than two separate commits). This was pragmatic — refactoring complete()'s try/except simultaneously with adding new methods in the same file is safest as one atomic operation.

**Note on jsonschema precondition:** Upgraded from 4.25.1 → 4.26.0 before execution as specified by RESEARCH.md Pitfall 4 and the plan's locked decision §9. Upgrade succeeded.

**Note on NotImplementedError-stub test deletion:** The plan anticipated a test named `test_classify_with_tool_stub` in `tests/test_phase3_adapter.py`. Grep confirmed no such function exists in the file — only a docstring comment reference at module level. No deletion was needed.

## Issues Encountered

None — the refactor was straightforward. Phase 3 tests passed byte-identically on first run.

## User Setup Required

None — no external service configuration required. The `ANTHROPIC_TOOLS_SUPPORTED` env flag defaults to `true`; operators flip it to `false` to engage the text-mode fallback.

## Next Phase Readiness

- Plan 04-02 complete: `classify_with_tool` is production-ready for both the strict path and the text-mode fallback
- Plan 04-03 (Azure parity): may reference `_emit_log` pattern if Azure needs analogous log-suppression mechanism
- Plan 04-04 (acceptance gate): should add one test per error-matrix row (9 rows); tests for `llm_tool_mode` field; tests for `tools_supported` in `llm_provider_loaded` log; test for text-mode fallback producing indistinguishable ToolCall
- Phase 5 (smoke test): `classify_with_tool` ready to call against live MGTI proxy with `ANTHROPIC_TOOLS_SUPPORTED=true`

---
*Phase: 04-strict-tools-smoke-test*
*Completed: 2026-05-21*
