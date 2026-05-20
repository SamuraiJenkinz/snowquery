---
phase: 02-azure-extraction-parity-gate
plan: 04
type: execute
wave: 3
depends_on: ["02-01", "02-02", "02-03"]
files_modified:
  - tests/test_phase2_parity.py
  - tests/fixtures/parity/q1_structured_classification.json
  - tests/fixtures/parity/q2_semantic_classification.json
  - tests/fixtures/parity/q3_hybrid_classification.json
  - tests/fixtures/parity/q4_sql_generation.json
  - tests/fixtures/parity/q5_exec_summary.json
autonomous: true

must_haves:
  truths:
    - "tests/test_phase2_parity.py exists and contains the FIVE-FIXTURE PARITY TEST as the headline — five representative queries spanning structured/semantic/hybrid intents + SQL generation + executive-summary path each prove byte-identical adapter extraction vs the fixture content (success criterion #2 — THE Phase 2 gate); the chain is ALSO proven end-to-end through each call site (`test_parity_end_to_end_classify_intent` / `_generate_sql` / `_exec_summary`) so the call-site `.strip()` + downstream JSON parse are part of the parity assertion (RESEARCH.md Pitfall 1)"
    - "Test proves success criterion #1 by grep-asserting `_call_azure_openai` absent from src/query_router.py and src/sql_generator.py"
    - "Test proves success criterion #3 by mocking the adapter to raise LLMTimeoutError, LLMTransientError, LLMAuthError, LLMConfigError at CS1 (classify_intent) — and BOTH LLMTimeoutError + LLMTransientError at CS2 (generate_sql) — asserting each surfaces at the call-site boundary as QueryError with the historic message/details text; the CS2 LLMTransientError assertion specifically locks out the regression path where a compat-layer catch-order break would let the error fall into CS2's broad `except Exception` and produce 'Failed to generate SQL' instead of 'Azure OpenAI API call failed'"
    - "Test proves success criterion #4 by capturing the logger.info('llm_call', extra={...}) record and asserting all required fields (llm_provider, llm_model, llm_latency_ms, llm_outcome, llm_prompt_tokens, llm_completion_tokens, llm_correlation_id) are present with correct types"
    - "Test runs offline — no live Azure HTTP call. All HTTP is mocked via unittest.mock.patch('requests.post', return_value=fixture_mock_response) per RESEARCH.md Decision 1"
    - "Test uses the same _clear_factory_cache + _strip_llm_env autouse fixture pattern established by tests/test_llm_seam.py for Phase 1 — load-bearing for module-level singleton isolation"
    - "Phase 1 acceptance gate (tests/test_llm_seam.py) still runs green alongside Phase 2 — both test modules pass in the same pytest invocation"
  artifacts:
    - path: "tests/test_phase2_parity.py"
      provides: "Pytest module proving all 4 Phase 2 success criteria; the five-fixture parity test + three call-site end-to-end tests are the headline."
      min_lines: 250
      exports: ["test_call_azure_openai_eliminated", "test_parity_q1_structured", "test_parity_q2_semantic", "test_parity_q3_hybrid", "test_parity_q4_sql_generation", "test_parity_q5_exec_summary", "test_parity_end_to_end_classify_intent", "test_parity_end_to_end_generate_sql", "test_parity_end_to_end_exec_summary", "test_error_translation_at_call_site", "test_log_event_shape", "test_log_event_on_error_path"]
    - path: "tests/fixtures/parity/q1_structured_classification.json"
      provides: "Synthetic Azure response for the structured-count classification query (CS1, max_tokens=500)"
      contains: "structured"
    - path: "tests/fixtures/parity/q2_semantic_classification.json"
      provides: "Synthetic Azure response for the semantic-similar classification query (CS1, max_tokens=500)"
      contains: "semantic"
    - path: "tests/fixtures/parity/q3_hybrid_classification.json"
      provides: "Synthetic Azure response for the hybrid-filter classification query (CS1, max_tokens=500)"
      contains: "hybrid"
    - path: "tests/fixtures/parity/q4_sql_generation.json"
      provides: "Synthetic Azure response for the SQL-generation query (CS2, max_tokens=1000)"
      contains: "SELECT"
    - path: "tests/fixtures/parity/q5_exec_summary.json"
      provides: "Synthetic Azure response for the executive-summary query (CS3, max_tokens=500)"
      contains: "summary"
  key_links:
    - from: "tests/test_phase2_parity.py"
      to: "src.llm.azure_openai.AzureOpenAIClient (real adapter)"
      via: "patch('requests.post', ...) — exercises the real adapter end-to-end against fixture responses"
      pattern: "patch\\(['\\\"]requests\\.post['\\\"]"
    - from: "tests/test_phase2_parity.py"
      to: "src.query_router.classify_intent + src.query_router.generate_executive_summary + src.sql_generator.generate_sql"
      via: "calls each call site with the corresponding fixture mocked at requests.post, asserts extracted content equals fixture content"
      pattern: "classify_intent|generate_sql|generate_executive_summary"
    - from: "tests/test_phase2_parity.py"
      to: "src.utils.logger"
      via: "adds a logging.Handler to capture llm_call records and assert the OBS-02 event shape"
      pattern: "logger\\.addHandler|llm_call"
