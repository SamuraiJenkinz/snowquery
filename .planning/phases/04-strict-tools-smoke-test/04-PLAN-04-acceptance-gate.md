---
phase: 4
plan: 4
name: acceptance-gate
type: execute
wave: 3
depends_on: [1, 2, 3]
files_modified:
  - tests/test_phase4_strict_tools.py
autonomous: true

must_haves:
  truths:
    - "tests/test_phase4_strict_tools.py exists as a self-contained pytest module (NO conftest.py, NO pytest.ini, NO new fixture files)"
    - "All 5 Phase 4 success criteria from ROADMAP.md are proven by named test functions"
    - "All 9 rows of the CONTEXT.md classify_with_tool error matrix have at least one test case each"
    - "The COMPAT-DISPATCH pair (LLMSchemaError → 'Anthropic API call failed' QueryError, LLMGuardrailError → same) is present, mirroring tests/test_phase3_adapter.py:519-552"
    - "Zero live HTTP — all requests.post and requests.get are mocked via unittest.mock.patch"
    - "Autouse fixtures _clear_factory_cache + _strip_llm_env mirror tests/test_phase3_adapter.py:59-101 verbatim"
    - "Inline mock-response builders (_make_anthropic_tool_use_response, _make_anthropic_error_response, etc.) — NO fixture files in tests/fixtures/"
    - "SC #5 verification uses os.path.exists + py_compile.compile(doraise=True); does NOT subprocess.run the smoke script (RESEARCH.md Pitfall 7)"
    - "Combined Phase 1+2+3+4 suite is approximately 39 + ~25 = ~64 tests, all passing"
    - "requirements.txt jsonschema version drift is verified resolved as a precondition (pip install -U 'jsonschema>=4.26.0,<5' BEFORE pytest)"
  artifacts:
    - path: "tests/test_phase4_strict_tools.py"
      provides: "Phase 4 acceptance gate — pytest module proving all 5 SCs + 9 error-matrix rows + COMPAT-DISPATCH"
      contains: "from src.llm.types import INTENT_TOOL"
  key_links:
    - from: "tests/test_phase4_strict_tools.py"
      to: "src.llm.types.INTENT_TOOL (Plan 01)"
      via: "from src.llm.types import INTENT_TOOL, ClassificationResultV1"
      pattern: "from src\\.llm\\.types import.*INTENT_TOOL"
    - from: "tests/test_phase4_strict_tools.py"
      to: "src.llm.anthropic_mgti.AnthropicMGTIClient.classify_with_tool (Plan 02)"
      via: "client.classify_with_tool(messages, INTENT_TOOL, tool_name='classify_intent')"
      pattern: "classify_with_tool\\("
    - from: "tests/test_phase4_strict_tools.py SC #5 test"
      to: "scripts/smoke_llm.py (Plan 03)"
      via: "os.path.exists + py_compile.compile(doraise=True)"
      pattern: "py_compile\\.compile"
    - from: "tests/test_phase4_strict_tools.py COMPAT-DISPATCH tests"
      to: "src.llm._compat.llm_to_query_error"
      via: "with llm_to_query_error(): raise LLMSchemaError('...', provider='anthropic_mgti')"
      pattern: "llm_to_query_error"
---

<objective>
Create `tests/test_phase4_strict_tools.py` — a pytest module proving ALL 5 Phase 4 success criteria from ROADMAP.md PLUS the 9 classify_with_tool error matrix rows from CONTEXT.md PLUS the COMPAT-DISPATCH per-provider regression guard. A green run on this module IS the Phase 4 gate.

Purpose: This is the single artifact that turns "Phase 4 work merged" into "Phase 4 complete." It is the rate-limiting evidence document for Phase 5 unblock. Following the Phase 1/2/3 precedent, the gate is one self-contained pytest module — no conftest.py, no pytest.ini, no fixture files, all mocks inline. Zero live HTTP. Combined run with Phase 1+2+3 gates yields approximately 64 tests, all green, in under 15 seconds.

Output: `tests/test_phase4_strict_tools.py` (~25 tests, ~700 lines) that exercises the strict-tools path, text-mode fallback, INTENT_TOOL derivation invariants, query_router heuristic-merge regression guard, smoke script existence + syntax, the 9-row error matrix, and the 2-test COMPAT-DISPATCH pair.
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-strict-tools-smoke-test/04-CONTEXT.md
@.planning/phases/04-strict-tools-smoke-test/04-RESEARCH.md

# Plans this depends on (must all be on disk before this plan runs)
@.planning/phases/04-strict-tools-smoke-test/04-01-SUMMARY.md
@.planning/phases/04-strict-tools-smoke-test/04-02-SUMMARY.md
@.planning/phases/04-strict-tools-smoke-test/04-03-SUMMARY.md

# Reference patterns (READ THIS FIRST — mirror its structure)
@tests/test_phase3_adapter.py

# Files this test verifies
@src/llm/types.py
@src/llm/anthropic_mgti.py
@src/query_router.py
@scripts/smoke_llm.py
@src/llm/_compat.py
@src/llm/errors.py
@requirements.txt
</context>

<decisions>
## Decisions locked for this plan

1. **Test module is SELF-CONTAINED.** NO `conftest.py`. NO `pytest.ini`. NO new `tests/fixtures/` files. NO new helpers in `tests/`. Matches Phase 1/2/3 acceptance-gate pattern (STATE.md Phase 3-04 decision: "Test module self-contained — no conftest.py, no pytest.ini added; matches Phase 1/Phase 2 gate pattern across all three phases now").

2. **Inline mock-response builders for Anthropic JSON envelopes.** Mirror the Phase 3 `_make_anthropic_response` / `_make_error_response` pattern (STATE.md Phase 3-04 decision: "Inline mock-response builders used INSTEAD of fixture files — Phase 3 has no parity baseline... RESEARCH.md 'Mock Response Builder Pattern' applied"). Phase 4 needs FOUR builders: `_make_tool_use_response`, `_make_text_response_for_fallback`, `_make_guardrail_response`, `_make_error_envelope`.

3. **Autouse fixtures mirror Phase 3 verbatim.** Copy `_clear_factory_cache` and `_strip_llm_env` from `tests/test_phase3_adapter.py:59-101`. Same purpose: isolate the module-level factory cache and strip env vars between tests so each test sees a clean slate.

