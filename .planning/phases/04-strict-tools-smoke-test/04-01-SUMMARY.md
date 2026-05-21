---
phase: 04-strict-tools-smoke-test
plan: 01
subsystem: llm
tags: [anthropic, strict-tools, json-schema, tool-use, classification, intent, dataclass-reflection]

# Dependency graph
requires:
  - phase: 03-anthropic-mgti-adapter
    provides: AnthropicMGTIClient with classify_with_tool stub + typed errors + _compat dispatch
  - phase: 01-abstraction-seam
    provides: ToolSchema, ToolCall, ClassificationResultV1 dataclasses in src/llm/types.py

provides:
  - INTENT_TOOL: ToolSchema constant derived programmatically from ClassificationResultV1 (TOOL-02)
  - _py_type_to_json_schema + _build_intent_tool_schema reflection helpers in src/llm/types.py
  - classify_intent migrated from client.complete() + json.loads to client.classify_with_tool()
  - ClassificationResultV1.intent tightened to Literal["structured", "semantic", "hybrid"]

affects:
  - 04-02-anthropic-classify-with-tool (takes ToolSchema param; INTENT_TOOL is the production arg)
  - 04-03-smoke-script (imports INTENT_TOOL directly for schema display)
  - 04-04-acceptance-gate (verifies INTENT_TOOL schema + classify_with_tool call site)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dataclass-to-JSON-Schema reflection using typing.get_type_hints() (not f.type strings)
    - additionalProperties=false for strict LLM schema enforcement (Anthropic best practice)
    - TOOL-04: heuristic merge AFTER LLM result (chart_requested/chart_type from locals, not call.input)
    - LLMSchemaError routed to heuristic fallback via existing except Exception at query_router.py:173-175

key-files:
  created: []
  modified:
    - src/llm/types.py
    - src/query_router.py
    - tests/test_phase2_parity.py

key-decisions:
  - "INTENT_TOOL derived from ClassificationResultV1 via get_type_hints() not fields().type (CRITICAL: from __future__ import annotations makes .type return strings)"
  - "version: str stays plain string (no Literal['v1'], no const/enum) per locked decision §2"
  - "additionalProperties: false on derived schema — LLM cannot inject chart_requested/chart_type"
  - "fence-stripping + json.loads + JSONDecodeError + intent-allowlist all deleted; schema enum enforces allowlist"
  - "test_phase2_parity.py updated (Rule 1): 3 tests that tested old complete() call path updated to mock classify_with_tool"

patterns-established:
  - "Schema derivation: typing.get_type_hints(cls) for type resolution + dataclasses.fields(cls) for ordering and required-detection"
  - "Heuristic merge pattern: detect chart BEFORE LLM call, merge locals AFTER into return dict (TOOL-04)"

# Metrics
duration: 6min
completed: 2026-05-21
---

# Phase 4 Plan 1: intent-tool-and-classify-intent-migration Summary

**INTENT_TOOL ToolSchema constant derived from ClassificationResultV1 via dataclass reflection; classify_intent migrated from complete()+json.loads to classify_with_tool() with heuristic merge preserved post-LLM**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-21T18:36:41Z
- **Completed:** 2026-05-21T18:42:43Z
- **Tasks:** 2
- **Files modified:** 3 (src/llm/types.py, src/query_router.py, tests/test_phase2_parity.py)

## Accomplishments

- Added `_py_type_to_json_schema` + `_build_intent_tool_schema` reflection helpers that automatically derive a JSON Schema object from any `@dataclass` — future field additions to `ClassificationResultV1` propagate automatically (TOOL-02 single-source-of-truth lock)
- Added `INTENT_TOOL: ToolSchema` top-level constant with 5-field schema (`version`, `intent`, `confidence`, `reasoning`, `detected_filters`), `intent` enum constraint, and `additionalProperties: false` — LLM cannot inject `chart_requested`/`chart_type`
- Migrated `classify_intent` from `client.complete() + json.loads()` to `client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")` while preserving the heuristic `chart_requested`/`chart_type` merge (TOOL-04)
- Deleted 4 dead blocks: markdown fence-stripping, `json.loads`, `JSONDecodeError` fallback, intent-allowlist runtime check

## Task Commits

Each task was committed atomically:

1. **Task 1.1: Add schema-derivation helpers + INTENT_TOOL constant** - `ec1bf5e` (feat)
2. **Task 1.2: Migrate classify_intent to classify_with_tool** - `2d82025` (feat)

**Plan metadata:** TBD (docs commit)

## Files Created/Modified

