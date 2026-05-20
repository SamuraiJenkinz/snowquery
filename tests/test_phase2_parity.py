"""Phase 2 acceptance gate: prove all four Phase 2 success criteria.

Each test function maps to one numbered success criterion from
.planning/phases/02-azure-extraction-parity-gate/ROADMAP.md success_criteria.

This module deliberately uses ZERO live external dependencies:
  - HTTP is mocked via unittest.mock.patch('requests.post', ...)
  - Five JSON fixtures in tests/fixtures/parity/ supply the response shapes
  - The factory cache is cleared between tests so adapter re-init is unambiguous

A green pytest run on this file IS the Phase 2 gate.

Run with: `pytest tests/test_phase2_parity.py -v`
"""
from __future__ import annotations

import inspect
import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.llm.azure_openai import AzureOpenAIClient
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.utils import QueryError, logger as snow_logger

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parity"

# Dummy but URL-shaped values so AzureOpenAIClient.__init__ can extract a model
# name and complete() passes the pre-flight config check.
_DUMMY_ENDPOINT = "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"
_DUMMY_KEY = "test-key-not-real"


# ---------------------------------------------------------------------------
# Autouse fixtures — same pattern as tests/test_llm_seam.py (Phase 1).
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Ensure each test sees an empty get_llm cache (the module-level _cache
    dict in src/llm/__init__.py persists across tests in one pytest process)."""
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()


@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch):
    """Strip all LLM-related env vars so tests start from a clean slate."""
    for name in (
        "LLM_PROVIDER_DEFAULT",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "API_VERSION",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def azure_env(monkeypatch):
    """Set realistic Azure env so AzureOpenAIClient can construct without
    LLMConfigError. Tests that exercise the pre-flight config path do NOT
    request this fixture."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", _DUMMY_ENDPOINT)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", _DUMMY_KEY)


def _load_fixture(name: str) -> dict:
    with open(FIXTURE_DIR / name) as f:
        return json.load(f)


def _make_mock_response(fixture: dict) -> MagicMock:
    """Build a MagicMock that imitates a successful Azure HTTP response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = lambda: None
    resp.json.return_value = fixture["response_json"]
    return resp


# ---------------------------------------------------------------------------
# Success criterion #1 — _call_azure_openai is GONE; DI at all 3 call sites.
# ABS-06.
# ---------------------------------------------------------------------------

def test_call_azure_openai_eliminated():
    """Success criterion #1: grep returns zero hits; DI at all three sites."""
    # Source-level grep equivalent: neither file contains the literal name.
    for module_name in ("src.query_router", "src.sql_generator"):
        mod = __import__(module_name, fromlist=["*"])
        src = inspect.getsource(mod)
        assert "_call_azure_openai" not in src, (
            f"{module_name} still references _call_azure_openai"
        )

    # DI shape: each of the three call sites uses get_llm() + llm_to_query_error().
    import src.query_router as qr
    import src.sql_generator as sg
    for fn, expected_max_tokens in [
        (qr.classify_intent, "max_tokens=500"),
        (qr.generate_executive_summary, "max_tokens=500"),
        (sg.generate_sql, "max_tokens=1000"),
    ]:
        src = inspect.getsource(fn)
        assert "get_llm()" in src, f"{fn.__name__} missing get_llm()"
        assert "llm_to_query_error()" in src, f"{fn.__name__} missing llm_to_query_error()"
        assert expected_max_tokens in src, (
            f"{fn.__name__} missing {expected_max_tokens} — load-bearing diff regressed!"
        )


# ---------------------------------------------------------------------------
# Success criterion #2 — Five-fixture parity gate. THE HEADLINE.
# ADP-01.
# ---------------------------------------------------------------------------

def _assert_adapter_returns_fixture_content(fixture_file: str, max_tokens: int, azure_env):
    """Shared assertion: real adapter + mocked requests.post → byte-identical content."""
    fixture = _load_fixture(fixture_file)
    expected = fixture["response_json"]["choices"][0]["message"]["content"]
    mock_resp = _make_mock_response(fixture)

    client = get_llm()  # real AzureOpenAIClient via the factory
    assert isinstance(client, AzureOpenAIClient)

    with patch("requests.post", return_value=mock_resp):
        out = client.complete(
            fixture["request_messages"], max_tokens=max_tokens
        )

    # CORE PARITY ASSERTION: adapter returns content verbatim (no .strip(), no
    # transformation). The .strip() happens at the call site, not here.
    assert out == expected, (
        f"PARITY FAILURE for {fixture_file}: "
        f"adapter returned {out!r}, expected {expected!r}"
    )


def test_parity_q1_structured(azure_env):
    """Success criterion #2 — Q1 (structured-count classification, CS1, max_tokens=500)."""
    _assert_adapter_returns_fixture_content(
        "q1_structured_classification.json", 500, azure_env
    )


