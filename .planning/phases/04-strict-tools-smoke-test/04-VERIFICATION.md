---
phase: 04-strict-tools-smoke-test
verified: 2026-05-21T19:14:03Z
status: human_needed
score: 4/5 must-haves automated-verified (SC 5 artifact verified; live execution operator-run)
human_verification:
  - test: Run smoke script against staging gateway
    expected: >-
      python scripts/smoke_llm.py --provider both --verbose exits 0; all configured
      providers PASS on service-info, complete, and classify_with_tool checks;
      transcript pasted into Phase 4 verification PR
    why_human: >-
      Live staging credentials are not available in CI or the dev environment.
      The smoke script OPERATOR-RUN ONLY designation is locked in 04-CONTEXT.md
      and RESEARCH.md Pitfall 7. The acceptance-gate pytest verifies artifact
      existence and py_compile syntax; live HTTP execution is the operator responsibility.
---

# Phase 4: Strict-Tools + Smoke Test - Verification Report

**Phase Goal:** Wire Anthropic strict-tools for intent classification (single Python source of truth,
chart_requested/chart_type stay out of the LLM schema) and ship scripts/smoke_llm.py as the
live-credential gate that must pass for both providers before Phase 5.

**Verified:** 2026-05-21T19:14:03Z
**Status:** human_needed
**Re-verification:** No - initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | INTENT_TOOL programmatically derived from ClassificationResultV1; chart_requested/chart_type absent from schema | VERIFIED | types.py:164-172 - INTENT_TOOL built via _build_intent_tool_schema(ClassificationResultV1); runtime dc_fields == schema_props is True |
| 2 | classify_with_tool sends strict-tools body and validates tool_use block | VERIFIED | anthropic_mgti.py:551-562 - body[tools] + body[tool_choice] with disable_parallel_tool_use:True; anthropic_mgti.py:669-678 - jsonschema.validate; anthropic_mgti.py:650-654 - LLMSchemaError on missing tool_use |
| 3 | ANTHROPIC_TOOLS_SUPPORTED=false transparently falls back to text-mode | VERIFIED | anthropic_mgti.py:524-525 - env-flag branch to _classify_via_text_mode; anthropic_mgti.py:778 - complete with _emit_log=False; result is indistinguishable ToolCall downstream |
| 4 | classify_intent merges heuristic chart fields AFTER LLM result; LLM cannot overwrite | VERIFIED | query_router.py:121 - _detect_chart_request runs before try block; query_router.py:167-168 - final dict reads from heuristic locals only, never call.input |
| 5 | scripts/smoke_llm.py --provider both exits zero against staging gateway | HUMAN NEEDED | Artifact verified: file exists, py_compile.compile passes. Live-credential execution is operator-run only. |

**Score:** 4/5 truths automated-verified; 1/5 human-needed (SC 5 live execution)
---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| src/llm/types.py | ClassificationResultV1 + INTENT_TOOL constant + derivation helpers | VERIFIED | 173 lines; ClassificationResultV1 at line 44; _build_intent_tool_schema at line 136; INTENT_TOOL at line 164; no stubs |
| src/llm/anthropic_mgti.py | classify_with_tool strict path + fallback + _post_messages + _emit_log kwarg + log fields | VERIFIED | 823 lines; classify_with_tool at line 462; _classify_via_text_mode at line 705; _post_messages at line 192; _emit_log kwarg at line 292; llm_tool_mode at lines 575 and 770; tools_supported at line 184 |
| src/query_router.py | classify_intent call-site with classify_with_tool + INTENT_TOOL + heuristic merge after LLM | VERIFIED | INTENT_TOOL imported at line 14; classify_with_tool called at lines 139-143; heuristic called at line 121 before LLM; merge at lines 162-169 from heuristic locals |
| scripts/smoke_llm.py | Operator-run live-credential gate for both providers | VERIFIED (ARTIFACT) | 471 lines; --provider both argparse; 3 Anthropic checks; 2 Azure checks; SKIP/FAIL cred logic; exit_code = 1 if failed > 0 else 0; compiles cleanly |
| tests/test_phase4_strict_tools.py | Acceptance gate: SC 1-5 + 9 error-matrix rows + COMPAT-DISPATCH | VERIFIED | 870 lines; 30 tests all passing; SC1 (6), SC2 (3), SC3 (3), SC4 (1), SC5 (2), error-matrix (9), COMPAT-DISPATCH (2), log-events (3), precondition (1) |
---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| INTENT_TOOL.input_schema | ClassificationResultV1 fields | _build_intent_tool_schema(ClassificationResultV1) at types.py:171 | WIRED | typing.get_type_hints + dataclasses.fields loop at types.py:145-158; runtime verified |
| query_router.classify_intent | AnthropicMGTIClient.classify_with_tool | client.classify_with_tool(messages, INTENT_TOOL, tool_name=...) at query_router.py:139-143 | WIRED | INTENT_TOOL imported line 14; wrapped in llm_to_query_error() at line 138 |
| classify_with_tool strict path | Anthropic Messages API | _post_messages(body, ...) at anthropic_mgti.py:579 with tools + tool_choice in body | WIRED | body[tools] at line 551; body[tool_choice] at line 558; disable_parallel_tool_use:True at line 561 |
| classify_with_tool fallback | _classify_via_text_mode | if not self._tools_supported at anthropic_mgti.py:524-525 | WIRED | Reads settings.anthropic_tools_supported at line 162; boolean gate at line 524 |
| _classify_via_text_mode | complete(_emit_log=False) | self.complete(enriched, _emit_log=False) at anthropic_mgti.py:778 | WIRED | _emit_log=False suppresses delegate event; wrapper emits one event tagged llm_tool_mode=text_fallback at line 821 |
| heuristic chart fields | classify_intent final dict | locals from _detect_chart_request at line 121, read at lines 167-168 | WIRED | call.input never accessed for chart fields; additionalProperties:False locks LLM out |
---

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| Single source of truth for intent schema (TOOL-01/TOOL-02) | SATISFIED | ClassificationResultV1 is the only definition; INTENT_TOOL derived programmatically |
| chart_requested/chart_type excluded from LLM contract (TOOL-03) | SATISFIED | Not in ClassificationResultV1; additionalProperties:False locks schema |
| Heuristic merge post-LLM prevents LLM overwrite (TOOL-04) | SATISFIED | query_router.py:121 runs heuristic before LLM; lines 167-168 reference heuristic locals only |
| Strict-tools request body shape (TOOL-06) | SATISFIED | tools + tool_choice + disable_parallel_tool_use:True at anthropic_mgti.py:551-562 |
| LLMSchemaError on missing tool_use | SATISFIED | anthropic_mgti.py:636-654 |
| jsonschema.validate defence-in-depth | SATISFIED | anthropic_mgti.py:669-678 |
| Env-flag-only fallback, no runtime auto-fallback | SATISFIED | anthropic_mgti.py:524-525 - env-flag check only, no try/except auto-fallback |
| Exactly one llm_call log event per classify_with_tool call | SATISFIED | Strict path emits at line 703; text-fallback suppresses delegate via _emit_log=False at line 778; test_logs_* confirms |
| llm_tool_mode log field | SATISFIED | strict at line 575; text_fallback at line 770 |
| tools_supported in startup log | SATISFIED | anthropic_mgti.py:184 |
| scripts/smoke_llm.py artifact | SATISFIED (artifact) | Exists, compiles, structured correctly; live execution operator-run |
| 69-test combined suite green | SATISFIED | pytest tests/ -q produces 69 passed, 1 warning in 8.21s |
---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No stubs, TODOs, placeholders, or empty handlers found in any Phase 4 artifact |