- `src/llm/types.py` — Added `from typing import Literal`; tightened `ClassificationResultV1.intent` to `Literal["structured", "semantic", "hybrid"]`; added `_PRIMITIVE_TO_JSON_SCHEMA`, `_py_type_to_json_schema`, `_build_intent_tool_schema`, `INTENT_TOOL` (99 lines added)
- `src/query_router.py` — Removed `import json`; added `from src.llm.types import INTENT_TOOL`; replaced `client.complete()` + JSON-parse block with `client.classify_with_tool()`; deleted fence-stripping, `json.loads`, `JSONDecodeError`, intent-allowlist; return dict uses `result["intent"]` directly (not `.get(..., "structured")`)
- `tests/test_phase2_parity.py` — Updated 3 tests that tested old `complete()` call path in `classify_intent` (Rule 1 deviation — see below)

## Decisions Made

- `intent: str` tightened to `Literal["structured", "semantic", "hybrid"]` — propagates directly to `INTENT_TOOL.input_schema['properties']['intent']['enum']`; replaces the deleted runtime allowlist check at old query_router.py:157-158
- `version: str` stays plain string — no `const`/`enum`/`Literal["v1"]` per locked decision §2; future v2 updates both the dataclass and derivation helper together
- `get_type_hints(cls)` used for type resolution (not `fields()[i].type`) — `from __future__ import annotations` at line 10 makes `.type` return strings; `get_type_hints()` resolves forward references to real type objects (RESEARCH.md Pitfall 1 / Plan decision §3)
- `result["intent"]` used in return dict (not `.get("intent", "structured")`) — the schema's `required` list + `enum` guarantees presence and validity; defaulting would silently mask upstream contract violation; `.get()` with defaults kept only for `confidence`, `reasoning`, `detected_filters` as defensive belt-and-braces

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_phase2_parity.py — 3 tests asserted old complete() call path**

- **Found during:** Task 1.2 verification (`python -m pytest tests/ -q` → 3 failures)
- **Issue:** Phase 2 acceptance gate contained 3 tests that directly invoked `classify_intent` and expected `client.complete()` to be called. After Plan 01's migration to `classify_with_tool`, these tests broke:
  - `test_call_azure_openai_eliminated`: asserted `max_tokens=500` in `classify_intent` source — no longer present since `classify_with_tool` doesn't take `max_tokens`
  - `test_parity_end_to_end_classify_intent`: patched `requests.post` expecting `complete()` to be called; Azure `classify_with_tool` uses `complete()` internally but the fixture JSON lacked `version` field, causing `LLMSchemaError`
  - `test_error_translation_at_call_site`: set `fake.complete.side_effect = exc` to test error routing through `classify_intent`; error never fired since call site now uses `classify_with_tool`
- **Fix:**
  - `test_call_azure_openai_eliminated`: Replace `max_tokens=500` check for CS1 with `classify_with_tool` presence check; CS2/CS3 `max_tokens` checks preserved
  - `test_parity_end_to_end_classify_intent`: Patch `AzureOpenAIClient.classify_with_tool` directly with a `ToolCall` mock carrying valid `ClassificationResultV1` fields
  - `test_error_translation_at_call_site`: Add `fake.classify_with_tool.side_effect = exc` alongside existing `fake.complete.side_effect = exc`
- **Files modified:** `tests/test_phase2_parity.py`
- **Verification:** `python -m pytest tests/ -q` → 39 passed
- **Committed in:** `2d82025` (Task 1.2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in tests that asserted old call path)
**Impact on plan:** The plan correctly anticipated that tests might need updating and said "flag if not zero." The Phase 2 tests tested the old `complete()` call path in `classify_intent` directly — these were correct tests for Phase 2 but needed updating for Phase 4's migration. The fix updates them to test the new `classify_with_tool` call path while preserving all error-routing, heuristic-merge, and CS2/CS3 invariants.

## Issues Encountered

None beyond the test deviation documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `INTENT_TOOL` is importable from `src.llm.types` — Plan 02 (`AnthropicMGTIClient.classify_with_tool`) takes `tool: ToolSchema` as a parameter and does NOT need to import `INTENT_TOOL` directly; Plan 03 (smoke script) WILL import it
- `classify_intent` call site is wired — Phase 4 Plan 02 need only implement the adapter method; the call site is already correct
- Azure adapter's `classify_with_tool` (prompt-based, ADP-02) handles `INTENT_TOOL` correctly since it's already been tested end-to-end in the updated Phase 2 gate
- 39/39 tests green — Phase 4 Plan 02 can proceed without baseline risk

---
*Phase: 04-strict-tools-smoke-test*
*Completed: 2026-05-21*