---

<objective>
Build the Phase 2 acceptance gate — `tests/test_phase2_parity.py` — that proves all four Phase 2 success criteria with a single pytest run, no live HTTP, and the five-fixture parity test as the headline. Mirror the structure of Phase 1's `tests/test_llm_seam.py`: each test function maps to one numbered ROADMAP.md success criterion.

Purpose: A green pytest run on this module IS the Phase 2 gate. If any test fails, Phase 2 is not done and the failure points at exactly which success criterion regressed. This is the same acceptance-gate pattern Phase 1 used (`tests/test_llm_seam.py`) — researcher specifically called this out as the model to follow (CONTEXT.md, RESEARCH.md "Recommended Decisions" Decision 1).

Output: One pytest module (`tests/test_phase2_parity.py`) + five JSON fixture files in `tests/fixtures/parity/`. Total ~250-350 lines of test code + five small fixture files.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-azure-extraction-parity-gate/02-CONTEXT.md
@.planning/phases/02-azure-extraction-parity-gate/02-RESEARCH.md
@.planning/phases/02-azure-extraction-parity-gate/02-01-SUMMARY.md
@.planning/phases/02-azure-extraction-parity-gate/02-02-SUMMARY.md
@.planning/phases/02-azure-extraction-parity-gate/02-03-SUMMARY.md

# The seam this gate verifies
@src/llm/azure_openai.py
@src/llm/_compat.py
@src/query_router.py
@src/sql_generator.py

# The Phase 1 pattern this gate mirrors
@tests/test_llm_seam.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create the five parity fixtures in tests/fixtures/parity/</name>
  <files>tests/fixtures/parity/q1_structured_classification.json, tests/fixtures/parity/q2_semantic_classification.json, tests/fixtures/parity/q3_hybrid_classification.json, tests/fixtures/parity/q4_sql_generation.json, tests/fixtures/parity/q5_exec_summary.json</files>
  <action>
Create the directory `tests/fixtures/parity/` (and `tests/fixtures/` if missing) and write five JSON fixture files. Each fixture is a dict with TWO top-level keys:

- `"request_messages"`: the messages list that would be sent to Azure (documentation only — not asserted; helps a future reader understand which call site this fixture exercises)
- `"response_json"`: the full Azure OpenAI response body, complete enough that `response.raise_for_status()` is a no-op AND `response.json()["choices"][0]["message"]["content"]` yields the string the call site expects

Per RESEARCH.md OQ-3, fixtures are **hand-authored with realistic synthetic content** — no live Azure call required. The "byte-identical" contract is: given fixture content X, the new adapter returns X verbatim, which the call site then `.strip()`s and JSON-parses identically to today.

**Fixture 1 — `tests/fixtures/parity/q1_structured_classification.json`** (CS1 classify_intent, structured intent):

```json
{
  "request_messages": [
    {"role": "system", "content": "[CLASSIFICATION_PROMPT + schema text]"},
    {"role": "user", "content": "How many P1 incidents were opened this week?"}
  ],
  "response_json": {
    "choices": [
      {
        "message": {
          "content": "{\"intent\": \"structured\", \"confidence\": 0.95, \"reasoning\": \"Count aggregation query with priority and date-range filters\", \"detected_filters\": {\"priority\": [\"P1\"], \"assignment_group\": null, \"date_range\": \"this week\"}}"
        }
      }
    ],
    "usage": {
      "prompt_tokens": 312,
      "completion_tokens": 52,
      "total_tokens": 364
    }
  }
}
```

