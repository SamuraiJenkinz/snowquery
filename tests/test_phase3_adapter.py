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
    """Ensure each test sees an empty get_llm cache.

    Phase 5 Plan 05-01 deleted the module-level _cache dict and replaced it
    with @_cache_resource on _get_llm_cached. The decorated function exposes
    .clear() in real Streamlit; in the no-Streamlit fallback the decorator
    is a pass-through and no .clear() exists — getattr-with-callable check
    handles both contexts.
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
