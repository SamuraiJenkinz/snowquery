---
phase: 03-anthropic-mgti-adapter
plan: 04
type: execute
wave: 3
depends_on: ["03-01", "03-02", "03-03"]
files_modified:
  - tests/test_phase3_adapter.py
autonomous: true

must_haves:
  truths:
    - "tests/test_phase3_adapter.py exists as a SELF-CONTAINED pytest module (no conftest.py, no pytest.ini — matches Phase 1/Phase 2 gate convention) proving all 5 Phase 3 ROADMAP success criteria; each test docstring cites the SC it proves; the test names are mnemonic for the SC + dimension"
    - "Test runs OFFLINE — zero live HTTP. All requests.post is patched via unittest.mock.patch; response bodies are inline Python dicts (NO fixture files — Phase 3 has no parity baseline so the Phase 2 fixture pattern does not apply per CONTEXT.md)"
    - "SC #1 proven by tests: URL construction (`{base_url}/model/{model}/messages` exact suffix), header presence (X-Api-Key, Content-Type, X-Correlation-Id all three present), and fresh UUID per call (two complete() calls produce two DIFFERENT X-Correlation-Id headers)"
    - "SC #2 proven by tests: (a) constructing AnthropicMGTIClient with ANTHROPIC_MODEL='gpt-4o' (or any non-eu.anthropic.claude- string) raises LLMConfigError at __init__; (b) constructing with empty ANTHROPIC_MODEL does NOT raise at __init__ (no-op pattern preserved); (c) constructing with ANTHROPIC_MODEL='eu.anthropic.claude-opus-4-7-20251201-v1:0' and calling complete() produces a request body where 'temperature', 'top_p', AND 'top_k' are all absent; (d) for non-opus eu.anthropic.claude-* model the body INCLUDES 'temperature'"
    - "SC #3 proven by tests for EVERY mapping in the criterion: 401→LLMAuthError, 403→LLMAuthError, 429→LLMTransientError, 503→LLMTransientError, requests.Timeout→LLMTimeoutError, stop_reason='guardrail_intervened'→LLMGuardrailError, HTTP 200 + empty content + stop_reason='end_turn' (NON-guardrail)→LLMSchemaError. The (e) and (f) cases are the load-bearing regression guards for the order bug in RESEARCH.md Pitfall 4."
    - "SC #4 proven by reading .env.example as text and asserting all 9 variables present with non-empty values: LLM_PROVIDER_DEFAULT, ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_VERSION, ANTHROPIC_MAX_TOKENS, ANTHROPIC_TEMPERATURE, ANTHROPIC_TIMEOUT_S, ANTHROPIC_TOOLS_SUPPORTED"
    - "SC #5 proven by tests: (a) constructing get_llm('anthropic_mgti') TWICE emits exactly ONE 'llm_provider_loaded' log event (factory cache idempotence); (b) constructing get_llm('azure_openai') ALSO emits 'llm_provider_loaded' for that provider (the Azure half installed in Plan 01); (c) inspect.getsource(generate_sql) AND inspect.getsource(generate_executive_summary) BOTH do NOT contain the string 'classify_with_tool' — the call sites use complete() only (no tool wrapping)"
    - "Test gate proves end-to-end LLMError→QueryError dispatch lands the Anthropic wording: LLMAuthError(provider='anthropic_mgti') translates to QueryError(message='Anthropic API key not configured or not authorised', details='Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.') — exercises Plan 02's dispatch end-to-end through llm_to_query_error()"
    - "Phase 1 + Phase 2 + Phase 3 acceptance gates all green when run together: pytest tests/ shows 18 (Phase 1+2) + N Phase 3 tests passing; the same combined run is the user-facing 'phase complete' signal"
  artifacts:
    - path: "tests/test_phase3_adapter.py"
      provides: "Phase 3 acceptance gate — pytest module proving all 5 Phase 3 success criteria, plus end-to-end Anthropic LLMError→QueryError dispatch through Plan 02's compat layer."
      min_lines: 350
      exports: ["test_url_construction", "test_required_headers_present", "test_fresh_correlation_id_per_call", "test_init_raises_on_bad_model_prefix", "test_init_no_raise_on_empty_model", "test_opus_4_7_omits_sampling_params", "test_non_opus_includes_temperature", "test_http_401_raises_auth_error", "test_http_403_raises_auth_error", "test_http_429_raises_transient_error", "test_http_503_raises_transient_error", "test_requests_timeout_raises_timeout_error", "test_guardrail_intervened_raises_guardrail_error", "test_empty_content_non_guardrail_raises_schema_error", "test_env_example_has_all_9_anthropic_vars", "test_startup_log_anthropic_provider", "test_startup_log_azure_provider", "test_factory_cache_dedupes_startup_log", "test_no_tool_wrapping_in_call_sites", "test_anthropic_auth_error_translates_to_anthropic_query_error", "test_anthropic_timeout_translates_to_anthropic_query_error"]
  key_links:
    - from: "tests/test_phase3_adapter.py"
      to: "src.llm.anthropic_mgti.AnthropicMGTIClient (the real adapter from Plan 03)"
      via: "patch('requests.post', ...) — exercises the real adapter against inline-dict mocked responses"
      pattern: "patch\\(['\\\"]requests\\.post['\\\"]"
    - from: "tests/test_phase3_adapter.py"
      to: "src.llm._compat.llm_to_query_error (with Plan 02's per-provider dispatch)"
      via: "with llm_to_query_error(): raise LLMAuthError(provider='anthropic_mgti', ...) — assert QueryError has Anthropic wording"
      pattern: "llm_to_query_error"
    - from: "tests/test_phase3_adapter.py"
      to: "src.utils.logger"
      via: "adds a logging.Handler to capture llm_provider_loaded events and asserts factory cache idempotence (1 event per provider per process)"
      pattern: "llm_provider_loaded"
    - from: "tests/test_phase3_adapter.py"
      to: ".env.example"
      via: "reads file, asserts each of the 9 new vars present as NAME=... with non-empty value"
      pattern: "ANTHROPIC_(BASE_URL|API_KEY|MODEL|VERSION|MAX_TOKENS|TEMPERATURE|TIMEOUT_S|TOOLS_SUPPORTED)|LLM_PROVIDER_DEFAULT"