4. **Realistic env constants matching Phase 3.** Reuse `_BASE_URL`, `_API_KEY`, `_MODEL_SONNET`, `_MODEL_OPUS_4_7`, `_AZURE_ENDPOINT`, `_AZURE_KEY` constant values from `tests/test_phase3_adapter.py:45-52` to keep cross-phase consistency.

5. **Level A patching (`patch('requests.post')`) for adapter-direct tests.** Plan 02's adapter is exercised via `with patch('src.llm.anthropic_mgti.requests.post', return_value=mock_resp): ...` — mirrors Phase 3's approach. For tests that exercise `_compat.py` translation, use Level B (raise the typed error inline inside `llm_to_query_error()`) — mirrors `test_phase3_adapter.py:519-552`.

6. **SC #5 verification = file-existence + py_compile, NO execution.** RESEARCH.md Pitfall 7 + CONTEXT.md §Verification strategy SC #5: "File-existence check on `scripts/smoke_llm.py`; syntax check via `py_compile`. NO execution from pytest (operator-run gate)." Use `import os; assert os.path.exists(...)` + `import py_compile; py_compile.compile(path, doraise=True)`.

7. **COMPAT-DISPATCH tests cover `LLMSchemaError` and `LLMGuardrailError`.** Phase 3 covered `LLMAuthError` and `LLMTimeoutError`. Phase 4's two new typed-error raise sites are `LLMSchemaError` (most of the error matrix) and `LLMGuardrailError` (already existed in Phase 3 but now reachable from classify_with_tool). Mirror the Phase 3 COMPAT-DISPATCH structure: raise the typed error inside `llm_to_query_error()` and assert the resulting `QueryError.message == "Anthropic API call failed"` (NOT `"Azure OpenAI API call failed"` — the regression guard).

