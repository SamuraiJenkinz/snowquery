# Phase 2: Azure Extraction + Parity Gate - Research

**Researched:** 2026-05-20
**Domain:** Python `requests` HTTP mocking, context-manager error translation, structured logging, dependency injection via factory cache
**Confidence:** HIGH — all findings from direct codebase reads, installed-package inventory, and Phase 1 artefacts

---

## Summary

Phase 2 has four delegated decision areas. All four are resolvable from what is already on disk; no new library installations are needed for the core refactor. The project has `pytest-mock` (via `pytest 9.0.2` + `pytest-mock 3.15.1`) and `unittest.mock.patch` — both available without touching `requirements.txt`. `vcrpy`, `responses`, and `requests_mock` are **not installed**, so the parity test must use `unittest.mock.patch` to mock `requests.post` at the adapter level.

The two duplicated `_call_azure_openai` functions differ only in `max_tokens` (500 vs 1000). The Phase 1 `complete()` signature already accepts `max_tokens` as a per-call kwarg, so extraction is a near-mechanical substitution. The three call sites return raw strings which are then JSON-parsed (CS1, CS2) or used directly as text (CS3), making the parity assertion straightforward.

The existing logging convention in `src/utils.py` uses `logging.getLogger("snow_query")` with a plain formatter — no JSON, no `extra={}`, no structured helper. Phase 2 should introduce a minimal `_log_llm_call(...)` helper inside `src/llm/azure_openai.py` using `logger.info` with `extra={}`. This approach extends the existing pattern, requires zero new packages, and is reusable verbatim by Phase 3.

**Primary recommendation:** Use `unittest.mock.patch("requests.post")` with hand-rolled JSON fixtures (five frozen response dicts stored in `tests/fixtures/`), a shared `contextlib.contextmanager` for the error translation seam, and inline `client = get_llm()` for dependency injection — patching `src.llm._cache` directly in tests.

---

## Recommended Decisions

### Decision 1: Parity Capture & Verification Mechanism

**Recommendation: Hand-rolled JSON fixtures + `unittest.mock.patch("requests.post")`**

Rationale: `vcrpy` and `responses` are not installed and adding them would grow `requirements.txt` for a test-only concern. `pytest-mock` IS installed and `unittest.mock.patch` is in the stdlib. The right-hand boundary for "byte-identical" is the string the call site receives from `_call_azure_openai` today — i.e., `response.json()["choices"][0]["message"]["content"]`. The adapter wraps HTTP but returns the same string; the parity test patches the HTTP layer and asserts the adapter extracts `content` identically.

**Fixture format:** Five Python dicts stored as JSON files in `tests/fixtures/parity/`:
```
tests/
  fixtures/
    parity/
      q1_structured.json
      q2_semantic.json
      q3_hybrid.json
      q4_exec_summary.json
      q5_structured_sql.json
```

Each fixture file contains the full `requests.Response`-shaped dict that `requests.post(...)` would return — specifically the minimum needed to satisfy `response.raise_for_status()` (status_code 200) and `response.json()["choices"][0]["message"]["content"]` (the text value). Example fixture shape:

```json
{
  "status_code": 200,
  "json": {
    "choices": [
      {
        "message": {
          "content": "{\"intent\": \"structured\", \"confidence\": 0.95, \"reasoning\": \"Aggregation query\", \"detected_filters\": {\"priority\": null, \"assignment_group\": null, \"date_range\": null}}"
        }
      }
    ],
    "usage": {
      "prompt_tokens": 312,
      "completion_tokens": 48,
      "total_tokens": 360
    }
  }
}
```

The test constructs a `MagicMock` response from the fixture, patches `requests.post` to return it, calls through the real adapter, and asserts the returned string equals `fixture["json"]["choices"][0]["message"]["content"]`.

**The five representative queries** (chosen to span all four intent paths and the executive-summary path):

| # | Label | Query Text | Call Site | Expected LLM JSON shape |
|---|-------|-----------|-----------|------------------------|
| Q1 | structured-count | `"How many P1 incidents were opened this week?"` | CS1 classify_intent | intent=structured |
| Q2 | semantic-similar | `"Find incidents similar to VPN connection failures"` | CS1 classify_intent | intent=semantic |
| Q3 | hybrid-filter | `"P1 incidents similar to database outages"` | CS1 classify_intent | intent=hybrid |
| Q4 | sql-generate | `"Top 5 assignment groups by incident count"` | CS2 generate_sql | SQL JSON with `sql`, `explanation`, `confidence` |
| Q5 | exec-summary | `generate_executive_summary` path with small DataFrame input | CS3 generate_executive_summary | Free text (not JSON) |

These five cover all three call sites and all three classification intents. Q4 covers the SQL-generation path which has different max_tokens (1000 vs 500) and a different JSON shape. Q5 covers the executive-summary path which uses the result directly as a string without JSON parsing.

**Confidence: HIGH** — pattern is stdlib-only, no new dependencies.

---

### Decision 2: Error Translation Seam

**Recommendation: Shared `contextlib.contextmanager` helper in `src/llm/_compat.py`**

The translation table is small (four cases). The constraint from CONTEXT.md is that the table appears **exactly once**. The three call sites all already have `except QueryError: raise` or `except Exception` guards — adding `except LLMError` within those guards is the minimal mechanical change.