**Fixture 2 — `tests/fixtures/parity/q2_semantic_classification.json`** (CS1 classify_intent, semantic intent):

```json
{
  "request_messages": [
    {"role": "system", "content": "[CLASSIFICATION_PROMPT + schema text]"},
    {"role": "user", "content": "Find incidents similar to VPN connection failures"}
  ],
  "response_json": {
    "choices": [
      {
        "message": {
          "content": "{\"intent\": \"semantic\", \"confidence\": 0.92, \"reasoning\": \"Similarity search using descriptive phrasing\", \"detected_filters\": {\"priority\": null, \"assignment_group\": null, \"date_range\": null}}"
        }
      }
    ],
    "usage": {
      "prompt_tokens": 298,
      "completion_tokens": 44,
      "total_tokens": 342
    }
  }
}
```

**Fixture 3 — `tests/fixtures/parity/q3_hybrid_classification.json`** (CS1 classify_intent, hybrid intent):

```json
{
  "request_messages": [
    {"role": "system", "content": "[CLASSIFICATION_PROMPT + schema text]"},
    {"role": "user", "content": "P1 incidents similar to database outages"}
  ],
  "response_json": {
    "choices": [
      {
        "message": {
          "content": "{\"intent\": \"hybrid\", \"confidence\": 0.88, \"reasoning\": \"Structured priority filter combined with semantic similarity\", \"detected_filters\": {\"priority\": [\"P1\"], \"assignment_group\": null, \"date_range\": null}}"
        }
      }
    ],
    "usage": {
      "prompt_tokens": 305,
      "completion_tokens": 48,
      "total_tokens": 353
    }
  }
}
```

**Fixture 4 — `tests/fixtures/parity/q4_sql_generation.json`** (CS2 generate_sql, max_tokens=1000 — the load-bearing difference):

```json
{
  "request_messages": [
    {"role": "system", "content": "[SYSTEM_PROMPT + schema text]"},
    {"role": "user", "content": "Top 5 assignment groups by incident count"}
  ],
  "response_json": {
    "choices": [
      {
        "message": {
          "content": "{\"sql\": \"SELECT assignment_group, COUNT(*) as incident_count FROM incidents WHERE assignment_group IS NOT NULL GROUP BY assignment_group ORDER BY incident_count DESC LIMIT 5\", \"explanation\": \"Counts incidents per assignment group and returns the top 5.\", \"confidence\": 0.97}"
        }
      }
    ],
    "usage": {
      "prompt_tokens": 425,
      "completion_tokens": 78,
      "total_tokens": 503
    }
  }
}
```

**Fixture 5 — `tests/fixtures/parity/q5_exec_summary.json`** (CS3 generate_executive_summary, free-text output, not JSON):

```json
{
  "request_messages": [
    {"role": "system", "content": "[SUMMARY_PROMPT]"},
    {"role": "user", "content": "Question: What are the top incidents?\n\nQuery Type: structured\n\nResults (3 results):\n[short dataframe text]\n\nPlease provide an executive summary of these results."}
  ],
  "response_json": {
    "choices": [
      {
        "message": {
          "content": "The top three incidents are concentrated in the Network Operations group and were opened within the last 24 hours. Two are flagged as P1 priority and relate to VPN gateway failures; the third is a P2 user-impact issue. All three remain in the In Progress state with no resolution timestamp yet."
        }
      }
    ],
    "usage": {
      "prompt_tokens": 218,
      "completion_tokens": 65,
      "total_tokens": 283
    }
  }
}
```

Notes:
- All five fixtures have a `usage` block — the parity test will also assert that `_log_llm_call` extracts `prompt_tokens` and `completion_tokens` correctly.
- The `"content"` strings are deliberately well-formed for the call sites' JSON-parse paths (Q1-Q4) OR plain text (Q5). Q5 has no JSON parse, so its content is free-form English.
- Q3 has `priority: ["P1"]` AND `intent: "hybrid"` — both a filter AND a similarity request, matching the hybrid intent definition.
- Q4 uses a `SELECT` query with `LIMIT 5` — passes the dangerous-keyword check in `generate_sql` (lines 222-228 in current `sql_generator.py`).
- These fixtures are stable test data — if any post-Phase-2 refactor changes the call sites' downstream parsing, the parity test failure will pinpoint the regression.
  </action>
  <verify>