8. **Heuristic-merge regression test (SC #4) patches the adapter to inject `chart_requested=True` into the LLM's tool_use response.** Then call `classify_intent(user_query, schema_summary)` and assert the final returned dict's `chart_requested` matches the HEURISTIC (which for a non-chart query is `False`), NOT the LLM injection. This catches the regression where someone reads `chart_requested` from `call.input` instead of the local.

9. **Precondition check: `jsonschema >= 4.26`.** Add as first test in the module (named `test_precondition_jsonschema_version`) — `import jsonschema; assert int(jsonschema.__version__.split('.')[1]) >= 26, f"installed {jsonschema.__version__}; pin requires >=4.26"`. If this fails, run `pip install -U "jsonschema>=4.26.0,<5"` and re-run pytest. The test makes the precondition self-documenting.

10. **No edits to existing `tests/` files in this plan.** Plan 02 may have already deleted the NotImplementedError-asserting test from `tests/test_phase3_adapter.py`. Plan 04 does NOT re-edit that file.

11. **Test counts target ~25, structured by SC.** Approximate breakdown (planner has discretion on exact count, but each SC must be PROVEN):
    - SC #1 (INTENT_TOOL derivation): 5 tests (presence, absence-of-chart, intent-enum, version-plain-string, additionalProperties+required+single-source-of-truth)
    - SC #2 (strict-tools path): 4 tests (request body shape, valid response → ToolCall, missing tool_use → LLMSchemaError, wrong tool name → LLMSchemaError)
    - SC #3 (text-mode fallback): 3 tests (env-flag triggers fallback, request body has NO tools/tool_choice, fallback returns indistinguishable ToolCall)
    - SC #4 (heuristic merge): 1 test (LLM injects chart_requested=True; classify_intent returns heuristic False)
    - SC #5 (smoke script): 2 tests (file exists, py_compile passes)
    - Error matrix (in addition to those above): malformed input not dict, jsonschema validation failure, max_tokens during tool_use, unknown stop_reason = 4 tests
    - COMPAT-DISPATCH: 2 tests (LLMSchemaError + LLMGuardrailError → Anthropic-named QueryError)
    - Log assertions: tools_supported in startup log = 1 test, llm_tool_mode field present in llm_call event for both paths = 2 tests
    - Optional: missing tools_supported field test for backwards-compat = skip if test count > 25

12. **NO test invokes `classify_intent` directly that hits the real LLM.** All tests that exercise `query_router.classify_intent` (SC #4) mock the adapter layer via `unittest.mock.patch` or `monkeypatch`.
</decisions>

<tasks>

<task type="auto">
  <name>Task 4.1: Write tests/test_phase4_strict_tools.py — full acceptance gate (~25 tests, ~700 lines)</name>
  <files>tests/test_phase4_strict_tools.py</files>
  <action>
**Precondition (MUST run before writing the test):**

```bash
pip install -U "jsonschema>=4.26.0,<5"
python -c "import jsonschema; print('jsonschema version:', jsonschema.__version__)"
# Expected: 4.26.x or higher (NOT 4.25.x)
```

If upgrade fails, halt and report — RESEARCH.md Pitfall 4 says the gate will fail on import.

**Write `tests/test_phase4_strict_tools.py`.** Use the skeleton below; flesh out each test per the SC + error-matrix breakdown in locked decision §11. Write all test bodies verbatim — no `# TODO` markers, no `...` placeholders.

**MODULE HEADER + IMPORTS + AUTOUSE FIXTURES + ENV CONSTANTS + MOCK BUILDERS:**

```python
"""Phase 4 acceptance gate: prove all 5 Phase 4 success criteria.

Each test function maps to one of:
  - The 5 numbered Phase 4 ROADMAP success criteria
  - One of the 9 rows of the CONTEXT.md classify_with_tool error matrix
  - The COMPAT-DISPATCH per-provider regression guard
  - Log-event assertions (tools_supported, llm_tool_mode)

Conventions inherited from tests/test_phase3_adapter.py:
  - autouse _clear_factory_cache + _strip_llm_env fixtures isolate
    module-level singletons and env-var state between tests
  - HTTP is mocked via unittest.mock.patch('src.llm.anthropic_mgti.requests.post', ...)
    (Level A) or by raising typed errors inline inside llm_to_query_error()
    (Level B — for COMPAT-DISPATCH)
  - Inline mock-response builders — NO fixture files
  - Tests have ZERO live external dependencies

Precondition: pip install -U "jsonschema>=4.26.0,<5" (RESEARCH.md Pitfall 4)

Run with: `pytest tests/test_phase4_strict_tools.py -v`
Or combined with prior phases: `pytest tests/ -v` (expected: ~64 tests)
"""
from __future__ import annotations

import json
import logging
import os
import py_compile
from unittest.mock import MagicMock, patch

import jsonschema
import pytest
import requests

from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.llm.anthropic_mgti import AnthropicMGTIClient
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMGuardrailError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.llm.types import (
    INTENT_TOOL,
    ClassificationResultV1,
    ToolCall,
    ToolSchema,
)
from src.utils import QueryError, logger as snow_logger


# Realistic env values — mirror tests/test_phase3_adapter.py:45-52 verbatim
_BASE_URL = "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1"
_API_KEY = "test-key-not-real"
_MODEL_SONNET = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
_MODEL_OPUS_4_7 = "eu.anthropic.claude-opus-4-7-20251201-v1:0"
_AZURE_ENDPOINT = (
    "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"
)
_AZURE_KEY = "azure-test-key-not-real"

# Smoke script path — relative to repo root (pytest CWD)
_SMOKE_SCRIPT_PATH = "scripts/smoke_llm.py"


# ---------------------------------------------------------------------------
# Autouse fixtures — MIRROR tests/test_phase3_adapter.py:59-101 verbatim
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Each test sees an empty get_llm cache."""
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()


@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch):
    """Strip ALL LLM-related env vars so tests start from a clean slate."""
    for name in (
        "LLM_PROVIDER_DEFAULT",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "API_VERSION",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_VERSION",
        "ANTHROPIC_MAX_TOKENS",
        "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_TIMEOUT_S",
        "ANTHROPIC_TOOLS_SUPPORTED",
    ):
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture
def anthropic_env(monkeypatch):
    """Realistic Anthropic env values (tools supported by default)."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", _BASE_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", _MODEL_SONNET)
    monkeypatch.setenv("ANTHROPIC_TOOLS_SUPPORTED", "true")


@pytest.fixture
def anthropic_env_tools_off(monkeypatch):
    """Anthropic env with TOOLS_SUPPORTED=false — triggers text-mode fallback."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", _BASE_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", _MODEL_SONNET)
    monkeypatch.setenv("ANTHROPIC_TOOLS_SUPPORTED", "false")


# ---------------------------------------------------------------------------
# Inline mock-response builders (NO fixture files — Phase 3-04 decision)
# ---------------------------------------------------------------------------

def _make_tool_use_response(
    intent: str = "structured",
    confidence: float = 0.95,
    reasoning: str = "Detected structured-query keywords.",
    detected_filters: dict | None = None,
    tool_name: str = "classify_intent",
    stop_reason: str = "tool_use",
    extra_content_blocks: list | None = None,
    extra_input_fields: dict | None = None,
    omit_input: bool = False,
    input_not_dict: object | None = None,
) -> MagicMock:
    """Build a mock requests.Response simulating Anthropic's tool_use response.

    Defaults to a happy-path response that passes INTENT_TOOL.input_schema.
    Pass `extra_content_blocks` to test mixed text+tool_use (RESEARCH.md Pitfall 3).
    Pass `input_not_dict=42` to test malformed-input error matrix row.
    """
    if detected_filters is None:
        detected_filters = {}
    input_dict = {
        "version": "v1",
        "intent": intent,
        "confidence": confidence,
        "reasoning": reasoning,
        "detected_filters": detected_filters,
    }
    if extra_input_fields:
        input_dict.update(extra_input_fields)

    tool_use_block: dict = {
        "type": "tool_use",
        "id": "toolu_test_xxx",
        "name": tool_name,
    }
    if omit_input:
        pass  # no input key
    elif input_not_dict is not None:
        tool_use_block["input"] = input_not_dict
    else:
        tool_use_block["input"] = input_dict

    content = list(extra_content_blocks or []) + [tool_use_block]

    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "msg_test_xxx",
        "type": "message",
        "role": "assistant",
        "model": _MODEL_SONNET,
        "stop_reason": stop_reason,
        "content": content,
        "usage": {"input_tokens": 50, "output_tokens": 25},
    }
    return mock_resp


def _make_text_response(text: str) -> MagicMock:
    """Mock a plain-text Anthropic response — used by text-mode fallback tests."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "msg_test_xxx",
        "type": "message",
        "role": "assistant",
        "model": _MODEL_SONNET,
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 50, "output_tokens": 25},
    }
    return mock_resp


def _make_guardrail_response() -> MagicMock:
    """Mock guardrail-intervened response (200 + empty content + stop_reason)."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "msg_test_xxx",
        "type": "message",
        "role": "assistant",
        "model": _MODEL_SONNET,
        "stop_reason": "guardrail_intervened",
        "content": [],
        "usage": {"input_tokens": 50, "output_tokens": 0},
    }
    return mock_resp


def _make_error_envelope_response(
    status: int, title: str = "bad_request", detail: str = "test detail"
) -> MagicMock:
    """Mock MGTI error envelope response (4xx/5xx)."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.ok = False
    mock_resp.status_code = status
    mock_resp.text = json.dumps({"error": {"title": title, "detail": detail, "status": status}})
    mock_resp.json.return_value = {
        "error": {"title": title, "detail": detail, "status": status}
    }
    return mock_resp


# ===========================================================================
# Precondition test
# ===========================================================================

def test_precondition_jsonschema_version():
    """Precondition: jsonschema >= 4.26.0 (requirements.txt:18 pin).

    If this fails, run: pip install -U "jsonschema>=4.26.0,<5"
    (RESEARCH.md Pitfall 4 — dev box may have 4.25.1 stuck)
    """
    parts = jsonschema.__version__.split(".")
    major, minor = int(parts[0]), int(parts[1])
    assert (major, minor) >= (4, 26), (
        f"jsonschema {jsonschema.__version__} installed; "
        f"requirements.txt:18 pins >=4.26.0,<5. "
        f"Run: pip install -U 'jsonschema>=4.26.0,<5'"
    )
```

**Continue writing the test functions** — group by SC, then error matrix, then COMPAT-DISPATCH, then logs. Each test function has a one-line docstring referencing the SC or matrix row it proves.

**Required test functions (write all of these):**

```python
# ===========================================================================
# SC #1: INTENT_TOOL is derived from ClassificationResultV1 (TOOL-02);
#        chart_requested/chart_type are absent from input_schema (TOOL-03)
# ===========================================================================

def test_sc1_intent_tool_is_a_toolschema_with_correct_name():
    """SC #1: INTENT_TOOL exists and is a ToolSchema with name='classify_intent'."""
    assert isinstance(INTENT_TOOL, ToolSchema)
    assert INTENT_TOOL.name == "classify_intent"
    assert isinstance(INTENT_TOOL.description, str)
    assert len(INTENT_TOOL.description) > 0


def test_sc1_intent_tool_properties_match_dataclass_fields():
    """SC #1: single source of truth — schema.properties keys == dataclass field names."""
    from dataclasses import fields
    dc_field_names = {f.name for f in fields(ClassificationResultV1)}
    schema_props = set(INTENT_TOOL.input_schema["properties"])
    assert dc_field_names == schema_props, (
        f"single-source-of-truth broken: dc={dc_field_names} schema={schema_props}"
    )


def test_sc1_intent_tool_intent_is_enum_constraint():
    """SC #1 + user-locked decision §1: intent schema has enum constraint."""
    intent_schema = INTENT_TOOL.input_schema["properties"]["intent"]
    assert intent_schema == {
        "type": "string",
        "enum": ["structured", "semantic", "hybrid"],
    }, f"intent enum constraint missing or wrong: {intent_schema}"


def test_sc1_intent_tool_version_is_plain_string():
    """SC #1 + user-locked decision §2: version schema stays plain string (no enum/const)."""
    version_schema = INTENT_TOOL.input_schema["properties"]["version"]
    assert version_schema == {"type": "string"}, (
        f"version schema should be plain string, got: {version_schema}"
    )


def test_sc1_intent_tool_excludes_chart_fields():
    """SC #1 + TOOL-03: chart_requested and chart_type are NOT in input_schema."""
    props = INTENT_TOOL.input_schema["properties"]
    assert "chart_requested" not in props, (
        "chart_requested leaked into INTENT_TOOL — TOOL-03 violated"
    )
    assert "chart_type" not in props, (
        "chart_type leaked into INTENT_TOOL — TOOL-03 violated"
    )


def test_sc1_intent_tool_locks_down_additional_properties():
    """SC #1 best practice: additionalProperties=False + all 5 fields required."""
    schema = INTENT_TOOL.input_schema
    assert schema.get("additionalProperties") is False
    assert set(schema["required"]) == {
        "version", "intent", "confidence", "reasoning", "detected_filters"
    }


# ===========================================================================
# SC #2: classify_with_tool strict-tools path — body shape, response handling
# ===========================================================================

def test_sc2_strict_tools_request_body_shape(anthropic_env):
    """SC #2: request body contains tools=[INTENT_TOOL_dict] and tool_choice with disable_parallel_tool_use=True."""
    client = AnthropicMGTIClient()
    mock_resp = _make_tool_use_response()
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp) as mock_post:
        client.classify_with_tool(
            [{"role": "user", "content": "test query"}],
            INTENT_TOOL,
            tool_name="classify_intent",
        )
    assert mock_post.call_count == 1
    body = mock_post.call_args.kwargs["json"]
    assert "tools" in body
    assert isinstance(body["tools"], list) and len(body["tools"]) == 1
    assert body["tools"][0]["name"] == INTENT_TOOL.name
    assert body["tools"][0]["description"] == INTENT_TOOL.description
    assert body["tools"][0]["input_schema"] == INTENT_TOOL.input_schema
    assert body["tool_choice"] == {
        "type": "tool",
        "name": "classify_intent",
        "disable_parallel_tool_use": True,
    }


def test_sc2_strict_tools_valid_response_returns_toolcall(anthropic_env):
    """SC #2: HTTP 200 with valid tool_use → returns ToolCall with validated input."""
    client = AnthropicMGTIClient()
    mock_resp = _make_tool_use_response(intent="semantic", confidence=0.88)
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        result = client.classify_with_tool(
            [{"role": "user", "content": "find similar incidents"}],
            INTENT_TOOL,
            tool_name="classify_intent",
        )
    assert isinstance(result, ToolCall)
    assert result.tool_name == "classify_intent"
    assert result.input["intent"] == "semantic"
    assert result.input["confidence"] == 0.88
    # raw_response captured for debugging
    assert "content" in result.raw_response


def test_sc2_mixed_text_and_tool_use_blocks_handled(anthropic_env):
    """RESEARCH.md Pitfall 3: defensive iteration finds tool_use even after text block."""
    client = AnthropicMGTIClient()
    text_block = {"type": "text", "text": "I'll classify this query."}
    mock_resp = _make_tool_use_response(extra_content_blocks=[text_block])
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        result = client.classify_with_tool(
            [{"role": "user", "content": "test"}],
            INTENT_TOOL,
            tool_name="classify_intent",
        )
    assert isinstance(result, ToolCall)
    assert result.input["intent"] == "structured"


# ===========================================================================
# SC #3: ANTHROPIC_TOOLS_SUPPORTED=false fallback path
# ===========================================================================

def test_sc3_tools_supported_false_triggers_text_mode(anthropic_env_tools_off):
    """SC #3: when env flag is false, request body has NO tools/tool_choice keys."""
    client = AnthropicMGTIClient()
    # Text-mode delegates to complete() which posts {"content":[{"type":"text",...}]}
    fallback_json = json.dumps({
        "version": "v1",
        "intent": "structured",
        "confidence": 0.9,
        "reasoning": "test",
        "detected_filters": {},
    })
    mock_resp = _make_text_response(fallback_json)
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp) as mock_post:
        result = client.classify_with_tool(
            [{"role": "user", "content": "test"}],
            INTENT_TOOL,
            tool_name="classify_intent",
        )
    body = mock_post.call_args.kwargs["json"]
    assert "tools" not in body, "tools key leaked into text-mode request body"
    assert "tool_choice" not in body, "tool_choice leaked into text-mode request body"
    # External shape is indistinguishable from strict path
    assert isinstance(result, ToolCall)
    assert result.tool_name == "classify_intent"
    assert result.input["intent"] == "structured"


def test_sc3_text_mode_strips_markdown_fences(anthropic_env_tools_off):
    """SC #3: text-mode handles markdown-fenced JSON (mirrors query_router.py:144-148)."""
    client = AnthropicMGTIClient()
    fenced = (
        "```json\n"
        + json.dumps({
            "version": "v1", "intent": "hybrid", "confidence": 0.75,
            "reasoning": "test", "detected_filters": {},
        })
        + "\n```"
    )
    mock_resp = _make_text_response(fenced)
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        result = client.classify_with_tool(
            [{"role": "user", "content": "test"}],
            INTENT_TOOL,
            tool_name="classify_intent",
        )
    assert result.input["intent"] == "hybrid"


def test_sc3_text_mode_invalid_json_raises_schema_error(anthropic_env_tools_off):
    """SC #3: text-mode invalid JSON → LLMSchemaError (not JSONDecodeError leaking)."""
    client = AnthropicMGTIClient()
    mock_resp = _make_text_response("not valid json {{{")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "invalid JSON" in str(exc_info.value)
    assert exc_info.value.provider == "anthropic_mgti"


# ===========================================================================
# SC #4: classify_intent heuristic merge — LLM cannot overwrite chart fields
# ===========================================================================

def test_sc4_heuristic_chart_request_not_overwritten_by_llm(anthropic_env, monkeypatch):
    """SC #4 + TOOL-04: LLM injects chart_requested=True into tool_use.input;
    classify_intent's final dict reads chart_requested from the heuristic local
    (which for the benign query 'how many incidents are open' is False).
    """
    from src import query_router

    # 1. Mock _detect_chart_request to return (False, None) — heuristic says
    #    no chart for our benign query.
    monkeypatch.setattr(
        query_router, "_detect_chart_request", lambda q: (False, None)
    )

    # 2. Mock format_schema_for_llm to avoid needing real schema_summary.
    monkeypatch.setattr(
        query_router, "format_schema_for_llm", lambda s: "id, priority, state"
    )

    # 3. The LLM "tries" to inject chart_requested=True via extra_input_fields.
    #    INTENT_TOOL.input_schema has additionalProperties=False, so this
    #    WOULD fail jsonschema validation — except the schema enforcement happens
    #    INSIDE classify_with_tool. To exercise TOOL-04 we need the LLM-side
    #    injection to make it past schema validation. The cleanest way: patch
    #    classify_with_tool directly to return a ToolCall whose input has
    #    chart_requested=True (simulating a schema-relaxation regression).
    fake_call = ToolCall(
        tool_name="classify_intent",
        input={
            "version": "v1",
            "intent": "structured",
            "confidence": 0.9,
            "reasoning": "test",
            "detected_filters": {},
            "chart_requested": True,  # LLM injected — TOOL-04 says we ignore this
            "chart_type": "pie",       # ditto
        },
        raw_response={},
    )

    # Patch the get_llm-returned client's classify_with_tool method.
    mock_client = MagicMock()
    mock_client.classify_with_tool = MagicMock(return_value=fake_call)
    monkeypatch.setattr(query_router, "get_llm", lambda *a, **kw: mock_client)

    # 4. Call classify_intent and assert the FINAL dict's chart fields come
    #    from the heuristic locals (False, None), NOT from the LLM's injection.
    result = query_router.classify_intent(
        "how many incidents are open",
        schema_summary={"columns": []},
    )
    assert result["chart_requested"] is False, (
        f"LLM-injected chart_requested=True LEAKED into classify_intent output: "
        f"{result['chart_requested']!r}. TOOL-04 violated — the final dict "
        f"reads chart_requested from call.input instead of the heuristic local."
    )
    assert result["chart_type"] is None, (
        f"LLM-injected chart_type='pie' LEAKED: {result['chart_type']!r}"
    )
    # Sanity: LLM-derived fields ARE present
    assert result["intent"] == "structured"
    assert result["confidence"] == 0.9


# ===========================================================================
# SC #5: scripts/smoke_llm.py existence + syntax
# ===========================================================================

def test_sc5_smoke_script_exists():
    """SC #5: scripts/smoke_llm.py exists at the documented path."""
    assert os.path.exists(_SMOKE_SCRIPT_PATH), (
        f"{_SMOKE_SCRIPT_PATH} not found. CONTEXT.md §Verification strategy SC #5 "
        f"requires file-existence check; smoke script must ship in Plan 03."
    )


def test_sc5_smoke_script_syntax_valid():
    """SC #5: scripts/smoke_llm.py compiles cleanly via py_compile.

    RESEARCH.md Pitfall 7 + CONTEXT.md §Verification: do NOT execute the script
    here (operator-run gate, needs live creds). py_compile is the locked
    verification surface.
    """
    py_compile.compile(_SMOKE_SCRIPT_PATH, doraise=True)


# ===========================================================================
# ERROR MATRIX — 9 rows from CONTEXT.md §classify_with_tool error handling
# (rows already covered by SC #2/SC #3 above are noted; remaining rows below)
# ===========================================================================
# Covered above:
#  - HTTP 200 + missing tool_use block → LLMSchemaError (test_sc2_*)
#  - HTTP 200 + wrong tool name → LLMSchemaError (below — separate test)
#  - HTTP 200 + invalid JSON in text-mode → LLMSchemaError (test_sc3_*)
# Remaining:
#  - guardrail (1 test)
#  - max_tokens during tool_use → schema error, DIVERGES from complete() (1 test)
#  - malformed tool_use input (not dict) → schema error (1 test)
#  - jsonschema.ValidationError → schema error (1 test)
#  - wrong tool name in tool_use block → schema error (1 test)
#  - unknown stop_reason → schema error (1 test)
#  - HTTP 401/403 → LLMAuthError via _post_messages (1 test)
#  - HTTP 429/5xx → LLMTransientError via _post_messages (1 test)


def test_errmatrix_guardrail_intervened_raises_guardrail_error(anthropic_env):
    """Error matrix row 2: stop_reason=guardrail_intervened → LLMGuardrailError."""
    client = AnthropicMGTIClient()
    mock_resp = _make_guardrail_response()
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMGuardrailError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "guardrail intervened" in str(exc_info.value).lower()
    assert exc_info.value.provider == "anthropic_mgti"


def test_errmatrix_max_tokens_during_tool_use_raises_schema_error(anthropic_env):
    """Error matrix row 8: max_tokens during tool_use → LLMSchemaError.

    LOCKED DIVERGENCE from complete() — there max_tokens is outcome='truncated'
    success; here it's a schema error because partial JSON cannot be trusted
    (RESEARCH.md Pitfall 2 + CONTEXT.md decision §3 of Plan 02).
    """
    client = AnthropicMGTIClient()
    mock_resp = _make_tool_use_response(stop_reason="max_tokens")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "max_tokens" in str(exc_info.value)
    assert "ANTHROPIC_MAX_TOKENS" in str(exc_info.value), (
        "error message must include remediation hint (CONTEXT.md error matrix row 8)"
    )


def test_errmatrix_malformed_input_not_dict_raises_schema_error(anthropic_env):
    """Error matrix row 6: tool_use.input not a dict → LLMSchemaError."""
    client = AnthropicMGTIClient()
    mock_resp = _make_tool_use_response(input_not_dict="not-a-dict")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "malformed tool_use input" in str(exc_info.value)
    assert "str" in str(exc_info.value)


def test_errmatrix_schema_validation_failure_raises_schema_error(anthropic_env):
    """Error matrix row 7: jsonschema.validate fails → LLMSchemaError with .message embedded."""
    client = AnthropicMGTIClient()
    # Inject an invalid intent value — fails the enum constraint on intent
    mock_resp = _make_tool_use_response(intent="invalid_intent_xyz")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "schema validation" in str(exc_info.value).lower()
    # jsonschema error message mentions the offending value
    assert "invalid_intent_xyz" in str(exc_info.value) or "enum" in str(exc_info.value).lower()


def test_errmatrix_wrong_tool_name_raises_schema_error(anthropic_env):
    """Error matrix row 5: tool_use.name != tool_name → LLMSchemaError."""
    client = AnthropicMGTIClient()
    mock_resp = _make_tool_use_response(tool_name="some_other_tool")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "wrong tool name" in str(exc_info.value)
    assert "some_other_tool" in str(exc_info.value)


def test_errmatrix_no_tool_use_block_raises_schema_error(anthropic_env):
    """Error matrix row 4: content has only text blocks → LLMSchemaError."""
    client = AnthropicMGTIClient()
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "msg_test_xxx",
        "type": "message",
        "role": "assistant",
        "model": _MODEL_SONNET,
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "I refuse to call a tool."}],
        "usage": {"input_tokens": 50, "output_tokens": 10},
    }
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "missing tool_use block" in str(exc_info.value)