The cleanest single-source-of-truth pattern that stays readable at the call site and is greppable is a context manager:

```python
# src/llm/_compat.py
import contextlib
from src.llm.errors import (
    LLMAuthError, LLMConfigError, LLMTimeoutError, LLMTransientError, LLMError
)
from src.utils import QueryError

@contextlib.contextmanager
def llm_to_query_error():
    """Translate LLMError subclasses into QueryError at the call-site boundary.

    This is the ONLY place in the codebase that maps LLMError → QueryError.
    Call sites wrap their client.complete(...) call with:
        with llm_to_query_error():
            result = client.complete(...)
    """
    try:
        yield
    except LLMConfigError as e:
        # Preserve the existing remediation text pattern from _call_azure_openai
        raise QueryError(str(e), "Check your .env configuration.") from e
    except LLMAuthError as e:
        raise QueryError(
            "Azure OpenAI API key not configured",
            "Set the AZURE_OPENAI_API_KEY environment variable."
        ) from e
    except LLMTimeoutError as e:
        raise QueryError("Azure OpenAI API call failed", str(e)) from e
    except LLMTransientError as e:
        raise QueryError("Azure OpenAI API call failed", str(e)) from e
    except LLMError as e:
        # Catch-all: any other LLMError subclass surfaces as QueryError
        raise QueryError("Azure OpenAI API call failed", str(e)) from e
```

**Where it lives:** `src/llm/_compat.py` — inside the `src/llm/` package, not in `src/utils.py` (keeping LLM concerns together). The leading underscore signals it is package-internal. Importing `QueryError` from `src.utils` is a cross-package dependency, but it is the correct direction (llm package knows about QueryError; utils does NOT need to know about LLMError).

**Call-site pattern (identical for all three):**
```python
from src.llm import get_llm
from src.llm._compat import llm_to_query_error

# inside classify_intent / generate_sql / generate_executive_summary:
client = get_llm()
with llm_to_query_error():
    content = client.complete(messages, max_tokens=500).strip()
```

**Why not per-call-site try/except:** Boilerplate × 3 means the translation table would appear in three places. When Phase 3 adds Anthropic-specific messages (e.g., "Set the ANTHROPIC_API_KEY environment variable."), all three sites would need updating. The context manager makes it a single edit.

**Why not a decorator on each function:** Decorators on `classify_intent`, `generate_sql`, `generate_executive_summary` would intercept ALL exceptions from those functions, not just LLM exceptions — `QueryError` from non-LLM paths (e.g., the DuckDB validation in `generate_sql`) would be double-wrapped. The context manager wraps only the `client.complete()` call.

**Preservation of existing remediation text:** The existing `_call_azure_openai` raises `QueryError("Azure OpenAI API key not configured", "Set the AZURE_OPENAI_API_KEY environment variable.")` for missing keys and `QueryError("Azure OpenAI API call failed", str(e))` for HTTP failures. The context manager preserves these exact strings. The `LLMAuthError` branch uses the key-not-configured text (matching what users see today when the key is absent). The `LLMTimeoutError`/`LLMTransientError` branches use the call-failed text.

**Confidence: HIGH** — `contextlib.contextmanager` is stdlib; pattern is standard Python.

---

### Decision 3: Structured Log Shape

**Recommendation: `logger.info("llm_call", extra={...})` with a small `_log_llm_call()` helper inside `AzureOpenAIClient`**

The existing logging convention (from `src/utils.py`):
- Uses stdlib `logging.getLogger("snow_query")`
- `StreamHandler` to `sys.stdout`
- Formatter: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
- No JSON, no structured helper, no `extra={}` currently

Streamlit captures `sys.stdout` for display in development mode when the app is run with `streamlit run app.py`. Log lines appear in the terminal where `streamlit run` was invoked, not in the browser UI. JSON-line format on stdout would work but is harder to read during development. The existing plain-text format is appropriate to extend.

The structured log event uses `logger.info(msg, extra=extra_dict)` where the `msg` is a fixed tag and `extra` carries the structured fields. This extends the existing convention without inventing a parallel one. The `extra={}` fields are accessible to any log handler that formats them (e.g., a JSON formatter could be added later in Phase 5 without touching the adapter code).

**Exact event shape:**

```python
extra = {
    "llm_provider": "azure_openai",        # str — from settings or registry key
    "llm_model": "<model-from-endpoint>",  # str — derived from AZURE_OPENAI_ENDPOINT if parseable, else "unknown"
    "llm_latency_ms": 234,                 # int — measured via time.monotonic()
    "llm_outcome": "success",              # str — "success" | "error"
    "llm_error_type": None,                # str | None — LLMError subclass name on error, None on success
    "llm_prompt_tokens": 312,              # int | None — from response["usage"]["prompt_tokens"] if present
    "llm_completion_tokens": 48,           # int | None — from response["usage"]["completion_tokens"] if present
    "llm_correlation_id": None,            # str | None — None in Phase 2, populated in Phase 3 from X-Correlation-Id
}
logger.info("llm_call", extra=extra)
```

**Token counts when missing:** Set to `None` (not `0`). Azure OpenAI usually returns `usage` but may omit it on certain error paths. `None` is semantically correct ("we don't know") vs `0` (misleading — implies zero tokens used). The `llm_prompt_tokens` and `llm_completion_tokens` fields use `response.json().get("usage", {}).get("prompt_tokens")` — returns `None` if absent.