def test_parity_q2_semantic(azure_env):
    """Success criterion #2 — Q2 (semantic-similar classification, CS1, max_tokens=500)."""
    _assert_adapter_returns_fixture_content(
        "q2_semantic_classification.json", 500, azure_env
    )


def test_parity_q3_hybrid(azure_env):
    """Success criterion #2 — Q3 (hybrid-filter classification, CS1, max_tokens=500)."""
    _assert_adapter_returns_fixture_content(
        "q3_hybrid_classification.json", 500, azure_env
    )


def test_parity_q4_sql_generation(azure_env):
    """Success criterion #2 — Q4 (SQL generation, CS2, max_tokens=1000).

    This is the load-bearing test for the only behavioral difference between
    the two old _call_azure_openai duplicates: max_tokens=1000 (not 500).
    """
    fixture = _load_fixture("q4_sql_generation.json")
    expected = fixture["response_json"]["choices"][0]["message"]["content"]
    mock_resp = _make_mock_response(fixture)

    client = get_llm()
    with patch("requests.post", return_value=mock_resp) as mp:
        out = client.complete(fixture["request_messages"], max_tokens=1000)

    assert out == expected

    # Also assert the request body actually carried max_tokens=1000.
    call_kwargs = mp.call_args.kwargs
    assert call_kwargs["json"]["max_tokens"] == 1000, (
        f"max_tokens=1000 not in request body: {call_kwargs['json']}"
    )


def test_parity_q5_exec_summary(azure_env):
    """Success criterion #2 — Q5 (executive summary, CS3, max_tokens=500, free text)."""
    _assert_adapter_returns_fixture_content(
        "q5_exec_summary.json", 500, azure_env
    )


def test_parity_end_to_end_classify_intent(azure_env):
    """Success criterion #2 — end-to-end CS1 parity through classify_intent.

    Exercises the full call-site path: mocked requests.post →
    AzureOpenAIClient.complete → llm_to_query_error context manager →
    classify_intent's JSON parse → returned dict. Proves the .strip() + JSON
    parse downstream still works the same as before.
    """
    from src.query_router import classify_intent

    fixture = _load_fixture("q1_structured_classification.json")
    mock_resp = _make_mock_response(fixture)
    schema = {
        "table_name": "incidents",
        "row_count": 10,
        "columns": [{"name": "priority", "type": "VARCHAR", "sample": "P1"}],
    }
    with patch("requests.post", return_value=mock_resp):
        result = classify_intent("How many P1 incidents were opened this week?", schema)

    assert result["intent"] == "structured"
    assert result["confidence"] == 0.95
    assert result["detected_filters"]["priority"] == ["P1"]
    # chart_requested is heuristic-merged at the call site (TOOL-03 prep)
    assert "chart_requested" in result
    assert "chart_type" in result


def test_parity_end_to_end_generate_sql(azure_env):
    """Success criterion #2 — end-to-end CS2 parity through generate_sql.

    Exercises the full Q4 call-site path: mocked requests.post →
    AzureOpenAIClient.complete (max_tokens=1000) → llm_to_query_error context
    manager → generate_sql's .strip() + JSON parse + dangerous-keyword check →
    returned dict. Proves that after extraction the SQL string the user gets
    back is byte-identical to what the fixture contains. The adapter-direct
    parity tests above do NOT cover this — the .strip() and downstream JSON
    parse live at the CALL SITE, not in the adapter (RESEARCH.md Pitfall 1).
    """
    from src.sql_generator import generate_sql

    fixture = _load_fixture("q4_sql_generation.json")
    fixture_content = fixture["response_json"]["choices"][0]["message"]["content"]
    expected_parsed = json.loads(fixture_content)  # the call site JSON-parses
    mock_resp = _make_mock_response(fixture)
    schema = {
        "table_name": "incidents",
        "row_count": 10,
        "columns": [
            {"name": "assignment_group", "type": "VARCHAR", "sample": "Network Ops"},
        ],
    }
    with patch("requests.post", return_value=mock_resp) as mp:
        result = generate_sql("Top 5 assignment groups by incident count", schema)

    # The returned dict carries the SQL string verbatim from the fixture
    # (post-strip-and-JSON-parse). This is the call-site-level "byte-identical"
    # contract that success criterion #2 actually requires.
    assert result["sql"] == expected_parsed["sql"]
    assert result["explanation"] == expected_parsed["explanation"]
    assert result["confidence"] == expected_parsed["confidence"]

    # Belt-and-suspenders: max_tokens=1000 reached the request body (load-bearing
    # diff between CS1 and CS2).
    call_kwargs = mp.call_args.kwargs
    assert call_kwargs["json"]["max_tokens"] == 1000