def test_errmatrix_unknown_stop_reason_raises_schema_error(anthropic_env):
    """Error matrix row 9: stop_reason not in (tool_use, end_turn, stop_sequence,
    guardrail_intervened, max_tokens) → LLMSchemaError.

    This requires the response to PASS the tool_use extraction (so we
    inject a valid tool_use block) but have an unexpected stop_reason.
    """
    client = AnthropicMGTIClient()
    mock_resp = _make_tool_use_response(stop_reason="mystery_value")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert "unknown stop_reason" in str(exc_info.value)
    assert "mystery_value" in str(exc_info.value)


def test_errmatrix_http_401_raises_auth_error(anthropic_env):
    """Error matrix row 1 (auth): HTTP 401 via _post_messages → LLMAuthError."""
    client = AnthropicMGTIClient()
    mock_resp = _make_error_envelope_response(401, "unauthorized", "bad key")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMAuthError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert exc_info.value.status_code == 401
    assert exc_info.value.provider == "anthropic_mgti"


def test_errmatrix_http_500_raises_transient_error(anthropic_env):
    """Error matrix row 1 (transient): HTTP 500 via _post_messages → LLMTransientError."""
    client = AnthropicMGTIClient()
    mock_resp = _make_error_envelope_response(500, "server_error", "upstream down")
    with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
        with pytest.raises(LLMTransientError) as exc_info:
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    assert exc_info.value.status_code == 500