**Granularity:** Single end-of-call event. Start+end pairs are useful for distributed tracing but are overkill for Phase 2 — the latency field in the single event is sufficient for monitoring. A start event would add noise without adding diagnostic value at this scale.

**`outcome` field values:** `"success"` or `"error"`. On error, `llm_error_type` carries the exception class name (e.g., `"LLMTimeoutError"`). This is simpler than a richer enum and fully greppable.

**Helper placement:** A `_log_llm_call(extra: dict) -> None` private function at module level in `src/llm/azure_openai.py`. Phase 3 copies the identical helper into `src/llm/anthropic_mgti.py`. This is intentional duplication (two files, two adapters) — if a shared helper is later justified, it can be extracted to `src/llm/_compat.py`. For Phase 2/3, keeping it inline in the adapter is simpler and avoids premature abstraction.

**Logger instance:** Import `from src.utils import logger` so both adapters share the same `"snow_query"` logger. Do NOT create a new logger with a different name.

**Placement in the adapter:** Inside `complete()`, wrap the HTTP call in a try/finally:
```python
import time
_t0 = time.monotonic()
try:
    response = requests.post(...)
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    _log_llm_call({..., "llm_outcome": "success", "llm_latency_ms": int((time.monotonic() - _t0) * 1000), ...})
    return text
except requests.exceptions.Timeout as e:
    _log_llm_call({..., "llm_outcome": "error", "llm_error_type": "LLMTimeoutError", ...})
    raise LLMTimeoutError(...) from e
except requests.exceptions.HTTPError as e:
    ...  # map to LLMAuthError / LLMTransientError
    _log_llm_call({..., "llm_outcome": "error", "llm_error_type": "LLMTransientError", ...})
    raise ...
```

**Confidence: HIGH** — stdlib `logging` + `time.monotonic()`, no new packages.

---

### Decision 4: Dependency Injection Pattern

**Recommendation: Inline `client = get_llm()` at the top of each call-site function**

The three call sites today call `_call_azure_openai(messages)` which reads globals directly. After extraction, the minimal-diff replacement is:
```python
from src.llm import get_llm
from src.llm._compat import llm_to_query_error

# Replace: content = _call_azure_openai(messages).strip()
# With:
client = get_llm()
with llm_to_query_error():
    content = client.complete(messages, max_tokens=500).strip()
```

**Why not function parameter `llm: LLMClient | None = None`:** The three call-site functions (`classify_intent`, `generate_sql`, `generate_executive_summary`) are called from `route_query`, `query_with_sql`, and `app.py`. Rippling an optional `llm` parameter through all three plus their callers is a signature change that Phase 2 does not need to make. The factory cache already provides a single point to override in tests (by patching `src.llm._cache` or `src.llm.get_llm`). Phase 5's mid-session switch works because `get_llm()` re-resolves from session state on each call — the factory cache is keyed by provider string, and when the user switches providers in the sidebar, `st.session_state["llm_provider"]` changes, `get_llm()` resolves to the new key, and either finds it in `_cache` or instantiates a new adapter.

**Test override mechanism:** In the parity test, patch `src.llm.get_llm` to return a `FakeAzureClient` (or monkeypatch `requests.post` at the HTTP level if testing the real adapter end-to-end). The Phase 1 pattern (`llm_pkg._cache.clear()` + `llm_pkg._cache["azure_openai"] = fake_instance`) is the simplest and most consistent with the established Phase 1 acceptance gate pattern.

```python
# In test:
import src.llm as llm_pkg
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def _clear_factory_cache():
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()

def test_parity_q1_structured(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.raise_for_status = lambda: None
    fake_response.json.return_value = FIXTURE_Q1  # loaded from tests/fixtures/parity/q1_structured.json
    with patch("requests.post", return_value=fake_response):
        # Call the real adapter (which has been populated into cache)
        ...
```

**Confidence: HIGH** — follows Phase 1 established pattern exactly.

---

## Parity Test Strategy

### Library/Approach

Use `unittest.mock.patch("requests.post")` with hand-rolled JSON fixtures. No new test dependencies needed. `pytest-mock` provides the `mocker` fixture as an alternative to `unittest.mock.patch`; either works. The Phase 1 test used `monkeypatch` for env vars — stay consistent and use `monkeypatch` + `unittest.mock.patch` for the parity test.

The parity test exercises the **real `AzureOpenAIClient.complete()` method** with a mocked HTTP layer. This is the correct layer to mock: it proves the adapter correctly extracts `response.json()["choices"][0]["message"]["content"]` and returns it as-is, which is what `_call_azure_openai` does today.

### Fixture Format

```
tests/
  fixtures/
    parity/
      q1_structured_classification.json
      q2_semantic_classification.json
      q3_hybrid_classification.json
      q4_sql_generation.json
      q5_exec_summary.json
```

Each JSON file is a dict with two keys: `"request_messages"` (the messages list sent, for documentation) and `"response_json"` (the Azure OpenAI response body). Example for Q1:

```json
{
  "request_messages": [
    {"role": "system", "content": "...CLASSIFICATION_PROMPT..."},
    {"role": "user", "content": "How many P1 incidents were opened this week?"}
  ],
  "response_json": {
    "choices": [
      {
        "message": {
          "content": "{\"intent\": \"structured\", \"confidence\": 0.95, \"reasoning\": \"Count aggregation query\", \"detected_filters\": {\"priority\": [\"P1\"], \"assignment_group\": null, \"date_range\": \"this week\"}}"
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

The test loads the fixture, mocks `requests.post` to return a `MagicMock` with `status_code=200`, `raise_for_status()` no-op, and `json()` returning `fixture["response_json"]`. It then calls the adapter and asserts the returned string equals `fixture["response_json"]["choices"][0]["message"]["content"]`.

### The Five Queries

| # | File | Query / Input | Call Site | Asserts |
|---|------|--------------|-----------|---------|
| Q1 | `q1_structured_classification.json` | `"How many P1 incidents were opened this week?"` | `classify_intent` → `complete(max_tokens=500)` | returned str == fixture content |
| Q2 | `q2_semantic_classification.json` | `"Find incidents similar to VPN connection failures"` | `classify_intent` → `complete(max_tokens=500)` | returned str == fixture content |
| Q3 | `q3_hybrid_classification.json` | `"P1 incidents similar to database outages"` | `classify_intent` → `complete(max_tokens=500)` | returned str == fixture content |
| Q4 | `q4_sql_generation.json` | `"Top 5 assignment groups by incident count"` | `generate_sql` → `complete(max_tokens=1000)` | returned str == fixture content; verify `max_tokens=1000` was passed |
| Q5 | `q5_exec_summary.json` | Short DataFrame with 3 rows of dummy incidents | `generate_executive_summary` → `complete(max_tokens=500)` | returned str == fixture content |

**How to capture them:** The fixtures are hand-authored to contain realistic but synthetic Azure response payloads. They do NOT require a live Azure call — the intent is to prove the adapter's extraction logic is correct, not to record real responses. The "byte-identical" contract is: given the same `requests.Response` mock, the adapter returns the same string that `_call_azure_openai` would return today (which is `response.json()["choices"][0]["message"]["content"]`). Since both old and new code do exactly this extraction, the parity test reduces to "does the new adapter make the same extraction call?" — which is verifiable with a fixture.

### Error-Path Parity

The parity test must also cover two error paths (Phase 2 success criterion #3):

| Error Scenario | Old behavior | New behavior (must match) |
|---|---|---|
| `AZURE_OPENAI_API_KEY` not set | `_call_azure_openai` raises `QueryError("Azure OpenAI API key not configured", "Set the AZURE_OPENAI_API_KEY environment variable.")` | `client.complete()` raises `LLMConfigError`; `llm_to_query_error()` translates to same `QueryError` text |
| `requests.exceptions.RequestException` (timeout/5xx) | `QueryError("Azure OpenAI API call failed", str(e))` | `client.complete()` raises `LLMTimeoutError` or `LLMTransientError`; `llm_to_query_error()` translates to `QueryError("Azure OpenAI API call failed", ...)` |

The test injects a `MagicMock` that raises `requests.exceptions.Timeout` and asserts the call site catches `QueryError` with the correct `.message` text.

---

## Error Translation Design

### Translation Table (appears EXACTLY ONCE in `src/llm/_compat.py`)

```python
LLMConfigError    → QueryError("Azure OpenAI API key not configured",
                               "Set the AZURE_OPENAI_API_KEY environment variable.")
                    # OR for endpoint: QueryError("Azure OpenAI endpoint not configured",
                    #                             "Set the AZURE_OPENAI_ENDPOINT environment variable.")
                    # Discriminate by str(e) content — see note below

LLMAuthError      → QueryError("Azure OpenAI API key not configured",
                               "Set the AZURE_OPENAI_API_KEY environment variable.")

LLMTimeoutError   → QueryError("Azure OpenAI API call failed", str(e))

LLMTransientError → QueryError("Azure OpenAI API call failed", str(e))

LLMError (base)   → QueryError("Azure OpenAI API call failed", str(e))
```

**Note on `LLMConfigError` discrimination:** The old `_call_azure_openai` has two separate config checks — one for missing API key and one for missing endpoint. The adapter's `complete()` will do the same two checks and raise `LLMConfigError` with different messages for each. The translation in `llm_to_query_error()` should preserve the message from `str(e)` rather than hardcoding "API key not configured" for all config errors:

```python
except LLMConfigError as e:
    raise QueryError(str(e), "Check your .env configuration.") from e
```

This is simpler and more future-proof than trying to discriminate between key vs endpoint errors in the context manager. The `LLMAuthError` branch is the one that should use the specific API key remediation text (it fires on HTTP 401/403 when the key IS set but invalid).

### Where It Lives

`src/llm/_compat.py` — one new file, package-internal, contains only `llm_to_query_error()`.

### How Each Call Site Invokes It

```python
# query_router.py — classify_intent (CS1):
client = get_llm()
with llm_to_query_error():
    content = client.complete(messages, max_tokens=500).strip()

# sql_generator.py — generate_sql (CS2):
client = get_llm()
with llm_to_query_error():
    content = client.complete(messages, max_tokens=1000).strip()