def test_parity_end_to_end_exec_summary(azure_env):
    """Success criterion #2 — end-to-end CS3 parity through generate_executive_summary.

    Exercises the full Q5 call-site path: mocked requests.post →
    AzureOpenAIClient.complete → llm_to_query_error context manager →
    generate_executive_summary's .strip() → returned string. CS3 is the only
    free-text (non-JSON) call site, so the proof is that the call site returns
    fixture_content.strip() verbatim. The adapter-direct test does not cover
    the call-site .strip() (RESEARCH.md Pitfall 1).
    """
    import pandas as pd
    from src.query_router import generate_executive_summary

    fixture = _load_fixture("q5_exec_summary.json")
    fixture_content = fixture["response_json"]["choices"][0]["message"]["content"]
    mock_resp = _make_mock_response(fixture)
    df = pd.DataFrame({"id": [1, 2, 3], "priority": ["P1", "P1", "P2"]})

    with patch("requests.post", return_value=mock_resp):
        result = generate_executive_summary(
            "What are the top incidents?", df, "structured"
        )

    # Byte-identical to fixture_content.strip() — proves the call-site .strip()
    # still runs after extraction (the adapter does NOT strip).
    assert result == fixture_content.strip()


# ---------------------------------------------------------------------------
# Success criterion #3 — LLMError subclasses translate to QueryError at the
# call-site boundary via llm_to_query_error(). Preserves the user-visible
# error contract (historic remediation text on auth failures).
# ERR-04.
# ---------------------------------------------------------------------------

def test_error_translation_at_call_site(monkeypatch):
    """Success criterion #3: every LLMError subclass surfaces as QueryError.

    Patches the factory cache to inject a stub adapter that raises a chosen
    LLMError subclass, then calls classify_intent and asserts QueryError
    surfaces with the historic message/details text.
    """
    import src.llm as llm_pkg
    from src.query_router import classify_intent
    from src.sql_generator import generate_sql

    schema = {
        "table_name": "incidents",
        "row_count": 10,
        "columns": [{"name": "priority", "type": "VARCHAR", "sample": "P1"}],
    }

    def _install_raising_client(exc: Exception):
        """Replace the cached azure_openai client with one whose .complete raises."""
        fake = MagicMock(spec=AzureOpenAIClient)
        fake.complete.side_effect = exc
        llm_pkg._cache["azure_openai"] = fake

    # --- LLMTimeoutError → QueryError("Azure OpenAI API call failed", ...) ---
    llm_pkg._cache.clear()
    _install_raising_client(LLMTimeoutError("timed out after 30s", provider="azure_openai"))
    with pytest.raises(QueryError) as exc_info:
        # classify_intent has `except QueryError: raise` BEFORE the broad
        # `except Exception` fallback — QueryError must propagate, NOT fall
        # through to the heuristic fallback (RESEARCH.md Risk 5).
        classify_intent("test query", schema)
    assert exc_info.value.message == "Azure OpenAI API call failed"
    assert "timed out" in (exc_info.value.details or "")

    # --- LLMTransientError → same first-arg ---
    llm_pkg._cache.clear()
    _install_raising_client(
        LLMTransientError("HTTP 503", provider="azure_openai", status_code=503)
    )
    with pytest.raises(QueryError) as exc_info:
        classify_intent("test", schema)
    assert exc_info.value.message == "Azure OpenAI API call failed"

    # --- LLMAuthError → historic Azure key-not-configured remediation text ---
    llm_pkg._cache.clear()
    _install_raising_client(
        LLMAuthError("HTTP 401", provider="azure_openai", status_code=401)
    )
    with pytest.raises(QueryError) as exc_info:
        classify_intent("test", schema)
    assert exc_info.value.message == "Azure OpenAI API key not configured"
    assert exc_info.value.details == (
        "Set the AZURE_OPENAI_API_KEY environment variable."
    )

    # --- LLMConfigError → adapter-embedded remediation passed through ---
    llm_pkg._cache.clear()
    _install_raising_client(
        LLMConfigError(
            "Azure OpenAI API key not configured. "
            "Set the AZURE_OPENAI_API_KEY environment variable.",
            provider="azure_openai",
        )
    )
    with pytest.raises(QueryError) as exc_info:
        classify_intent("test", schema)
    assert "AZURE_OPENAI_API_KEY" in exc_info.value.message
    assert exc_info.value.details == "Check your .env configuration."

    # --- Same exception types must translate at CS2 (generate_sql) too ---
    # CS2's exception-handler structure differs from CS1: it has
    # `except QueryError: raise` followed by a broad `except Exception as e:
    # raise QueryError("Failed to generate SQL", ...)`. If a regression in the
    # compat-layer catch order ever lets an LLMError leak past
    # llm_to_query_error(), it would be caught by the broad-except and the
    # user would see "Failed to generate SQL" instead of the required
    # "Azure OpenAI API call failed". We assert BOTH LLMTimeoutError AND
    # LLMTransientError at CS2 to lock that down.
    llm_pkg._cache.clear()
    _install_raising_client(LLMTimeoutError("timeout", provider="azure_openai"))
    with pytest.raises(QueryError) as exc_info:
        generate_sql("test", schema)
    assert exc_info.value.message == "Azure OpenAI API call failed", (
        f"CS2 LLMTimeoutError leaked past compat manager — got "
        f"{exc_info.value.message!r}, expected 'Azure OpenAI API call failed'"
    )

    llm_pkg._cache.clear()
    _install_raising_client(
        LLMTransientError("HTTP 503", provider="azure_openai", status_code=503)
    )
    with pytest.raises(QueryError) as exc_info:
        generate_sql("test", schema)
    assert exc_info.value.message == "Azure OpenAI API call failed", (
        f"CS2 LLMTransientError leaked past compat manager into the broad "
        f"except — got {exc_info.value.message!r}, expected "
        f"'Azure OpenAI API call failed' (NOT 'Failed to generate SQL')"
    )

    # --- CS3 (generate_executive_summary) silently swallows the error and
    # returns None — this is INTENTIONAL behavior preserved from the old code
    # (RESEARCH.md Pitfall 4). Both old and new behave the same way here.
    import pandas as pd
    from src.query_router import generate_executive_summary
    llm_pkg._cache.clear()
    _install_raising_client(LLMTimeoutError("timeout", provider="azure_openai"))
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = generate_executive_summary("test", df, "structured")
    assert result is None, (
        "generate_executive_summary should silently return None on LLM error "
        "— this preserves byte-identical behavior vs the old _call_azure_openai path"
    )