# ===========================================================================
# COMPAT-DISPATCH — mirror tests/test_phase3_adapter.py:519-552 pattern
# Locks against "Anthropic error surfaces as Azure-named QueryError" regression
# ===========================================================================

def test_compat_dispatch_schema_error_translates_to_anthropic_query_error():
    """COMPAT-DISPATCH: LLMSchemaError(provider='anthropic_mgti') → QueryError
    with 'Anthropic API call failed' (NOT 'Azure OpenAI API call failed').

    Exercises _compat.py's catch-all `except LLMError` branch (which already
    dispatches by e.provider since Phase 3). No _compat.py edits in Phase 4 —
    this is the regression guard ensuring the dispatch covers LLMSchemaError.
    """
    with pytest.raises(QueryError) as exc_info:
        with llm_to_query_error():
            raise LLMSchemaError(
                "test schema failure", provider="anthropic_mgti"
            )
    assert exc_info.value.message == "Anthropic API call failed", (
        f"LLMSchemaError mistranslated as: {exc_info.value.message!r}. "
        f"If this says 'Azure OpenAI API call failed', _compat.py dispatch "
        f"regressed for the LLMSchemaError → QueryError path."
    )
    assert "test schema failure" in (exc_info.value.details or "")


def test_compat_dispatch_guardrail_error_translates_to_anthropic_query_error():
    """COMPAT-DISPATCH: LLMGuardrailError(provider='anthropic_mgti') → QueryError
    with 'Anthropic API call failed'.

    Phase 3's COMPAT-DISPATCH covered LLMAuthError and LLMTimeoutError; Phase 4
    extends to LLMGuardrailError which is now reachable from classify_with_tool.
    """
    with pytest.raises(QueryError) as exc_info:
        with llm_to_query_error():
            raise LLMGuardrailError(
                "guardrail intervened", provider="anthropic_mgti"
            )
    assert exc_info.value.message == "Anthropic API call failed"
    assert "guardrail intervened" in (exc_info.value.details or "")