# query_router.py — generate_executive_summary (CS3):
client = get_llm()
with llm_to_query_error():
    summary = client.complete(messages, max_tokens=500).strip()
```

The `except QueryError: raise` guards that already exist in CS1 and CS2 remain unchanged — `llm_to_query_error()` raises `QueryError`, which the existing guards pass through correctly.

---

## Logging Design

### Exact Event Shape

```python
# Field names, types, and when each is populated:
{
    "llm_provider":          str,        # always — registry key, e.g. "azure_openai"
    "llm_model":             str,        # always — parsed from endpoint URL or "unknown"
    "llm_latency_ms":        int,        # always — time.monotonic() delta in ms
    "llm_outcome":           str,        # always — "success" | "error"
    "llm_error_type":        str | None, # None on success; LLMError subclass __name__ on error
    "llm_prompt_tokens":     int | None, # from response["usage"]["prompt_tokens"]; None if absent
    "llm_completion_tokens": int | None, # from response["usage"]["completion_tokens"]; None if absent
    "llm_correlation_id":    str | None, # None in Phase 2; populated from X-Correlation-Id in Phase 3
}
```

### Format

`logger.info("llm_call", extra=extra_dict)` — one call per `complete()` invocation. The `"llm_call"` message is the fixed tag; all structured data is in `extra`. This matches the existing `logger.info(f"...")` convention in `query_router.py` and `sql_generator.py` (same `logger` instance from `src.utils`).

The plain text formatter from `src/utils.py` will render these as:
```
2026-05-20 14:23:01 - snow_query - INFO - llm_call
```

The structured fields in `extra` are available to any downstream log handler but are not visible in the default formatter. This is acceptable for Phase 2 — the requirement (OBS-02) says the adapter "emits one structured log event per call"; it does not require the fields to appear in the console output. A JSON formatter can be added to `setup_logging()` in a later phase without touching adapter code.

### Where the Helper Lives

`_log_llm_call(extra: dict) -> None` — private module-level function in `src/llm/azure_openai.py`. Phase 3 copies the identical function into `src/llm/anthropic_mgti.py`. If both adapters are ever unified, extract to `src/llm/_compat.py`.

### Model Extraction

`AZURE_OPENAI_ENDPOINT` contains the full URL: `https://xxx.openai.azure.com/openai/deployments/<deployment-name>/chat/completions`. The deployment name (proxy for "model") can be extracted with a URL parse:

```python
from urllib.parse import urlparse

def _extract_model_from_endpoint(endpoint: str) -> str:
    """Extract deployment name from Azure endpoint URL, or return 'unknown'."""
    try:
        parts = urlparse(endpoint).path.split("/")
        idx = parts.index("deployments")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return "unknown"
```

This is called once at adapter construction time and cached as `self._model`.

---

## DI Pattern

### Exact Call-Site Change

For all three call sites, the change is mechanical:

**Before (in `query_router.py:180`):**
```python
content = _call_azure_openai(messages).strip()
```

**After:**
```python
from src.llm import get_llm
from src.llm._compat import llm_to_query_error

client = get_llm()
with llm_to_query_error():
    content = client.complete(messages, max_tokens=500).strip()
```

The `from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, API_VERSION` imports in `query_router.py` and `sql_generator.py` become unused once `_call_azure_openai` is deleted — remove them to keep the files clean.

### Exact Test Override Mechanism

The parity test patches at two possible levels:

**Level A (HTTP layer — tests the real adapter end-to-end):**
```python
with patch("requests.post", return_value=mock_response):
    # get_llm() returns real AzureOpenAIClient
    # AzureOpenAIClient.complete() calls requests.post (mocked)
    result = classify_intent(query, schema_summary)
```

**Level B (factory cache — injects a fake adapter):**
```python
import src.llm as llm_pkg
fake_client = MagicMock(spec=LLMClient)
fake_client.complete.return_value = fixture_content
llm_pkg._cache["azure_openai"] = fake_client
result = classify_intent(query, schema_summary)
```

**Recommendation: Level A for parity tests.** Level A exercises the adapter's actual HTTP extraction logic, which is what "byte-identical" means. Level B is appropriate for unit tests of call-site parsing logic (e.g., testing JSON parse fallback in `classify_intent`). Both patterns are valid and the Phase 2 acceptance gate should include both.

The `_clear_factory_cache` autouse fixture from Phase 1 must be included in the Phase 2 test module — it is a load-bearing pattern for module-level singleton isolation.

---

## Risks & Edge Cases

### Risk 1: Azure Non-Determinism at temperature=0.1

**What:** `temperature=0.1` is not deterministic. Azure OpenAI with `temperature=0.0` is also not guaranteed deterministic across API versions or deployments. Live A/B comparison would fail the parity gate intermittently.

**Mitigation:** The parity test does NOT call the live Azure endpoint. It mocks `requests.post` with fixtures. The "byte-identical" contract applies to the fixture→adapter→call-site chain, not to live outputs. This is the correct interpretation of CONTEXT.md: "capture real Azure responses for the five queries once, save as fixtures, mock the HTTP layer."

**Confidence: HIGH** — design explicitly avoids the non-determinism problem.

### Risk 2: JSON Parse Differences in Call-Site Logic

**What:** CS1 (`classify_intent`) and CS2 (`generate_sql`) JSON-parse the string returned by `complete()`. If the adapter changes the returned string in any way (trailing whitespace, encoding differences), JSON parsing could produce different results.