Grep across all Phase 4 modified files confirms: zero TODO, FIXME, placeholder, return null,
return {}, or console.log patterns in types.py, anthropic_mgti.py, query_router.py,
or scripts/smoke_llm.py.
---

### Human Verification Required

#### 1. Live Smoke Script Execution Against Staging Gateway

**Test:** From a dev environment with valid .env containing ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY,
ANTHROPIC_MODEL, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_KEY set to staging values, run:

    python scripts/smoke_llm.py --provider both --verbose

**Expected:**

    [PASS] anthropic_mgti   / service-info         - 200 in <N>ms  shape={...}
    [PASS] anthropic_mgti   / complete              - 200 in <N>ms  model=eu.anthropic.claude-*  shape={...}
    [PASS] anthropic_mgti   / classify_with_tool    - 200 in <N>ms  intent=structured|semantic|hybrid  shape={...}
    [PASS] azure_openai     / complete              - 200 in <N>ms  shape={...}
    [PASS] azure_openai     / classify_with_tool    - 200 in <N>ms  intent=structured|semantic|hybrid  shape={...}
    Summary: 5 passed, 0 failed, 0 skipped - exit 0

Exit code: 0

**Why human:** Live staging credentials are not available in CI. The smoke script is designated
OPERATOR-RUN ONLY in scripts/smoke_llm.py:18-19 and 04-CONTEXT.md. RESEARCH.md Pitfall 7 locks
py_compile as the automated verification surface; HTTP execution requires real gateway access.

**Action required:** Paste the full terminal transcript into the Phase 4 verification PR before
Phase 5 work begins.
---

### Gaps Summary

No gaps found. All four automated success criteria pass structural, substantive, and wiring
verification against the actual codebase. The single human-needed item (SC 5 live execution)
is an expected operator-run gate per phase design - the artifact is present and structurally
correct as verified by test_sc5_smoke_script_exists and test_sc5_smoke_script_syntax_valid.

---

### Test Suite Evidence

    pytest tests/ -q
    69 passed, 1 warning in 8.21s

    pytest tests/test_phase4_strict_tools.py -v
    30 passed, 1 warning in 7.68s

Phase 4 tests by SC mapping:

- SC 1 (INTENT_TOOL derivation): test_sc1_* - 6 tests
- SC 2 (strict-tools path): test_sc2_* - 3 tests
- SC 3 (text-mode fallback): test_sc3_* - 3 tests
- SC 4 (heuristic merge): test_sc4_* - 1 test
- SC 5 (smoke script artifact): test_sc5_* - 2 tests
- Error matrix (9 rows): test_errmatrix_* - 9 tests
- COMPAT-DISPATCH: test_compat_dispatch_* - 2 tests
- Log events: test_logs_* - 3 tests
- Precondition: test_precondition_jsonschema_version - 1 test

---

_Verified: 2026-05-21T19:14:03Z_
_Verifier: Claude (gsd-verifier)_