# ===========================================================================
# Log-event assertions — startup log has tools_supported; llm_call has llm_tool_mode
# ===========================================================================

class _LogCapturer:
    """Lightweight log-record capturer for assertion in tests.

    Mirrors the Phase 3 _RecordCapturer pattern (STATE.md Phase 3-04 decision:
    'class-level helper (not a fixture) — adds handler in test body and
    removes in finally; no global logger mutation').
    """
    def __init__(self):
        self.records: list[logging.LogRecord] = []

    def __call__(self, record: logging.LogRecord) -> bool:
        self.records.append(record)
        return True


def test_logs_startup_log_contains_tools_supported(anthropic_env):
    """Plan 02 decision §8: llm_provider_loaded log has tools_supported: bool field."""
    capturer = _LogCapturer()
    handler = logging.Handler()
    handler.addFilter(capturer)
    snow_logger.addHandler(handler)
    try:
        AnthropicMGTIClient()  # triggers startup log
    finally:
        snow_logger.removeHandler(handler)

    startup_events = [
        r for r in capturer.records
        if getattr(r, "provider", None) == "anthropic_mgti"
        and r.getMessage() == "llm_provider_loaded"
    ]
    assert len(startup_events) >= 1, "no llm_provider_loaded event captured"
    ev = startup_events[0]
    assert hasattr(ev, "tools_supported"), (
        "llm_provider_loaded event missing tools_supported field — "
        "Plan 02 decision §8 violated"
    )
    assert ev.tools_supported is True, (
        f"tools_supported should be True for default env: {ev.tools_supported!r}"
    )