**Mitigation:** The adapter must return `response.json()["choices"][0]["message"]["content"]` with no transformation (no `.strip()`, no encoding changes). The `.strip()` is applied AT the call site (it already exists there: `content = _call_azure_openai(messages).strip()`). The call site will be changed to `content = client.complete(messages, max_tokens=500).strip()` — same `.strip()` at the same place. The fixture parity test asserts the raw string from `complete()` is identical to the fixture content; the `.strip()` and JSON parsing are tested by the call-site unit tests.

### Risk 3: Missing `usage` Block

**What:** Azure OpenAI may return a response without a `usage` block (e.g., on quota exhaustion before generation starts, or on certain streaming configurations). The adapter must not raise on a missing `usage` block.

**Mitigation:** Use `.get()` chains: `response.json().get("usage", {}).get("prompt_tokens")` — returns `None` safely. This is documented in the logging design above (token counts are `int | None`).

### Risk 4: HTTP 401 vs Missing Key

**What:** The old `_call_azure_openai` raises `QueryError("Azure OpenAI API key not configured", "Set the AZURE_OPENAI_API_KEY environment variable.")` for a MISSING key (checked before the HTTP call), but the same user-visible message would make sense for an INVALID key (HTTP 401). After extraction, the adapter raises `LLMConfigError` for missing key (pre-flight check) and `LLMAuthError` for HTTP 401. The error translation seam must map both to `QueryError` with consistent text.

**Mitigation:** The `llm_to_query_error()` context manager maps `LLMConfigError` to a generic "Check your .env configuration" message and `LLMAuthError` to the specific "Set the AZURE_OPENAI_API_KEY environment variable" text. This is a slight behavior change: today, a missing key raises "Azure OpenAI API key not configured" before any HTTP call; an invalid key would also raise "Azure OpenAI API call failed" (via `requests.exceptions.RequestException`). After extraction: missing key → `LLMConfigError` → `QueryError` with config message; invalid key → HTTP 401 → `LLMAuthError` → `QueryError` with auth-remediation message. The parity test must cover BOTH cases.

### Risk 5: `classify_intent` Exception Swallowing

**What:** `classify_intent` has a broad `except Exception as e: return _heuristic_classify(user_query)` at line 215 in `query_router.py`. This means `QueryError` raised by `llm_to_query_error()` inside the `try:` block would normally be re-raised by the `except QueryError: raise` at line 213 — but only if `QueryError` is caught first. The order of `except` clauses matters.

**Mitigation:** The existing code already has `except QueryError: raise` before `except Exception`, so `QueryError` from `llm_to_query_error()` propagates correctly. The Phase 2 change does not alter the exception handler order. Verify this in the test by asserting that a mocked `LLMTimeoutError` from the adapter surfaces as `QueryError` at the caller of `classify_intent`, NOT as a heuristic fallback result.

### Risk 6: `_call_azure_openai` Import Removal

**What:** After deletion, `from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, API_VERSION` in `query_router.py` and `sql_generator.py` becomes unused. If any other code in those files still needs those imports, removing them would break things.