Run from project root:

```
python -c "
import json
import os

fixtures = [
    'q1_structured_classification.json',
    'q2_semantic_classification.json',
    'q3_hybrid_classification.json',
    'q4_sql_generation.json',
    'q5_exec_summary.json',
]
for name in fixtures:
    path = os.path.join('tests', 'fixtures', 'parity', name)
    assert os.path.exists(path), f'missing fixture: {path}'
    with open(path) as f:
        data = json.load(f)
    assert 'request_messages' in data, f'{name}: missing request_messages'
    assert 'response_json' in data, f'{name}: missing response_json'
    content = data['response_json']['choices'][0]['message']['content']
    assert isinstance(content, str) and len(content) > 0, f'{name}: empty content'
    # Q1-Q4 must be valid JSON in their content (since the call sites JSON-parse it)
    if name != 'q5_exec_summary.json':
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f'{name}: content is not valid JSON: {e}')
    print(f'{name}: OK ({len(content)} chars)')
print('all 5 fixtures OK')
"
```

Must print one `OK` line per fixture and end with `all 5 fixtures OK`.
  </verify>
  <done>
- `tests/fixtures/parity/` directory exists with five JSON files (q1 through q5).
- Each fixture has `request_messages` (documentation) and `response_json` (the mocked Azure body).
- Q1, Q2, Q3 have JSON-parseable content matching the CLASSIFICATION_PROMPT shape (`intent`/`confidence`/`reasoning`/`detected_filters`).
- Q4 has JSON-parseable content matching the SQL SYSTEM_PROMPT shape (`sql`/`explanation`/`confidence`) and the SQL passes the dangerous-keyword check (starts with `SELECT`, has a `LIMIT`).
- Q5 has free-text content matching the SUMMARY_PROMPT output shape (no JSON parse downstream).
- All five fixtures have a `usage` block with `prompt_tokens` and `completion_tokens` for OBS-02 log-field verification.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/test_phase2_parity.py — the Phase 2 acceptance gate</name>
  <files>tests/test_phase2_parity.py</files>
  <action>
Create `tests/test_phase2_parity.py`. The module has twelve test functions, organized by success criterion:

- Success criterion #1 (`_call_azure_openai` eliminated, DI at all 3 call sites) → `test_call_azure_openai_eliminated`
- Success criterion #2 (five-fixture parity gate — THE HEADLINE) → `test_parity_q1_structured` through `test_parity_q5_exec_summary` + three end-to-end tests through the call sites (`test_parity_end_to_end_classify_intent`, `test_parity_end_to_end_generate_sql`, `test_parity_end_to_end_exec_summary`) that prove the full chain including the call-site `.strip()` + downstream JSON parse
- Success criterion #3 (LLMError → QueryError at call-site boundary, all four LLMError subclasses; both CS1 and CS2 covered) → `test_error_translation_at_call_site`
- Success criterion #4 (one structured log event per call with the full extra-field shape) → `test_log_event_shape` + `test_log_event_on_error_path`

Use the SAME autouse-fixture pattern from `tests/test_llm_seam.py` — `_clear_factory_cache` (for the module-level `_cache` dict in `src/llm/__init__.py`) and `_strip_llm_env` (for env var isolation) — plus a new `_set_azure_env` fixture for the tests that need the adapter to construct without LLMConfigError.

Exact file contents:

```python
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
        # classify_intent has `except Exception: return _heuristic_classify(...)`
        # AFTER `except QueryError: raise` — QueryError must propagate, NOT
        # fall through to the heuristic fallback (RESEARCH.md Risk 5).
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
```

Notes on the test design:

- **`_RecordCapturer` adds a fresh handler** for each log test and removes it in `finally` — does NOT mutate the global logger's level or formatters. Phase 1's `tests/test_llm_seam.py` did not exercise log capture; this is a Phase 2 addition.
- **`test_error_translation_at_call_site` uses `_install_raising_client`** (the Level B pattern from RESEARCH.md "DI Pattern" section): patch the factory cache to inject a `MagicMock(spec=AzureOpenAIClient)` whose `.complete.side_effect` is the LLMError of interest. This isolates the call site's `llm_to_query_error()` behavior from the adapter's HTTP behavior.
- **`test_parity_*` uses Level A** (patch `requests.post`): exercises the REAL adapter end-to-end against the fixture. This is the "byte-identical" assertion at the right layer.
- **`test_parity_end_to_end_classify_intent`** combines Level A with the full call-site path — proves that after extraction, classify_intent still returns the same `result` dict shape (intent, confidence, detected_filters, chart_requested, chart_type).
- **The CS3 (generate_executive_summary) silent-failure test** is critical — RESEARCH.md Pitfall 4 calls this out as a Phase 2 invariant: the broad `except Exception: return None` was intentional and the QueryError raised by `llm_to_query_error()` must still be swallowed. If a future plan adds `except QueryError: raise` to that function, this test fails.

DO NOT add a `pytest.ini` or `conftest.py` — this single file is self-contained. The Phase 1 acceptance gate also took this approach.
  </action>
  <verify>
Run from project root:

```
python -m pytest tests/test_phase2_parity.py -v
```

Expected output (12 tests, all PASS):

```
tests/test_phase2_parity.py::test_call_azure_openai_eliminated PASSED
tests/test_phase2_parity.py::test_parity_q1_structured PASSED
tests/test_phase2_parity.py::test_parity_q2_semantic PASSED
tests/test_phase2_parity.py::test_parity_q3_hybrid PASSED
tests/test_phase2_parity.py::test_parity_q4_sql_generation PASSED
tests/test_phase2_parity.py::test_parity_q5_exec_summary PASSED
tests/test_phase2_parity.py::test_parity_end_to_end_classify_intent PASSED
tests/test_phase2_parity.py::test_parity_end_to_end_generate_sql PASSED
tests/test_phase2_parity.py::test_parity_end_to_end_exec_summary PASSED
tests/test_phase2_parity.py::test_error_translation_at_call_site PASSED
tests/test_phase2_parity.py::test_log_event_shape PASSED
tests/test_phase2_parity.py::test_log_event_on_error_path PASSED

========== 12 passed in <X>s ==========
```

All 12 tests must pass. If any fails, Phase 2 has a regression — the failing test name points at the regressed success criterion.

**Critical**: run BOTH test modules together to confirm Phase 1 stays green:

```
python -m pytest tests/ -v
```

Expected: 6 (Phase 1) + 12 (Phase 2) = 18 tests passing.
  </verify>
  <done>
- `tests/test_phase2_parity.py` exists with 12 standalone test functions (no test classes; verify with `pytest tests/test_phase2_parity.py --collect-only`).
- All 12 tests pass when run via `python -m pytest tests/test_phase2_parity.py -v`.
- Each test docstring cites the Phase 2 success criterion it proves.
- The five-fixture parity test is the headline: `test_parity_q1_structured` through `test_parity_q5_exec_summary` plus three end-to-end tests (`test_parity_end_to_end_classify_intent`, `test_parity_end_to_end_generate_sql`, `test_parity_end_to_end_exec_summary`) that exercise the full call-site chain (mocked `requests.post` → adapter → compat manager → call-site `.strip()` + downstream parse).
- The OBS-02 log shape is asserted via a `logging.Handler` that captures `llm_call` records — all required `llm_*` extra fields are checked.
- Error-translation tests cover all four LLMError subclasses that the compat layer maps (`LLMTimeoutError`, `LLMTransientError`, `LLMAuthError`, `LLMConfigError`) at CS1 (`classify_intent`) and BOTH `LLMTimeoutError` AND `LLMTransientError` at CS2 (`generate_sql`) — the LLMTransientError CS2 assertion locks out a regression where a compat-layer catch-order break would let the error fall into CS2's broad `except Exception` and produce "Failed to generate SQL" instead of "Azure OpenAI API call failed"; CS3 (`generate_executive_summary`) is verified to silently return None on LLM error (intentional).
- Both Phase 1 (`tests/test_llm_seam.py`) and Phase 2 (`tests/test_phase2_parity.py`) tests pass together (18 total).
- The acceptance gate runs offline — zero live HTTP calls.
  </done>