def test_logs_classify_with_tool_strict_path_emits_one_event_with_llm_tool_mode_strict(anthropic_env):
    """RESEARCH.md Pitfall 6 + Plan 02 decision §7: strict path emits exactly ONE
    llm_call event tagged llm_tool_mode='strict'.
    """
    capturer = _LogCapturer()
    handler = logging.Handler()
    handler.addFilter(capturer)
    snow_logger.addHandler(handler)
    try:
        client = AnthropicMGTIClient()
        mock_resp = _make_tool_use_response()
        with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    finally:
        snow_logger.removeHandler(handler)

    call_events = [
        r for r in capturer.records
        if r.getMessage() == "llm_call"
        and getattr(r, "llm_provider", None) == "anthropic_mgti"
    ]
    assert len(call_events) == 1, (
        f"strict path should emit exactly 1 llm_call event, got "
        f"{len(call_events)}: {[r.getMessage() for r in call_events]}"
    )
    ev = call_events[0]
    assert getattr(ev, "llm_tool_mode", None) == "strict", (
        f"llm_tool_mode should be 'strict', got "
        f"{getattr(ev, 'llm_tool_mode', None)!r}"
    )


def test_logs_classify_with_tool_text_fallback_emits_one_event_with_llm_tool_mode_text_fallback(anthropic_env_tools_off):
    """RESEARCH.md Pitfall 6 + Plan 02 decision §7 + user-locked decision §3:
    text-mode fallback emits EXACTLY ONE llm_call event tagged
    llm_tool_mode='text_fallback'. The delegate's (complete()'s) event is
    suppressed via _emit_log=False.
    """
    capturer = _LogCapturer()
    handler = logging.Handler()
    handler.addFilter(capturer)
    snow_logger.addHandler(handler)
    try:
        client = AnthropicMGTIClient()
        fallback_json = json.dumps({
            "version": "v1", "intent": "structured", "confidence": 0.9,
            "reasoning": "test", "detected_filters": {},
        })
        mock_resp = _make_text_response(fallback_json)
        with patch("src.llm.anthropic_mgti.requests.post", return_value=mock_resp):
            client.classify_with_tool(
                [{"role": "user", "content": "test"}],
                INTENT_TOOL,
                tool_name="classify_intent",
            )
    finally:
        snow_logger.removeHandler(handler)

    call_events = [
        r for r in capturer.records
        if r.getMessage() == "llm_call"
        and getattr(r, "llm_provider", None) == "anthropic_mgti"
    ]
    assert len(call_events) == 1, (
        f"text-mode fallback should emit exactly 1 llm_call event "
        f"(delegate's complete() event suppressed via _emit_log=False), "
        f"got {len(call_events)}. If 2, Pitfall 6 regressed."
    )
    ev = call_events[0]
    assert getattr(ev, "llm_tool_mode", None) == "text_fallback", (
        f"llm_tool_mode should be 'text_fallback', got "
        f"{getattr(ev, 'llm_tool_mode', None)!r}"
    )
```

**Run the suite as you write to catch issues early:**

```bash
# After every batch of tests, run the new module to validate
pytest tests/test_phase4_strict_tools.py -v --tb=short
```

Fix as needed; do not stop until ALL named tests pass.
  </action>
  <verify>
```bash
# 1. Precondition: jsonschema version
python -c "import jsonschema; print(jsonschema.__version__)"
# Expected: 4.26.x or higher

# 2. New test file exists
ls -la tests/test_phase4_strict_tools.py
# Expected: file present

# 3. No new fixture files or conftest.py
ls tests/conftest.py tests/fixtures/phase4* 2>/dev/null
# Expected: no matches (matches Phase 1/2/3 pattern)

# 4. Run Phase 4 gate ALONE
pytest tests/test_phase4_strict_tools.py -v
# Expected: ~25 tests, ALL PASSING, in <10 seconds

# 5. Run combined Phase 1+2+3+4 gate
pytest tests/ -v
# Expected: ~64 tests (39 from prior phases + ~25 Phase 4), ALL PASSING

# 6. Confirm zero live HTTP — assert tests pass even WITHOUT internet by simulating
# (no need to disable network; the patch('requests.post') mocks should mean no real call)
pytest tests/test_phase4_strict_tools.py -v --tb=short
# (re-run; should still pass — mocks deterministic)

# 7. Smoke script existence test passes
pytest tests/test_phase4_strict_tools.py::test_sc5_smoke_script_exists tests/test_phase4_strict_tools.py::test_sc5_smoke_script_syntax_valid -v
# Expected: 2 passed

# 8. COMPAT-DISPATCH tests pass
pytest tests/test_phase4_strict_tools.py -v -k compat_dispatch
# Expected: 2 passed

# 9. Log-assertion tests pass
pytest tests/test_phase4_strict_tools.py -v -k logs_
# Expected: 3 passed

# 10. Only the declared file modified
git diff --stat HEAD -- src/ scripts/ tests/
# Expected: ONLY tests/test_phase4_strict_tools.py (plus any earlier-plan deletions
# already committed)

