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
    """Each test sees an empty get_llm cache.

    Phase 5 Plan 05-01: _cache dict deleted, replaced by @_cache_resource on
    _get_llm_cached. The decorated function exposes .clear() under Streamlit;
    in the no-Streamlit fallback no .clear() attribute exists — defended via
    getattr-with-callable.
    """
    import src.llm as llm_pkg
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
    yield
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()


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
    """Error matrix row 9: stop_reason not in known set → LLMSchemaError.

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

class _RecordCapturer(logging.Handler):
    """Capture log records for the test's lifetime.

    MIRRORS tests/test_phase3_adapter.py:412-420 VERBATIM (STATE.md Phase 3-04
    decision: 'class-level helper (not a fixture) — adds handler in test body
    and removes in finally; no global logger mutation'). Locked decision §3
    of this plan requires Phase 3 idiom verbatim — subclass logging.Handler
    and override emit(), then register via snow_logger.addHandler(cap) /
    snow_logger.removeHandler(cap). Do NOT use addFilter on a vanilla
    logging.Handler() — its default emit() raises NotImplementedError and
    pollutes test output.
    """

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_logs_startup_log_contains_tools_supported(anthropic_env):
    """Plan 02 decision §8: llm_provider_loaded log has tools_supported: bool field."""
    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
    try:
        AnthropicMGTIClient()  # triggers startup log
    finally:
        snow_logger.removeHandler(cap)

    startup_events = [
        r for r in cap.records
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
    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
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
        snow_logger.removeHandler(cap)

    call_events = [
        r for r in cap.records
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
    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
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
        snow_logger.removeHandler(cap)

    call_events = [
        r for r in cap.records
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