---

<objective>
Build the Phase 3 acceptance gate `tests/test_phase3_adapter.py` — one pytest module proving all 5 Phase 3 ROADMAP success criteria in a single offline run. Mirrors the Phase 1 (`tests/test_llm_seam.py`) and Phase 2 (`tests/test_phase2_parity.py`) gate convention: self-contained, no `conftest.py`, autouse fixtures clear factory cache + strip env, inline mocked responses (no fixture files — Phase 3 has no parity baseline so the Phase 2 fixture-file pattern does not apply per CONTEXT.md).

Purpose: A green pytest run on this module IS the Phase 3 gate. If any test fails, Phase 3 is not done and the failing test name pinpoints which SC regressed. Combined with the Phase 1/2 gates: 18 (Phase 1+2) + N (Phase 3) tests passing on `pytest tests/` is the user-facing "Phase 3 complete" signal.

Output: One pytest module (`tests/test_phase3_adapter.py`) — ~21 test functions across 5 SC groupings + an end-to-end compat dispatch group, ~350-450 lines total. NO fixture files.

The module must:
- Use the same autouse fixture pattern from `tests/test_phase2_parity.py` (`_clear_factory_cache`, `_strip_llm_env`) extended to strip Anthropic env vars too.
- Define inline mock-response builder helpers `_make_anthropic_response(...)` and `_make_error_response(...)` per RESEARCH.md "Mock Response Builder Pattern".
- Patch `requests.post` (Level A) for adapter-direct tests; reach into the factory cache (`src.llm._cache`) where needed for cache-idempotence tests.
- Cover ALL the load-bearing edge cases — the guardrail-before-emptiness ordering, the opus-4-7 sampling-param omission, the empty-model no-raise at __init__.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-anthropic-mgti-adapter/03-CONTEXT.md
@.planning/phases/03-anthropic-mgti-adapter/03-RESEARCH.md
@.planning/phases/03-anthropic-mgti-adapter/03-01-SUMMARY.md
@.planning/phases/03-anthropic-mgti-adapter/03-02-SUMMARY.md
@.planning/phases/03-anthropic-mgti-adapter/03-03-SUMMARY.md

# Real artifacts under test
@src/llm/anthropic_mgti.py
@src/llm/azure_openai.py
@src/llm/_compat.py
@src/llm/__init__.py
@.env.example

# The Phase 2 pattern this gate mirrors
@tests/test_phase2_parity.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests/test_phase3_adapter.py — Phase 3 acceptance gate covering all 5 SCs + end-to-end compat dispatch</name>
  <files>tests/test_phase3_adapter.py</files>
  <action>
Create `tests/test_phase3_adapter.py`. The module has FIVE SC-grouped test sections plus a sixth COMPAT-DISPATCH group:

- **SC #1 group** (URL + headers + fresh UUID): `test_url_construction`, `test_required_headers_present`, `test_fresh_correlation_id_per_call`
- **SC #2 group** (model validation + opus sampling-param omission): `test_init_raises_on_bad_model_prefix`, `test_init_no_raise_on_empty_model`, `test_opus_4_7_omits_sampling_params`, `test_non_opus_includes_temperature`
- **SC #3 group** (typed-error mapping + the order-sensitive guardrail-before-emptiness): `test_http_401_raises_auth_error`, `test_http_403_raises_auth_error`, `test_http_429_raises_transient_error`, `test_http_503_raises_transient_error`, `test_requests_timeout_raises_timeout_error`, `test_guardrail_intervened_raises_guardrail_error`, `test_empty_content_non_guardrail_raises_schema_error`
- **SC #4 group** (`.env.example` shape): `test_env_example_has_all_9_anthropic_vars`
- **SC #5 group** (startup log per provider + no tool wrapping): `test_startup_log_anthropic_provider`, `test_startup_log_azure_provider`, `test_factory_cache_dedupes_startup_log`, `test_no_tool_wrapping_in_call_sites`
- **COMPAT-DISPATCH group** (end-to-end through Plan 02's per-provider dispatch): `test_anthropic_auth_error_translates_to_anthropic_query_error`, `test_anthropic_timeout_translates_to_anthropic_query_error`

Total: 21 tests.

Exact file contents below. The module is self-contained — DO NOT add a conftest.py or pytest.ini.

```python
"""Phase 3 acceptance gate: prove all 5 Phase 3 success criteria.

Each test function maps to one of the 5 numbered Phase 3 ROADMAP success
criteria. A green pytest run on this module IS the Phase 3 gate.

Conventions inherited from tests/test_phase2_parity.py:
  - autouse _clear_factory_cache + _strip_llm_env fixtures isolate
    module-level singletons and env-var state between tests.
  - HTTP is mocked via unittest.mock.patch('requests.post', ...) (Level A).
  - Inline Python dicts as response bodies — NO fixture files. (CONTEXT.md:
    Phase 3 has no parity baseline so the Phase 2 fixture-file pattern
    does not apply.)
  - Tests have ZERO live external dependencies.

Run with: `pytest tests/test_phase3_adapter.py -v`
Or combined with Phase 1+2: `pytest tests/ -v` (expected: 18 + 21 = 39 tests)
"""
from __future__ import annotations

import inspect
import logging
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.llm.anthropic_mgti import AnthropicMGTIClient
from src.llm.azure_openai import AzureOpenAIClient
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMGuardrailError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.utils import QueryError, logger as snow_logger

# Realistic Anthropic env values for happy-path tests
_BASE_URL = "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1"
_API_KEY = "test-key-not-real"
_MODEL_SONNET = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
_MODEL_OPUS_4_7 = "eu.anthropic.claude-opus-4-7-20251201-v1:0"

# Realistic Azure env values for the SC #5 Azure-half test
_AZURE_ENDPOINT = "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"
_AZURE_KEY = "azure-test-key-not-real"


# ---------------------------------------------------------------------------
# Autouse fixtures — same pattern as tests/test_phase2_parity.py.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Ensure each test sees an empty get_llm cache."""
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


@pytest.fixture
def anthropic_env(monkeypatch):
    """Set realistic Anthropic env so AnthropicMGTIClient constructs cleanly
    with the SONNET model (passes the eu.anthropic.claude- prefix check)."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", _BASE_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", _MODEL_SONNET)


@pytest.fixture
def opus_env(monkeypatch):
    """Set Anthropic env with the OPUS-4-7 model (triggers sampling-param omission)."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", _BASE_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", _MODEL_OPUS_4_7)


# ---------------------------------------------------------------------------
# Inline mock-response builders (no fixture files — RESEARCH.md pattern).
# ---------------------------------------------------------------------------

def _make_anthropic_response(
    text: str = "Hello.",
    stop_reason: str = "end_turn",
    input_tokens: int = 25,
    output_tokens: int = 10,
    model: str = _MODEL_SONNET,
) -> MagicMock:
    """Build a MagicMock imitating a successful MGTI response.

    When text='' the content array is empty (used for guardrail + empty-content
    LLMSchemaError tests). When text is non-empty there is exactly one text block.
    """
    resp = MagicMock()
    resp.status_code = 200
    resp.ok = True
    resp.json.return_value = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}] if text else [],
        "stop_reason": stop_reason,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    return resp


def _make_error_response(
    status_code: int,
    title: str = "Error",
    detail: str = "detail",
) -> MagicMock:
    """Build a MagicMock imitating an MGTI 4xx/5xx error response.

    Uses the MGTI proxy envelope shape {"error": {"title", "detail", "status"}}.
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = False
    resp.json.return_value = {
        "error": {"title": title, "detail": detail, "status": status_code}
    }
    resp.text = f"{title}: {detail}"
    return resp


# ===========================================================================
# SC #1 — POST {base_url}/model/{model}/messages with X-Api-Key,
# Content-Type: application/json, and a fresh X-Correlation-Id UUID per call.
# ===========================================================================

def test_url_construction(anthropic_env):
    """SC #1: complete() POSTs to f'{base_url}/model/{model}/messages'.

    The /messages suffix is mandatory — RESEARCH.md flags this as the bug
    that survived production code review (the spec PDF originally omitted it).
    """
    client = get_llm("anthropic_mgti")
    assert isinstance(client, AnthropicMGTIClient)

    with patch("requests.post", return_value=_make_anthropic_response()) as mp:
        client.complete([{"role": "user", "content": "hi"}], max_tokens=64)

    call_args = mp.call_args
    url = call_args.args[0] if call_args.args else call_args.kwargs["url"]
    expected = f"{_BASE_URL}/model/{_MODEL_SONNET}/messages"
    assert url == expected, f"URL mismatch: got {url!r}, expected {expected!r}"


def test_required_headers_present(anthropic_env):
    """SC #1: headers MUST include X-Api-Key, Content-Type=application/json,
    and X-Correlation-Id (a valid UUID).
    """
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_anthropic_response()) as mp:
        client.complete([{"role": "user", "content": "hi"}])
    headers = mp.call_args.kwargs["headers"]
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Api-Key"] == _API_KEY
    assert "X-Correlation-Id" in headers, "X-Correlation-Id header missing"
    uuid.UUID(headers["X-Correlation-Id"])  # raises ValueError if not a valid UUID


def test_fresh_correlation_id_per_call(anthropic_env):
    """SC #1: two complete() calls produce two DIFFERENT X-Correlation-Id headers."""
    client = get_llm("anthropic_mgti")
    captured_ids: list[str] = []

    def _capture(*args, **kwargs):
        captured_ids.append(kwargs["headers"]["X-Correlation-Id"])
        return _make_anthropic_response()

    with patch("requests.post", side_effect=_capture):
        client.complete([{"role": "user", "content": "a"}])
        client.complete([{"role": "user", "content": "b"}])

    assert len(captured_ids) == 2
    assert len(set(captured_ids)) == 2, (
        f"X-Correlation-Id repeated across calls: {captured_ids}"
    )
    for cid in captured_ids:
        uuid.UUID(cid)


# ===========================================================================
# SC #2 — Bad model prefix raises LLMConfigError at __init__; opus-4-7
# models OMIT temperature/top_p/top_k from the request body.
# ===========================================================================

def test_init_raises_on_bad_model_prefix(monkeypatch):
    """SC #2 first half: non-empty ANTHROPIC_MODEL that doesn't start with
    'eu.anthropic.claude-' raises LLMConfigError at __init__."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", _BASE_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", "gpt-4o")
    with pytest.raises(LLMConfigError) as exc_info:
        AnthropicMGTIClient()
    assert exc_info.value.provider == "anthropic_mgti"
    assert "eu.anthropic.claude-" in str(exc_info.value), (
        f"remediation text missing eu.anthropic.claude- mention: {exc_info.value}"
    )


def test_init_no_raise_on_empty_model():
    """SC #2 boundary: empty ANTHROPIC_MODEL does NOT raise at __init__.

    Preserves the Phase 1 no-op pattern — the factory cache must be able to
    store the instance even when config is missing. Missing config is caught
    at HTTP time in complete() via the pre-flight LLMConfigError raise.
    """
    # No env vars set (autouse _strip_llm_env strips ANTHROPIC_MODEL)
    client = AnthropicMGTIClient()  # MUST NOT raise
    assert isinstance(client, AnthropicMGTIClient)
    # Verify the at-HTTP-time pre-flight DOES raise when complete() is called
    with pytest.raises(LLMConfigError) as exc_info:
        client.complete([{"role": "user", "content": "x"}])
    assert exc_info.value.provider == "anthropic_mgti"


def test_opus_4_7_omits_sampling_params(opus_env):
    """SC #2 second half: opus-4-7 model OMITS temperature/top_p/top_k from body."""
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_anthropic_response(model=_MODEL_OPUS_4_7)) as mp:
        # Pass temperature explicitly — adapter MUST still omit it because
        # the model is opus-4-7.
        client.complete([{"role": "user", "content": "x"}], temperature=0.5)
    body = mp.call_args.kwargs["json"]
    assert "temperature" not in body, f"opus-4-7 must OMIT temperature: {body}"
    assert "top_p" not in body, f"opus-4-7 must OMIT top_p: {body}"
    assert "top_k" not in body, f"opus-4-7 must OMIT top_k: {body}"
    # And the required fields MUST still be there
    assert body["max_tokens"] > 0
    assert body["anthropic_version"] == "bedrock-2023-05-31"


def test_non_opus_includes_temperature(anthropic_env):
    """SC #2 boundary: non-opus eu.anthropic.claude-* model INCLUDES temperature.

    The SONNET model is not opus-4-7 so temperature IS sent in the body
    (sourced from the kwarg or env default).
    """
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_anthropic_response()) as mp:
        client.complete([{"role": "user", "content": "x"}], temperature=0.3)
    body = mp.call_args.kwargs["json"]
    assert body.get("temperature") == 0.3, (
        f"non-opus model must INCLUDE temperature from kwarg: {body}"
    )
    # top_p/top_k still omitted (caller didn't pass them — Phase 3 doesn't
    # plumb arbitrary kwargs through; that's a Phase 4+ concern)
    assert "top_p" not in body
    assert "top_k" not in body


# ===========================================================================
# SC #3 — MGTI HTTP error mapping (401/403/429/5xx/Timeout) plus the
# order-sensitive guardrail-before-emptiness check.
# ===========================================================================

def test_http_401_raises_auth_error(anthropic_env):
    """SC #3: HTTP 401 raises LLMAuthError with provider='anthropic_mgti'."""
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_error_response(401, "Unauthorized", "Invalid API key")):
        with pytest.raises(LLMAuthError) as exc_info:
            client.complete([{"role": "user", "content": "x"}])
    assert exc_info.value.provider == "anthropic_mgti"
    assert exc_info.value.status_code == 401
    # MGTI envelope title/detail must be parsed into the message
    assert "Unauthorized" in str(exc_info.value) or "Invalid API key" in str(exc_info.value)


def test_http_403_raises_auth_error(anthropic_env):
    """SC #3: HTTP 403 raises LLMAuthError (same family as 401)."""
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_error_response(403, "Forbidden", "no access")):
        with pytest.raises(LLMAuthError):
            client.complete([{"role": "user", "content": "x"}])


def test_http_429_raises_transient_error(anthropic_env):
    """SC #3: HTTP 429 raises LLMTransientError."""
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_error_response(429, "TooMany", "rate limited")):
        with pytest.raises(LLMTransientError) as exc_info:
            client.complete([{"role": "user", "content": "x"}])
    assert exc_info.value.status_code == 429


def test_http_503_raises_transient_error(anthropic_env):
    """SC #3: HTTP 503 raises LLMTransientError (5xx family)."""
    client = get_llm("anthropic_mgti")
    with patch("requests.post", return_value=_make_error_response(503, "Service Unavailable", "down")):
        with pytest.raises(LLMTransientError):
            client.complete([{"role": "user", "content": "x"}])


def test_requests_timeout_raises_timeout_error(anthropic_env):
    """SC #3: requests.exceptions.Timeout raises LLMTimeoutError."""
    client = get_llm("anthropic_mgti")
    with patch("requests.post", side_effect=requests.exceptions.Timeout("simulated")):
        with pytest.raises(LLMTimeoutError) as exc_info:
            client.complete([{"role": "user", "content": "x"}])
    assert exc_info.value.provider == "anthropic_mgti"


def test_guardrail_intervened_raises_guardrail_error(anthropic_env):
    """SC #3: HTTP 200 + stop_reason='guardrail_intervened' raises LLMGuardrailError.

    The guardrail response has EMPTY content[] — but the adapter MUST check
    stop_reason BEFORE checking content emptiness (RESEARCH.md Pitfall 4),
    otherwise this case would surface as LLMSchemaError instead.

    This is one of the two load-bearing order-sensitivity tests for SC #3
    (the other is test_empty_content_non_guardrail_raises_schema_error below).
    """
    client = get_llm("anthropic_mgti")
    resp = _make_anthropic_response(text="", stop_reason="guardrail_intervened")
    with patch("requests.post", return_value=resp):
        with pytest.raises(LLMGuardrailError) as exc_info:
            client.complete([{"role": "user", "content": "x"}])
    assert exc_info.value.provider == "anthropic_mgti"


def test_empty_content_non_guardrail_raises_schema_error(anthropic_env):
    """SC #3: HTTP 200 + empty content[] + stop_reason != 'guardrail_intervened'
    raises LLMSchemaError. 'HTTP 200 + empty content does NOT count as success'.

    Companion test to test_guardrail_intervened_raises_guardrail_error: the
    pair proves the order is correct (guardrail check fires LLMGuardrailError;
    empty-content-non-guardrail check fires LLMSchemaError). If the adapter
    reordered the checks, this test would still pass but the guardrail test
    above would fail — both must be green.
    """
    client = get_llm("anthropic_mgti")
    resp = _make_anthropic_response(text="", stop_reason="end_turn")
    with patch("requests.post", return_value=resp):
        with pytest.raises(LLMSchemaError) as exc_info:
            client.complete([{"role": "user", "content": "x"}])
    assert "empty content" in str(exc_info.value).lower() or "does NOT count as success" in str(exc_info.value)


# ===========================================================================
# SC #4 — .env.example lists every new Anthropic variable with documented defaults.
# ===========================================================================

def test_env_example_has_all_9_anthropic_vars():
    """SC #4: .env.example contains all 9 Phase 3 vars as NAME=value with
    non-empty defaults.
    """
    # Locate .env.example at project root (this file is in tests/)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(repo_root, ".env.example")
    assert os.path.exists(env_path), f"{env_path} not found"

    content = open(env_path).read()
    required = [
        "LLM_PROVIDER_DEFAULT",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_VERSION",
        "ANTHROPIC_MAX_TOKENS",
        "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_TIMEOUT_S",
        "ANTHROPIC_TOOLS_SUPPORTED",
    ]
    for var in required:
        assert f"{var}=" in content, f"MISSING: {var}= not found in .env.example"

    # Each var must have a non-empty value after the =
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name in required:
            assert len(value) > 0, f"{name} has empty value in .env.example: {line!r}"


# ===========================================================================
# SC #5 — Startup log per loadable provider; no tool wrapping at call sites.
# ===========================================================================

class _RecordCapturer(logging.Handler):
    """Capture log records for the test's lifetime."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_startup_log_anthropic_provider(anthropic_env):
    """SC #5: constructing get_llm('anthropic_mgti') emits exactly one
    'llm_provider_loaded' log event with provider+base_url extras.
    """
    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
    try:
        get_llm("anthropic_mgti")
    finally:
        snow_logger.removeHandler(cap)

    events = [r for r in cap.records if r.getMessage() == "llm_provider_loaded"]
    assert len(events) == 1, (
        f"expected 1 llm_provider_loaded event for anthropic_mgti, got {len(events)}"
    )
    ev = events[0]
    assert ev.provider == "anthropic_mgti"
    assert ev.base_url == _BASE_URL


def test_startup_log_azure_provider(monkeypatch):
    """SC #5: 'for each loadable provider' — Azure also logs llm_provider_loaded.

    Phase 3 Plan 01 added the matching llm_provider_loaded call to
    AzureOpenAIClient.__init__ for symmetry. The factory-cache idempotence
    test below covers the 'exactly once' clause.
    """
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", _AZURE_ENDPOINT)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", _AZURE_KEY)

    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
    try:
        get_llm("azure_openai")
    finally:
        snow_logger.removeHandler(cap)

    events = [r for r in cap.records if r.getMessage() == "llm_provider_loaded"]
    assert len(events) == 1, (
        f"expected 1 llm_provider_loaded event for azure_openai, got {len(events)}"
    )
    ev = events[0]
    assert ev.provider == "azure_openai"
    assert ev.base_url == _AZURE_ENDPOINT


def test_factory_cache_dedupes_startup_log(anthropic_env):
    """SC #5 'exactly once': calling get_llm('anthropic_mgti') twice still
    produces exactly ONE llm_provider_loaded event because the factory cache
    returns the same instance on the second call (no second __init__ run).
    """
    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
    try:
        c1 = get_llm("anthropic_mgti")
        c2 = get_llm("anthropic_mgti")
    finally:
        snow_logger.removeHandler(cap)

    assert c1 is c2, "factory cache not idempotent (different instances)"
    events = [r for r in cap.records if r.getMessage() == "llm_provider_loaded"]
    assert len(events) == 1, (
        f"factory cache should dedupe to 1 event for 2 get_llm() calls, got {len(events)}"
    )


def test_no_tool_wrapping_in_call_sites():
    """SC #5: generate_sql and generate_executive_summary call ONLY complete()
    on whichever provider is active — no tool-use wrapping on either side.

    Same pattern as Phase 2's test_call_azure_openai_eliminated: inspect the
    function source and assert classify_with_tool does NOT appear.
    """
    from src.query_router import generate_executive_summary
    from src.sql_generator import generate_sql

    for fn in (generate_sql, generate_executive_summary):
        src = inspect.getsource(fn)
        assert "classify_with_tool" not in src, (
            f"{fn.__name__} contains classify_with_tool — Phase 3 SC #5 forbids "
            f"tool wrapping at this call site"
        )
        # Belt and suspenders: the call site MUST use complete() directly
        assert "complete(" in src, (
            f"{fn.__name__} does not call complete() — call-site wiring regressed"
        )


# ===========================================================================
# COMPAT-DISPATCH group — proves Plan 02's per-provider QueryError dispatch
# end-to-end through the llm_to_query_error() context manager. This is the
# user-visible "Anthropic API key not configured..." wording — without it,
# Phase 5's UI would still show "Azure OpenAI API call failed" on Anthropic
# auth errors.
# ===========================================================================

def test_anthropic_auth_error_translates_to_anthropic_query_error():
    """COMPAT-DISPATCH: LLMAuthError(provider='anthropic_mgti') → QueryError
    with Anthropic-named message + remediation. Exercises Plan 02's dispatch.
    """
    with pytest.raises(QueryError) as exc_info:
        with llm_to_query_error():
            raise LLMAuthError("HTTP 401", provider="anthropic_mgti", status_code=401)

    assert exc_info.value.message == "Anthropic API key not configured or not authorised", (
        f"Anthropic auth-error message wrong: {exc_info.value.message!r}"
    )
    assert exc_info.value.details == (
        "Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env."
    ), f"Anthropic auth-error details wrong: {exc_info.value.details!r}"


def test_anthropic_timeout_translates_to_anthropic_query_error():
    """COMPAT-DISPATCH: LLMTimeoutError(provider='anthropic_mgti') → QueryError
    with 'Anthropic API call failed' (NOT 'Azure OpenAI API call failed').

    Locks out the Phase 2 known-debt regression path where an Anthropic
    timeout would have surfaced as 'Azure OpenAI API call failed' in the UI.
    """
    with pytest.raises(QueryError) as exc_info:
        with llm_to_query_error():
            raise LLMTimeoutError("timed out after 30s", provider="anthropic_mgti")

    assert exc_info.value.message == "Anthropic API call failed", (
        f"Anthropic timeout message wrong: {exc_info.value.message!r} "
        f"(if this says 'Azure OpenAI API call failed', Plan 02 dispatch regressed)"
    )
    assert "timed out after 30s" in (exc_info.value.details or ""), (
        f"timeout details lost: {exc_info.value.details!r}"
    )
```

Notes on the test design:

- **`_RecordCapturer` is a class-level helper** (defined once near the SC #5 group) rather than a fixture. It adds a fresh handler in each test and removes it in `finally` — does NOT mutate the global logger's level or formatters.
- **`test_init_no_raise_on_empty_model` is the SC #2 BOUNDARY test** — empty model must NOT raise at construction; the no-op pattern from Phase 1 must be preserved. If this test fails, the `if self._model and ...` guard in `AnthropicMGTIClient.__init__` regressed.
- **`test_guardrail_intervened_raises_guardrail_error` and `test_empty_content_non_guardrail_raises_schema_error` are a PAIR** — together they prove the order-sensitive guardrail-before-emptiness check is correct. If only the second one passes (and the first fails), the order is reversed and the adapter raises LLMSchemaError on guardrail responses. This is the RESEARCH.md Pitfall 4 regression guard.
- **`test_startup_log_azure_provider`** depends on Plan 01 having added the matching `llm_provider_loaded` call to `AzureOpenAIClient.__init__`. If Plan 01 didn't ship, this test fails — directly indicating Plan 01 regression.
- **`test_factory_cache_dedupes_startup_log`** is the "exactly once per loadable provider" half of SC #5 — calling get_llm twice produces ONE log event because cache returns the same instance.
- **`test_no_tool_wrapping_in_call_sites`** uses `inspect.getsource` (same pattern as Phase 2's `test_call_azure_openai_eliminated`). It does NOT actually call the call sites — just confirms they don't use `classify_with_tool`. Since Phase 2 already made these call sites use `complete()` only, this test passes today; it's a regression guard for any future plan that might add tool wrapping at the wrong layer.
- **COMPAT-DISPATCH group** exercises Plan 02 end-to-end. Two tests is sufficient (one auth, one timeout) — Plan 02's own task verification covered the full dispatch table. These two tests are the user-facing proof that the Plan 02 + Plan 03 wiring lands the right product label in the UI.

DO NOT add a conftest.py or pytest.ini — this single file is self-contained, matching the Phase 1 and Phase 2 acceptance-gate pattern.
  </action>
  <verify>
Run from project root:

```
# 1. Phase 3 acceptance gate runs and all 21 tests pass
python -m pytest tests/test_phase3_adapter.py -v
```

Expected output (21 tests, all PASS):

```
tests/test_phase3_adapter.py::test_url_construction PASSED
tests/test_phase3_adapter.py::test_required_headers_present PASSED
tests/test_phase3_adapter.py::test_fresh_correlation_id_per_call PASSED
tests/test_phase3_adapter.py::test_init_raises_on_bad_model_prefix PASSED
tests/test_phase3_adapter.py::test_init_no_raise_on_empty_model PASSED
tests/test_phase3_adapter.py::test_opus_4_7_omits_sampling_params PASSED
tests/test_phase3_adapter.py::test_non_opus_includes_temperature PASSED
tests/test_phase3_adapter.py::test_http_401_raises_auth_error PASSED
tests/test_phase3_adapter.py::test_http_403_raises_auth_error PASSED
tests/test_phase3_adapter.py::test_http_429_raises_transient_error PASSED
tests/test_phase3_adapter.py::test_http_503_raises_transient_error PASSED
tests/test_phase3_adapter.py::test_requests_timeout_raises_timeout_error PASSED
tests/test_phase3_adapter.py::test_guardrail_intervened_raises_guardrail_error PASSED
tests/test_phase3_adapter.py::test_empty_content_non_guardrail_raises_schema_error PASSED
tests/test_phase3_adapter.py::test_env_example_has_all_9_anthropic_vars PASSED
tests/test_phase3_adapter.py::test_startup_log_anthropic_provider PASSED
tests/test_phase3_adapter.py::test_startup_log_azure_provider PASSED
tests/test_phase3_adapter.py::test_factory_cache_dedupes_startup_log PASSED
tests/test_phase3_adapter.py::test_no_tool_wrapping_in_call_sites PASSED
tests/test_phase3_adapter.py::test_anthropic_auth_error_translates_to_anthropic_query_error PASSED
tests/test_phase3_adapter.py::test_anthropic_timeout_translates_to_anthropic_query_error PASSED

========== 21 passed in <X>s ==========
```

If any test fails, Phase 3 has a regression in the named area — the test name points at the SC.

```
# 2. CRITICAL: combined run — Phase 1 + Phase 2 + Phase 3 all green together
python -m pytest tests/ -v
```

Expected: 6 (Phase 1) + 12 (Phase 2) + 21 (Phase 3) = 39 tests passing.

The combined run is the user-facing "Phase 3 complete" signal. If Phase 1 or Phase 2 regressed in any prior plan, this is where it shows.
  </verify>
  <done>
- `tests/test_phase3_adapter.py` exists with 21 standalone test functions (no test classes — verify with `pytest --collect-only`).
- All 21 tests pass via `python -m pytest tests/test_phase3_adapter.py -v`.
- Each test docstring cites the Phase 3 SC (or COMPAT-DISPATCH purpose) it proves.
- All 5 Phase 3 ROADMAP SCs map to ≥1 passing test:
  - SC #1 → `test_url_construction`, `test_required_headers_present`, `test_fresh_correlation_id_per_call`
  - SC #2 → `test_init_raises_on_bad_model_prefix`, `test_init_no_raise_on_empty_model`, `test_opus_4_7_omits_sampling_params`, `test_non_opus_includes_temperature`
  - SC #3 → seven typed-error tests including the order-sensitive guardrail-before-emptiness pair
  - SC #4 → `test_env_example_has_all_9_anthropic_vars`
  - SC #5 → `test_startup_log_anthropic_provider`, `test_startup_log_azure_provider`, `test_factory_cache_dedupes_startup_log`, `test_no_tool_wrapping_in_call_sites`
- COMPAT-DISPATCH group proves Plan 02's per-provider QueryError dispatch end-to-end (Anthropic auth + Anthropic timeout) — without these, Phase 5's UI would still show "Azure OpenAI API call failed" on Anthropic errors.
- Phase 1 + Phase 2 + Phase 3 acceptance gates ALL green together: `pytest tests/` shows 39 tests passing.
- Test gate runs OFFLINE — zero live HTTP. All `requests.post` patched, all responses inline Python dicts (no fixture files).
- No `conftest.py` or `pytest.ini` added.
  </done>
</task>

</tasks>

<verification>
End-of-phase verification — this IS the Phase 3 acceptance gate:

```
# 1. Phase 3 acceptance gate — 21 tests, all green
python -m pytest tests/test_phase3_adapter.py -v

# 2. Phase 1 + Phase 2 acceptance gates still green
python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v

# 3. Combined — all 39 tests across the three phases passing together
python -m pytest tests/ -v
```

The third command MUST show 39 passing (6 + 12 + 21). If any test fails, Phase 3 is NOT complete.

Cross-cutting checks verifying each SC from a different angle:

```
# SC #1: URL/headers signals in adapter source
grep -n "X-Correlation-Id\|X-Api-Key\|/messages" src/llm/anthropic_mgti.py

# SC #2: model validation + opus sampling-param omission
grep -n "eu.anthropic.claude-" src/llm/anthropic_mgti.py
grep -n "eu.anthropic.claude-opus-4-7" src/llm/anthropic_mgti.py

# SC #3: all six typed-error raises present
grep -cE "raise LLM(Config|Auth|Transient|Timeout|Guardrail|Schema)Error" src/llm/anthropic_mgti.py
# Expected: at least 6 (one per error class — LLMConfigError appears multiple times for pre-flight + init validation)

# SC #4: env.example has all 9 vars
python -c "
content = open('.env.example').read()
for v in ('LLM_PROVIDER_DEFAULT','ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_MODEL','ANTHROPIC_VERSION','ANTHROPIC_MAX_TOKENS','ANTHROPIC_TEMPERATURE','ANTHROPIC_TIMEOUT_S','ANTHROPIC_TOOLS_SUPPORTED'):
    assert f'{v}=' in content
print('all 9 vars present')
"

# SC #5: llm_provider_loaded emitted in BOTH adapter __init__ methods
grep -n "llm_provider_loaded" src/llm/anthropic_mgti.py
grep -n "llm_provider_loaded" src/llm/azure_openai.py
```

LOCKED files NOT modified by this plan (Plan 04 surface is test-only):
```
git diff --name-only HEAD src/ app.py config.py .env.example 2>&1 | head
```

Must produce no output (this plan touches ONLY `tests/test_phase3_adapter.py`).

NOTE: The grep cross-check `grep -cE "raise LLM(Config|Auth|...)Error"` returning "at least 6" is approximate — `LLMConfigError` appears 4 times (one __init__ validation + three pre-flight checks for missing key/url/model), `LLMAuthError`/`LLMTransientError`/`LLMTimeoutError`/`LLMGuardrailError`/`LLMSchemaError` each appear ≥1 time. Total raises in `src/llm/anthropic_mgti.py` should be ~10-12 across all error paths.
</verification>

<success_criteria>
- `tests/test_phase3_adapter.py` exists and `python -m pytest tests/test_phase3_adapter.py -v` exits 0 with 21/21 passing.
- All 5 Phase 3 ROADMAP success criteria from ROADMAP.md proven by ≥1 executable test:
  - SC #1 (URL + headers + fresh UUID) → 3 tests
  - SC #2 (model validation + opus sampling-param omission + non-opus temperature) → 4 tests
  - SC #3 (typed-error mapping including the guardrail-before-emptiness order) → 7 tests
  - SC #4 (`.env.example` has all 9 vars) → 1 test
  - SC #5 (startup log per provider + factory cache dedupe + no tool wrapping) → 4 tests
  - Plus COMPAT-DISPATCH (Plan 02 dispatch verified end-to-end) → 2 tests
- Phase 1 + Phase 2 + Phase 3 acceptance gates ALL green together: `pytest tests/` shows 39 tests passing.
- Test gate runs OFFLINE — zero live HTTP. All `requests.post` patched, all responses inline Python dicts.
- LOCKED files (everything except `tests/test_phase3_adapter.py`) NOT modified.

Maps to: All 5 Phase 3 ROADMAP success criteria (executable verification). Requirements verified: ADP-03, ADP-04, ADP-05, ADP-06, ADP-08, ERR-02, ERR-03, CFG-02, CFG-04, OBS-01, OBS-04, TOOL-07 (stub-preserved check via `test_no_tool_wrapping_in_call_sites` reading the call-site sources).
</success_criteria>

<output>
After completion, create `.planning/phases/03-anthropic-mgti-adapter/03-04-SUMMARY.md` documenting:
- pytest command + exit code + per-test pass/fail for `tests/test_phase3_adapter.py` (21 tests expected).
- pytest command + exit code for `tests/test_llm_seam.py` (6 tests, must still be green) and `tests/test_phase2_parity.py` (12 tests, must still be green).
- Combined `pytest tests/` showing 39 tests passing.
- Confirmation that the 5 ROADMAP Phase 3 success criteria each map to a passing test (table form: criterion → test function names).
- Confirmation that the test suite runs offline (no live HTTP, all `requests.post` patched).
- Confirmation that this plan modified ONLY `tests/test_phase3_adapter.py` — paste `git diff --name-only HEAD` output (relative to the start of this plan; sibling plans 01-03 will already be in HEAD).
- Phase 3 sign-off paragraph: "Phase 3 (Anthropic MGTI Adapter) is complete. The acceptance gate is green — Anthropic adapter is wired against the MGTI Apigee proxy with full typed-error mapping, structured logging, and per-provider QueryError dispatch. The adapter is reachable via `get_llm('anthropic_mgti')` but no UI exposes it yet — Phase 5 owns the sidebar toggle. Phase 4 (Strict-Tools + Smoke Test) is unblocked."
</output>