# 11. Test discovery (sanity)
pytest tests/test_phase4_strict_tools.py --collect-only -q
# Expected: ~25 test ids listed; no collection errors
```
  </verify>
  <done>
`tests/test_phase4_strict_tools.py` exists with ~25 tests covering all 5 Phase 4 SCs, all 9 error matrix rows (some via SC tests, the rest as explicit `test_errmatrix_*`), 2 COMPAT-DISPATCH tests, 3 log-event assertions, and 2 SC #5 smoke-script tests using `os.path.exists` + `py_compile.compile(doraise=True)`. Zero conftest.py. Zero pytest.ini. Zero fixture files in tests/fixtures/phase4*. Zero live HTTP — all mocked. Combined Phase 1+2+3+4 pytest run is ~64 tests, all passing. Only `tests/test_phase4_strict_tools.py` modified.
  </done>
</task>

</tasks>

<verification>
Phase-level verification for Plan 04 (and Phase 4 overall):

1. **Combined gate green:**
   ```bash
   pytest tests/ -v
   # Expected: ~64 tests pass; 0 failures; <15 seconds wall-clock
   ```

2. **No new fixture infrastructure:**
   ```bash
   ls tests/conftest.py tests/pytest.ini tests/fixtures/phase4* 2>/dev/null
   # Expected: zero output
   ```

3. **Self-contained module count:**
   ```bash
   pytest tests/test_phase4_strict_tools.py --collect-only -q | wc -l
   # Expected: ~26 (25 test functions + 1 summary line); ±3 tolerance
   ```

4. **All 5 SCs traceable:**
   ```bash
   grep -n "def test_sc[0-9]_" tests/test_phase4_strict_tools.py
   # Expected: SC #1 (≥5), SC #2 (≥3), SC #3 (≥3), SC #4 (≥1), SC #5 (=2)
   ```

5. **All 9 error matrix rows traceable:**
   ```bash
   grep -nE "def test_errmatrix_|def test_sc[23]_" tests/test_phase4_strict_tools.py | wc -l
   # Expected: ≥9 (some rows covered by SC tests, rest by test_errmatrix_*)
   ```

6. **COMPAT-DISPATCH pair present:**
   ```bash
   grep -n "def test_compat_dispatch" tests/test_phase4_strict_tools.py
   # Expected: 2 matches (LLMSchemaError + LLMGuardrailError)
   ```

7. **Log assertions present:**
   ```bash
   grep -n "def test_logs_" tests/test_phase4_strict_tools.py
   # Expected: 3 matches (startup tools_supported, strict path 1-event, text fallback 1-event)
   ```

8. **No subprocess.run on smoke script (Pitfall 7):**
   ```bash
   grep -n "subprocess" tests/test_phase4_strict_tools.py
   # Expected: ZERO matches
   ```

9. **Phase 1+2+3 gates preserved:**
   ```bash
   pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py -v
   # Expected: 39 passed (Phase 3 may be 20 if NotImplementedError test was deleted by Plan 02)
   ```

10. **Plan 04's diff touches ONLY its declared file:**
    ```bash
    git diff --stat HEAD -- src/ scripts/ tests/
    # Expected: ONLY tests/test_phase4_strict_tools.py
    ```
</verification>

<success_criteria>
- [ ] `tests/test_phase4_strict_tools.py` exists; `pytest tests/test_phase4_strict_tools.py -v` → all green (~25 tests)
- [ ] No `tests/conftest.py`, no `tests/pytest.ini`, no `tests/fixtures/phase4*` files created
- [ ] Inline mock builders present: `_make_tool_use_response`, `_make_text_response`, `_make_guardrail_response`, `_make_error_envelope_response`
- [ ] Autouse `_clear_factory_cache` and `_strip_llm_env` fixtures mirror Phase 3 verbatim
- [ ] SC #1 covered: 5+ tests on INTENT_TOOL derivation (presence, dataclass-match, intent enum, version plain string, chart absence, additionalProperties)
- [ ] SC #2 covered: 3+ tests on strict-tools (body shape, valid → ToolCall, mixed text+tool_use)
- [ ] SC #3 covered: 3+ tests on text-mode fallback (env-flag triggers, no tools key in body, fence-stripping + invalid JSON)
- [ ] SC #4 covered: 1 test on heuristic-merge regression (LLM-injected chart_requested=True does NOT leak into classify_intent output)
- [ ] SC #5 covered: 2 tests (`os.path.exists` + `py_compile.compile(doraise=True)`); NO subprocess.run; NO live execution
- [ ] Error matrix rows covered by test_errmatrix_* functions: guardrail, max_tokens-during-tool_use (with `ANTHROPIC_MAX_TOKENS` remediation hint asserted), malformed-input-not-dict, jsonschema-validation-failure, wrong-tool-name, no-tool_use-block, unknown-stop_reason, HTTP 401, HTTP 500
- [ ] COMPAT-DISPATCH pair: `test_compat_dispatch_schema_error_*` AND `test_compat_dispatch_guardrail_error_*` both assert `QueryError.message == "Anthropic API call failed"` (the regression guard)
- [ ] Log-event tests: startup log has `tools_supported`; strict path emits 1 llm_call with `llm_tool_mode='strict'`; text-fallback path emits 1 llm_call with `llm_tool_mode='text_fallback'`
- [ ] `test_precondition_jsonschema_version` is the first non-fixture test; fails clearly if dev box is on 4.25.x
- [ ] Combined `pytest tests/` is ~64 tests, all passing, in <15 seconds; zero live HTTP
- [ ] Phase 4 (the milestone): all 5 ROADMAP SCs proven; Phase 5 (Sidebar UI) is now unblocked pending operator-run smoke gate against stage gateway
</success_criteria>

<output>
After completion, create `.planning/phases/04-strict-tools-smoke-test/04-04-SUMMARY.md` documenting:
- Total test count and pass-time
- Mapping from each Phase 4 SC to its proving test function(s) (5 entries)
- Mapping from each CONTEXT.md error matrix row to its test function (9 entries)
- COMPAT-DISPATCH coverage summary (LLMSchemaError, LLMGuardrailError vs Phase 3's LLMAuthError, LLMTimeoutError)
- Confirmation: zero live HTTP; zero conftest.py; zero fixture files
- Combined Phase 1+2+3+4 result: e.g. `39 + 25 = 64 passed in 12.4s`
- Phase 4 sign-off statement: "All 5 ROADMAP success criteria proven; Anthropic strict-tools + text-mode fallback + operator-run smoke gate shipped. classify_intent uses provider-side strict tools when ANTHROPIC_TOOLS_SUPPORTED=true and JSON-parse fallback when false; heuristic-merge regression locked by SC #4 test. Phase 5 (Sidebar UI Toggle) is unblocked pending operator-run smoke gate against stage gateway."
- Pending operator action: "Set `.env` with stage gateway URLs + valid keys, then run `python scripts/smoke_llm.py --provider both --verbose` and paste the transcript into the Phase 4 verification PR. Without this, Phase 5 work should not begin (per SMK-05 / CONTEXT.md §Smoke script credential)."
</output>
</content>
</invoke>