</task>

</tasks>

<verification>
End-of-phase verification — this IS the Phase 2 acceptance gate:

```
# 1. Phase 2 acceptance gate — 12 tests, all green
python -m pytest tests/test_phase2_parity.py -v

# 2. Phase 1 acceptance gate still green
python -m pytest tests/test_llm_seam.py -v

# 3. Both together — no test interferes with the other (autouse fixtures
#    correctly isolate the factory cache + env vars between test modules)
python -m pytest tests/ -v
```

All three commands must show 0 failures. The combined run must show 18 tests passing.

Final cross-cutting checks (verifying the four ROADMAP success criteria from a different angle):

```
# Criterion #1: _call_azure_openai is gone
grep -rn "_call_azure_openai" src/ ; test $? -ne 0 && echo "PASS"

# Criterion #4: log event tag and fields are present in the adapter source
grep -n "llm_call" src/llm/azure_openai.py
grep -n "llm_provider\|llm_model\|llm_latency_ms\|llm_outcome\|llm_prompt_tokens\|llm_completion_tokens\|llm_correlation_id" src/llm/azure_openai.py
```

LOCKED files NOT modified by this plan: everything except `tests/test_phase2_parity.py` + the five fixture files. The Plan 04 surface is test-only.

```
git diff --name-only HEAD src/ app.py config.py 2>&1 | head
```

Must produce no output (no diff to any source file or config — this plan adds only test files).
</verification>

<success_criteria>
- `tests/test_phase2_parity.py` exists and `python -m pytest tests/test_phase2_parity.py -v` exits 0 with 12/12 passing.
- All four Phase 2 success criteria from ROADMAP.md are proven by at least one executable test:
  - #1 (`_call_azure_openai` gone + DI at all 3 sites) → `test_call_azure_openai_eliminated`
  - #2 (five-fixture parity) → adapter-direct: `test_parity_q1_structured`, `test_parity_q2_semantic`, `test_parity_q3_hybrid`, `test_parity_q4_sql_generation`, `test_parity_q5_exec_summary`; full-chain end-to-end through the call sites: `test_parity_end_to_end_classify_intent` (CS1), `test_parity_end_to_end_generate_sql` (CS2), `test_parity_end_to_end_exec_summary` (CS3)
  - #3 (LLMError → QueryError at call site, historic remediation text preserved; CS1 + CS2 both covered, including `LLMTransientError` at CS2 to lock out the broad-except regression path) → `test_error_translation_at_call_site`
  - #4 (one log event per call, full extra-field shape) → `test_log_event_shape`, `test_log_event_on_error_path`
- Five fixture files exist under `tests/fixtures/parity/` with valid JSON content.
- No live HTTP call is made by the test suite (all `requests.post` calls are patched).
- Phase 1 acceptance gate (`tests/test_llm_seam.py`) still 6/6 passing when run alongside Phase 2.
- LOCKED files (everything except `tests/test_phase2_parity.py` and the five fixture files) NOT modified by this plan.

Maps to: All 4 ROADMAP.md Phase 2 success criteria (executable verification). Requirements verified: ABS-06 (criterion #1), ADP-01 + ADP-02 (criterion #2), ERR-04 (criterion #3), OBS-02 (criterion #4).
</success_criteria>

<output>
After completion, create `.planning/phases/02-azure-extraction-parity-gate/02-04-SUMMARY.md` documenting:
- pytest command + exit code + per-test pass/fail for `tests/test_phase2_parity.py` (12 tests expected).
- pytest command + exit code for `tests/test_llm_seam.py` (6 tests expected, must still be green).
- Combined run `pytest tests/` showing 18 tests passing.
- Confirmation that the 4 ROADMAP.md Phase 2 success criteria each map to a passing test (table form: criterion → test function name).
- Confirmation that the test suite runs offline (no live HTTP, all `requests.post` patched).
- Confirmation that this plan modified ONLY `tests/` files — `git diff --name-only HEAD src/ app.py config.py` is empty.
- A short Phase 2 sign-off paragraph: "Phase 2 (Azure Extraction + Parity Gate) is complete. The parity gate is green — Azure adapter extraction is verified byte-identical against five representative queries. Phase 3 (Anthropic MGTI Adapter) is unblocked."
</output>
</content>
</invoke>