# ---------------------------------------------------------------------------
# Success criterion #4 — one structured log event per complete() call with
# the full extra-field shape.
# OBS-02.
# ---------------------------------------------------------------------------

class _RecordCapturer(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_log_event_shape(azure_env):
    """Success criterion #4: one llm_call event per complete() call with all
    OBS-02 fields present (provider, model, latency_ms, outcome, error_type,
    prompt_tokens, completion_tokens, correlation_id).
    """
    fixture = _load_fixture("q1_structured_classification.json")
    mock_resp = _make_mock_response(fixture)

    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
    try:
        client = get_llm()
        with patch("requests.post", return_value=mock_resp):
            client.complete(fixture["request_messages"], max_tokens=500)
    finally:
        snow_logger.removeHandler(cap)

    llm_events = [r for r in cap.records if r.getMessage() == "llm_call"]
    assert len(llm_events) == 1, (
        f"expected exactly 1 llm_call event, got {len(llm_events)}: "
        f"{[(r.getMessage(), getattr(r, 'llm_outcome', None)) for r in cap.records]}"
    )

    ev = llm_events[0]
    # All required OBS-02 fields present with correct types/values.
    assert ev.llm_provider == "azure_openai"
    assert ev.llm_model == "gpt-4o-mini"  # parsed from _DUMMY_ENDPOINT
    assert ev.llm_outcome == "success"
    assert ev.llm_error_type is None  # only set on error path
    assert ev.llm_prompt_tokens == 312  # from fixture usage block
    assert ev.llm_completion_tokens == 52
    assert ev.llm_correlation_id is None  # Azure has no correlation ID in Phase 2
    assert isinstance(ev.llm_latency_ms, int)
    assert ev.llm_latency_ms >= 0


def test_log_event_on_error_path(azure_env):
    """Success criterion #4 + ERR-02: error path ALSO emits exactly one
    llm_call event, with llm_outcome='error' and llm_error_type set."""
    cap = _RecordCapturer()
    snow_logger.addHandler(cap)
    try:
        client = get_llm()
        # Simulate a timeout (Timeout is a RequestException subclass)
        import requests
        with patch("requests.post", side_effect=requests.exceptions.Timeout("simulated")):
            with pytest.raises(LLMTimeoutError):
                client.complete(
                    [{"role": "user", "content": "x"}], max_tokens=500
                )
    finally:
        snow_logger.removeHandler(cap)

    llm_events = [r for r in cap.records if r.getMessage() == "llm_call"]
    assert len(llm_events) == 1
    ev = llm_events[0]
    assert ev.llm_outcome == "error"
    assert ev.llm_error_type == "LLMTimeoutError"
    assert ev.llm_prompt_tokens is None  # no response body on timeout
    assert ev.llm_completion_tokens is None
    assert isinstance(ev.llm_latency_ms, int)