**Mitigation:** Grep both files for `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `API_VERSION` usage outside of `_call_azure_openai`. From reading the files: these names appear ONLY inside `_call_azure_openai`. Safe to remove the imports.

### Risk 7: `generate_executive_summary` Silent Failure Path

**What:** `generate_executive_summary` has a broad `except Exception: return None` (line 546). After extraction, `QueryError` raised by `llm_to_query_error()` would be caught by this `except Exception` and silently swallowed (returning `None`). This is actually the EXISTING behavior — `_call_azure_openai` raises `QueryError` which is a subclass of `Exception`, so the current code also swallows it here. The parity is preserved (both old and new return `None` on error for this function).

**Mitigation:** No change needed — the existing silent-failure behavior is intentional for executive summary generation (it's optional; the app continues without it). Document this in the Phase 2 plan so the planner does not add `except QueryError: raise` to this function.

---

## Phase 3 Compatibility Check

The four decisions are checked against Phase 3's `AnthropicMGTIClient` requirements:

### Parity Mechanism (Decision 1)

Phase 3 will use the same `unittest.mock.patch("requests.post")` pattern with its own fixtures in `tests/fixtures/parity/`. The fixture format (dict with `request_messages` + `response_json`) will need to reflect Anthropic's response shape instead of Azure's, but the test infrastructure is identical. **Phase 3-clean: YES.**

### Error Translation Seam (Decision 2)

`llm_to_query_error()` in `src/llm/_compat.py` catches `LLMError` subclasses and translates to `QueryError`. Phase 3 adds `LLMGuardrailError` (Anthropic-specific `stop_reason == "guardrail_intervened"`). The current context manager has a catch-all `except LLMError` branch that would handle `LLMGuardrailError` correctly. Phase 3 may want to add a specific branch for `LLMGuardrailError` with a different `QueryError` message — it can do so by editing `_compat.py` in one place. **Phase 3-clean: YES, one edit in one file.**

The provider-specific remediation text ("Set the AZURE_OPENAI_API_KEY environment variable") is currently hardcoded in `llm_to_query_error()`. Phase 3 needs different remediation text ("Set the ANTHROPIC_API_KEY environment variable"). Options:
- Make `llm_to_query_error()` accept a `provider` parameter and branch on it
- Have each adapter raise `LLMConfigError` with the provider-specific message already embedded in `str(e)`, and let `llm_to_query_error()` use `str(e)` for the `QueryError` message

The second option is cleaner and avoids leaking provider logic into the compat layer. **Recommendation: `AzureOpenAIClient` embeds remediation text in `LLMConfigError` messages; `llm_to_query_error()` uses `str(e)` for the `QueryError.message`.**

### Structured Log Shape (Decision 3)

Phase 3's `AnthropicMGTIClient` emits the same event shape:
- `llm_provider`: `"anthropic_mgti"`
- `llm_model`: from `ANTHROPIC_MODEL` env var (no URL parsing needed)
- `llm_correlation_id`: populated from `X-Correlation-Id` response header (Phase 3 specific)
- Token counts: from Anthropic's `usage.input_tokens` and `usage.output_tokens` (different field names than Azure's `prompt_tokens`/`completion_tokens`)

The field NAMES in `extra` are shared between adapters. The values differ by provider. Phase 3 copies `_log_llm_call()` and maps Anthropic field names to the shared schema. **Phase 3-clean: YES, field names are stable.**

Note: Anthropic MGTI's response shape uses `"usage": {"input_tokens": N, "output_tokens": N}` (not `prompt_tokens`/`completion_tokens`). The `_log_llm_call()` helper in Phase 3 maps `input_tokens → llm_prompt_tokens` and `output_tokens → llm_completion_tokens`. The log event shape stays identical across providers.

### DI Pattern (Decision 4)

Phase 3's `AnthropicMGTIClient` registers under `"anthropic_mgti"` in `_REGISTRY`. `get_llm("anthropic_mgti")` returns it. Call sites already use `client = get_llm()` — when the user switches to Anthropic in Phase 5, `get_llm()` resolves to `"anthropic_mgti"` and all three call sites automatically use the Anthropic adapter. No call-site changes needed in Phase 3. **Phase 3-clean: YES.**

---

## Open Questions for Planner

### OQ-1: `LLMConfigError` Message Content for `llm_to_query_error()`

The planner must decide whether `AzureOpenAIClient.complete()` embeds provider-specific remediation text in the `LLMConfigError` message (e.g., `"Azure OpenAI API key not configured. Set the AZURE_OPENAI_API_KEY environment variable."`) and `llm_to_query_error()` passes `str(e)` through as `QueryError.message`, OR whether `llm_to_query_error()` hardcodes the Azure-specific text for Phase 2.

**Recommendation:** Embed in the `LLMConfigError` message at raise time and pass through in `llm_to_query_error()`. This is the Phase-3-clean path and avoids editing `_compat.py` for each new provider.

### OQ-2: Where to Put `_compat.py` vs Inline in Adapter

The planner must decide if `llm_to_query_error()` lives in `src/llm/_compat.py` (importable by call sites) or in each adapter module. Since call sites in `query_router.py` and `sql_generator.py` import it directly, it must be in a shared location. `src/llm/_compat.py` is the right place.

**This is a closed question in the research; adding it as a planner note to confirm the file creation task.**

### OQ-3: Fixture Authoring vs Live Capture

The planner must decide whether the five parity fixtures are:
- A) Hand-authored with realistic but synthetic content (no live Azure needed)
- B) Captured from a live Azure call during Phase 2 work and committed as files

Option B is the most rigorous "parity" story but requires live credentials during the planning/implementation phase. Option A is sufficient for proving the adapter extraction logic is correct.

**Recommendation: Option A for the acceptance gate (no live credentials required in CI); add a note in the plan that Option B can replace the fixtures for extra confidence if credentials are available during development.**

### OQ-4: `classify_with_tool` in AzureOpenAIClient

Phase 2 requirements include ADP-02: `AzureOpenAIClient.classify_with_tool` uses prompt-based JSON parsing. The three call sites today only call `complete()` — none of them call `classify_with_tool()`. The planner must decide whether Phase 2 implements `classify_with_tool()` for Azure (even though no call site uses it yet) or leaves it as `NotImplementedError`. 

**Recommendation: Implement it in Phase 2** as it is listed in requirements (ADP-02) and is needed to prove the adapter is not a stub. The implementation is mechanical: build a prompt from `ToolSchema`, call `complete()`, JSON-parse the result, return `ToolCall`. The parity gate does not need to cover it (no existing call site to compare against), but it should have a unit test.

### OQ-5: Imports to Remove from `query_router.py` and `sql_generator.py`

After deleting `_call_azure_openai`, the following imports become unused:
- `query_router.py`: `from config import API_VERSION, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT`
- `sql_generator.py`: `from config import API_VERSION, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT`
- Both files: `import requests` (used only by `_call_azure_openai`)

The planner must include a task to remove these imports. Leaving them in triggers linting warnings and is misleading.

---

## Standard Stack

### Core (no new installs needed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `unittest.mock` | stdlib | HTTP mocking for parity tests | `patch("requests.post", ...)` |
| `pytest-mock` | 3.15.1 (installed) | `mocker` fixture alternative | Optional; `unittest.mock.patch` is sufficient |
| `contextlib` | stdlib | Error translation context manager | `@contextlib.contextmanager` |
| `time` | stdlib | Latency measurement | `time.monotonic()` |
| `logging` | stdlib | Structured log events | `logger.info("llm_call", extra={...})` |
| `requests` | >=2.31.0 (installed) | HTTP calls in adapter | Already in requirements.txt |
| `json` | stdlib | Fixture loading in tests | `json.load(open(...))` |

### No New Dependencies Needed

The Phase 2 implementation requires zero additions to `requirements.txt`. All needed libraries are either stdlib or already installed.

---

## Common Pitfalls

### Pitfall 1: Calling `.strip()` Inside the Adapter

The call sites do `.strip()` on the return value today. If the adapter also `.strip()`s, the test will still pass but the behavior changes (double-strip is idempotent, but it is not byte-identical to the old path where `.strip()` happened only at the call site). The adapter must NOT strip — return `response.json()["choices"][0]["message"]["content"]` as-is.

### Pitfall 2: `requests` Import Scope

`import requests` is currently at the top of `query_router.py` and `sql_generator.py`. After `_call_azure_openai` is deleted, `requests` is no longer needed in those files but IS needed in `src/llm/azure_openai.py`. Make sure the adapter imports `requests` and the call-site files remove the now-unused import.

### Pitfall 3: `lru_cache` vs Module-Level `_cache` Dict

The factory uses a plain dict `_cache` (not `@functools.lru_cache`). Tests must clear `src.llm._cache` (not invalidate an `lru_cache`). The Phase 1 pattern (`llm_pkg._cache.clear()`) is correct.

### Pitfall 4: `generate_executive_summary` Exception Behavior

This function has `except Exception: return None`. After extraction, `QueryError` raised inside the `with llm_to_query_error():` block propagates out of the context manager as `QueryError` (a subclass of `Exception`), and is caught by the function's broad handler, returning `None`. This is correct and matches today's behavior. Do NOT add `except QueryError: raise` to `generate_executive_summary` — it would break the existing UI behavior where a failed summary is silently skipped.

### Pitfall 5: Phase 3 `usage` Field Name Mismatch

Azure: `usage.prompt_tokens` / `usage.completion_tokens`
Anthropic: `usage.input_tokens` / `usage.output_tokens`

The `_log_llm_call()` helper in Phase 2 accesses `.get("usage", {}).get("prompt_tokens")`. Phase 3 must use `.get("usage", {}).get("input_tokens")` but map it to the same `"llm_prompt_tokens"` key in `extra`. Document this mapping in a comment in Phase 3's `_log_llm_call()`.

---

## Sources

### Primary (HIGH confidence — direct code reads)

- `C:\mbrunoapp\snow_query\src\query_router.py` — three call sites, `_call_azure_openai` definition (lines 105–141), exception handling patterns
- `C:\mbrunoapp\snow_query\src\sql_generator.py` — CS2 `_call_azure_openai` definition (lines 86–133), `generate_sql` exception guards
- `C:\mbrunoapp\snow_query\src\utils.py` — `logger` setup pattern, `QueryError` class, formatter string
- `C:\mbrunoapp\snow_query\src\llm\errors.py` — confirmed LLMError hierarchy (all 6 subclasses)
- `C:\mbrunoapp\snow_query\src\llm\azure_openai.py` — Phase 1 stub confirmed
- `C:\mbrunoapp\snow_query\src\llm\__init__.py` — factory, `_cache` dict, `_REGISTRY`
- `C:\mbrunoapp\snow_query\src\llm\base.py` — `complete()` signature confirmed
- `C:\mbrunoapp\snow_query\tests\test_llm_seam.py` — Phase 1 test patterns (`_clear_factory_cache` fixture, monkeypatch usage)
- `C:\mbrunoapp\snow_query\requirements.txt` — confirmed `requests>=2.31.0` present; no `vcrpy`/`responses`/`requests_mock`
- `C:\mbrunoapp\snow_query\.planning\phases\01-abstraction-seam\01-RESEARCH.md` — MGTI response shape, Phase 1 decisions
- `pip list` output — confirmed `pytest-mock 3.15.1`, `pytest 9.0.2`; no `vcrpy`, `responses`, `requests_mock`
- `python -c "import unittest.mock"` — confirmed stdlib mock available

### Secondary (MEDIUM confidence)

- `C:\mbrunoapp\snow_query\USER_GUIDE.md` — five representative queries sourced from documented example queries
- `C:\mbrunoapp\snow_query\.planning\STATE.md` — accumulated decisions confirming Phase 2 intent

---

## Metadata

**Confidence breakdown:**
- Parity mechanism (mock approach): HIGH — stdlib only, no new deps
- Error translation (context manager): HIGH — well-established Python pattern
- Logging shape: HIGH — extends existing convention directly
- DI pattern (inline get_llm): HIGH — follows Phase 1 factory design exactly
- Phase 3 compatibility: HIGH — cross-checked against MGTI skill documented in Phase 1 research

**Research date:** 2026-05-20
**Valid until:** 2026-06-19 (30 days; stable Python patterns)

---

## RESEARCH COMPLETE

All four delegated decision areas have concrete recommendations supported by direct codebase evidence. No new library installs are needed. The implementation path is clear enough for the planner to decompose into PLAN.md files immediately.
