---
phase: 02-azure-extraction-parity-gate
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/azure_openai.py
autonomous: true

must_haves:
  truths:
    - "AzureOpenAIClient.complete() returns response.json()['choices'][0]['message']['content'] as-is (no .strip(), no transformation) — preserves byte-identical extraction vs today's _call_azure_openai (success criterion #2, ADP-01)"
    - "AzureOpenAIClient.complete() pre-flight checks AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT — missing values raise LLMConfigError with provider-specific remediation embedded in the message (RESEARCH.md OQ-1)"
    - "HTTP 401/403 → LLMAuthError; 429/5xx → LLMTransientError; requests.Timeout → LLMTimeoutError (ERR-02 scoped to Azure)"
    - "Every complete() call emits exactly one logger.info('llm_call', extra={...}) event carrying llm_provider, llm_model, llm_latency_ms, llm_outcome, llm_error_type, llm_prompt_tokens, llm_completion_tokens, llm_correlation_id (success criterion #4, OBS-02)"
    - "AzureOpenAIClient.classify_with_tool() implements prompt-based JSON parsing — calls complete(), JSON-parses the result, validates against tool.input_schema via jsonschema.validate, returns ToolCall (ADP-02)"
    - "repr(AzureOpenAIClient()) does NOT leak the API key (OBS-03 preserved from Phase 1)"
  artifacts:
    - path: "src/llm/azure_openai.py"
      provides: "AzureOpenAIClient with real complete() and classify_with_tool() implementations + _log_llm_call helper + _extract_model_from_endpoint helper"
      contains: "class AzureOpenAIClient(LLMClient)"
      min_lines: 150
  key_links:
    - from: "src/llm/azure_openai.py"
      to: "requests.post"
      via: "POST {endpoint}?api-version={version} with api-key header"
      pattern: "requests\\.post"
    - from: "src/llm/azure_openai.py"
      to: "src.utils.logger"
      via: "logger.info('llm_call', extra={...}) emitted in try/finally inside complete()"
      pattern: "logger\\.info.*llm_call.*extra"
    - from: "src/llm/azure_openai.py"
      to: "src.llm.errors"
      via: "raises LLMConfigError / LLMAuthError / LLMTransientError / LLMTimeoutError per ERR-02"
      pattern: "raise LLM(Auth|Transient|Timeout|Config|Schema)Error"
---

<objective>
Replace the Phase 1 stub `AzureOpenAIClient` with a real implementation that wraps the same Azure OpenAI HTTP call shape used by today's `_call_azure_openai`, plus typed-error mapping, a structured logging hook, and the `classify_with_tool` prompt-based JSON path required by ADP-02.

Purpose: The adapter is the single piece of code that talks to Azure OpenAI HTTP in the new world. Plan 03 deletes the two duplicated `_call_azure_openai` definitions and routes all three call sites through this adapter — but only if this plan's `complete()` extracts the response content byte-identically to today and raises typed `LLMError` subclasses the error-translation seam (Plan 02) can map back to `QueryError`.

Output: One file rewritten — `src/llm/azure_openai.py` — going from a ~47-line stub to a ~150+ line real adapter with `complete()`, `classify_with_tool()`, `_log_llm_call()` helper, and `_extract_model_from_endpoint()` helper.
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

# The seam this adapter plugs into (READ-ONLY here)
@src/llm/base.py
@src/llm/errors.py
@src/llm/types.py
@src/llm/config.py

# The current Azure call shape this adapter must preserve byte-identically
@src/query_router.py
@src/sql_generator.py
@src/utils.py
@config.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement AzureOpenAIClient.complete() with typed errors and structured logging</name>
  <files>src/llm/azure_openai.py</files>
  <action>
Rewrite `src/llm/azure_openai.py`, replacing the Phase 1 stub with a real adapter implementation. Preserve the file-level docstring style and import conventions from the existing stub.

Implementation requirements drawn from RESEARCH.md ("Logging Design", "Error Translation Design", "Risks & Edge Cases", "Common Pitfalls"):

**1. Module-level imports** (top of file, after the docstring):
```python
from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import requests

from src.llm.base import LLMClient
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.llm.types import ToolCall, ToolSchema
from src.utils import logger
```

Note: Import `logger` from `src.utils`, NOT from `src.llm` — both adapters (Azure now, Anthropic in Phase 3) share the same `"snow_query"` logger instance for log correlation.

**2. Module-level helper `_extract_model_from_endpoint(endpoint: str) -> str`** (exact shape from RESEARCH.md):
```python
def _extract_model_from_endpoint(endpoint: str) -> str:
    """Extract Azure deployment name (proxy for 'model') from the endpoint URL.

    Azure endpoints look like:
        https://xxx.openai.azure.com/openai/deployments/<deployment>/chat/completions

    Returns the deployment name, or 'unknown' if the URL doesn't fit that shape.
    Called once at adapter construction; cached on the instance as self._model.
    """
    try:
        parts = urlparse(endpoint).path.split("/")
        idx = parts.index("deployments")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return "unknown"
```

**3. Module-level helper `_log_llm_call(extra: dict) -> None`** (exact shape from RESEARCH.md):
```python
def _log_llm_call(extra: dict) -> None:
    """Emit one structured log event per LLM call (OBS-02).

    The 'msg' is the fixed tag 'llm_call'; all structured fields live in extra.
    The existing snow_query logger uses a plain-text formatter, so the structured
    fields are not visible in default console output — but they are accessible
    to any downstream handler (e.g. a JSON formatter could be added later in
    setup_logging() without touching this code).

    Phase 3's AnthropicMGTIClient copies this function verbatim into
    src/llm/anthropic_mgti.py. If both adapters are ever unified, extract here.
    """
    logger.info("llm_call", extra=extra)
```

**4. Real `AzureOpenAIClient` class** — replace the existing stub body. Class docstring should note that the only differences vs the old `_call_azure_openai` are: (a) typed errors at the boundary, (b) `max_tokens` is now a per-call kwarg (was hardcoded 500/1000 in two duplicated places), (c) one structured log event per call.

The `__init__` MUST:
- Read endpoint/api_key/api_version from `src.llm.config.load_settings()` (Phase 1 infrastructure).
- Cache them as private attributes `self._endpoint`, self._api_key`, `self._api_version`.
- Call `_extract_model_from_endpoint(self._endpoint)` once and cache as `self._model`.
- Override `__repr__` to NOT include `self._api_key` — return a static string like `"AzureOpenAIClient()"` (OBS-03 regression guard from Phase 1's test).
- NOT raise on missing config — Phase 1 decision (CONTEXT.md "Already locked from Phase 1"): the no-op constructor pattern is preserved so the factory cache can store the instance. The HTTP-time check below catches missing config.

The `complete()` method MUST follow this exact structure:

```python
def complete(
    self,
    messages: list[dict],
    *,
    max_tokens: int = 500,
    temperature: float = 0.1,
    **kwargs: Any,
) -> str:
    # Pre-flight config check — embed provider-specific remediation in the
    # LLMConfigError message so the error translation seam (Plan 02) can pass
    # str(e) through as QueryError.message without hardcoding Azure text in
    # the compat layer (RESEARCH.md OQ-1: Phase-3-clean path).
    if not self._api_key:
        raise LLMConfigError(
            "Azure OpenAI API key not configured. "
            "Set the AZURE_OPENAI_API_KEY environment variable.",
            provider="azure_openai",
        )
    if not self._endpoint:
        raise LLMConfigError(
            "Azure OpenAI endpoint not configured. "
            "Set the AZURE_OPENAI_ENDPOINT environment variable.",
            provider="azure_openai",
        )

    headers = {
        "Content-Type": "application/json",
        "api-key": self._api_key,
    }
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    t0 = time.monotonic()
    extra: dict = {
        "llm_provider": "azure_openai",
        "llm_model": self._model,
        "llm_latency_ms": 0,
        "llm_outcome": "error",  # overwritten on success
        "llm_error_type": None,
        "llm_prompt_tokens": None,
        "llm_completion_tokens": None,
        "llm_correlation_id": None,  # Azure has no correlation ID; Phase 3 populates this
    }
    try:
        response = requests.post(
            f"{self._endpoint}?api-version={self._api_version}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {}) or {}
        extra["llm_prompt_tokens"] = usage.get("prompt_tokens")
        extra["llm_completion_tokens"] = usage.get("completion_tokens")
        extra["llm_outcome"] = "success"
        return text  # NO .strip() — call sites already strip; double-strip is idempotent but is not byte-identical to the old path

    except requests.exceptions.Timeout as e:
        extra["llm_error_type"] = "LLMTimeoutError"
        raise LLMTimeoutError(
            f"Azure OpenAI request timed out: {e}",
            provider="azure_openai",
        ) from e

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        extra["llm_error_type"] = (
            "LLMAuthError" if status in (401, 403)
            else "LLMTransientError" if status == 429 or (status is not None and 500 <= status < 600)
            else "LLMError"
        )
        if status in (401, 403):
            raise LLMAuthError(
                f"Azure OpenAI authentication failed (HTTP {status}): {e}",
                provider="azure_openai",
                status_code=status,
            ) from e
        if status == 429 or (status is not None and 500 <= status < 600):
            raise LLMTransientError(
                f"Azure OpenAI transient failure (HTTP {status}): {e}",
                provider="azure_openai",
                status_code=status,
            ) from e
        # Any other HTTP error falls through to the catch-all below
        raise LLMError(
            f"Azure OpenAI HTTP error (HTTP {status}): {e}",
            provider="azure_openai",
            status_code=status,
        ) from e

    except requests.exceptions.RequestException as e:
        # Connection errors, DNS, etc. — treat as transient.
        extra["llm_error_type"] = "LLMTransientError"
        raise LLMTransientError(
            f"Azure OpenAI request failed: {e}",
            provider="azure_openai",
        ) from e

    finally:
        extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
        _log_llm_call(extra)
```

Notes on this shape (each addresses a specific RESEARCH.md pitfall):

- **No `.strip()` in the adapter** — Pitfall 1. The call sites already `.strip()` the return value; the adapter returns the raw content unchanged so the parity test can assert string equality against the fixture's `content` field.
- **Token counts use `.get()` chains returning `None`** — Risk 3. Missing `usage` block does not raise.
- **`raise_for_status()` raises `HTTPError`** which carries the status code via `e.response.status_code`; we discriminate 401/403/429/5xx within the `except HTTPError` block. The order of `except` clauses (Timeout → HTTPError → RequestException) matters because `HTTPError` and `Timeout` are both `RequestException` subclasses.
- **`finally` block always logs** — success path overwrites `llm_outcome="success"` before the function returns; error paths set `llm_error_type` then `raise`, and the `finally` populates `llm_latency_ms` and emits the log event. This is the single source of OBS-02 events for Azure.
- **No correlation ID for Azure** — `llm_correlation_id` is always `None` in Phase 2. Phase 3's Anthropic adapter populates it from `X-Correlation-Id`. The field is in `extra` for shape-stability across providers.
- **`__repr__` override** — Phase 1's `test_no_api_keys_in_repr` (`tests/test_llm_seam.py` line 287) constructs `AzureOpenAIClient()` and asserts the sentinel `AZURE_SECRET_DO_NOT_LEAK_AAAA` is not in `repr()`. After this plan, the instance carries `self._api_key` — the default object repr does not include attributes (it shows `<src.llm.azure_openai.AzureOpenAIClient object at 0x...>`), but to be defensive and to match Phase 1's expectation that repr is intentionally lean, override `__repr__` to return `"AzureOpenAIClient()"`.
  </action>
  <verify>
Run from project root:

```
python -c "
import os
# Strip any real Azure env vars; we are testing the constructor + error paths.
for k in ('AZURE_OPENAI_API_KEY','AZURE_OPENAI_ENDPOINT','API_VERSION'):
    os.environ.pop(k, None)

# Step 1: construct without env — must NOT raise (Phase 1 locked decision).
from src.llm.azure_openai import AzureOpenAIClient, _extract_model_from_endpoint, _log_llm_call
client = AzureOpenAIClient()
assert repr(client) == 'AzureOpenAIClient()', f'unexpected repr: {repr(client)}'

# Step 2: complete() raises LLMConfigError with the exact remediation text Plan 02's compat layer expects.
from src.llm.errors import LLMConfigError
try:
    client.complete([{'role':'user','content':'hi'}])
    raise AssertionError('expected LLMConfigError for missing key')
except LLMConfigError as e:
    assert 'AZURE_OPENAI_API_KEY' in str(e), f'remediation text missing from LLMConfigError: {e}'
    assert e.provider == 'azure_openai', f'provider attr missing: {e.provider!r}'

# Step 3: _extract_model_from_endpoint behaviour.
url = 'https://my.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions'
assert _extract_model_from_endpoint(url) == 'gpt-4o-mini', f'extract failed: {_extract_model_from_endpoint(url)!r}'
assert _extract_model_from_endpoint('https://example.com/foo') == 'unknown'

# Step 4: With endpoint set but missing api key → still LLMConfigError, different message.
os.environ['AZURE_OPENAI_ENDPOINT'] = url
# Force the adapter to re-read settings (Phase 1 caches per-instance, so build a new one).
client2 = AzureOpenAIClient()
try:
    client2.complete([{'role':'user','content':'hi'}])
    raise AssertionError('expected LLMConfigError for missing key')
except LLMConfigError as e:
    assert 'AZURE_OPENAI_API_KEY' in str(e), f'remediation text missing: {e}'

# Step 5: With both set, mock requests.post and prove (a) the body shape, (b) successful extraction,
# (c) one log event with correct fields.
os.environ['AZURE_OPENAI_API_KEY'] = 'dummy-key-for-test'
client3 = AzureOpenAIClient()
from unittest.mock import patch, MagicMock
import logging
captured = []
class _H(logging.Handler):
    def emit(self, record): captured.append(record)
import src.utils as u
u.logger.addHandler(_H())
try:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        'choices':[{'message':{'content':'hello world'}}],
        'usage':{'prompt_tokens':10,'completion_tokens':5},
    }
    with patch('requests.post', return_value=mock_resp) as mp:
        out = client3.complete([{'role':'user','content':'hi'}], max_tokens=1000)
    assert out == 'hello world', f'extraction wrong: {out!r}'
    # Confirm body shape passed to requests.post
    kwargs = mp.call_args.kwargs
    assert kwargs['json']['max_tokens'] == 1000, f'max_tokens not honored: {kwargs[\"json\"]}'
    assert kwargs['json']['messages'] == [{'role':'user','content':'hi'}]
    # Confirm one log event with llm_call tag and correct extra fields
    llm_events = [r for r in captured if r.getMessage() == 'llm_call']
    assert len(llm_events) == 1, f'expected 1 llm_call event, got {len(llm_events)}'
    ev = llm_events[0]
    assert ev.llm_provider == 'azure_openai'
    assert ev.llm_model == 'gpt-4o-mini'
    assert ev.llm_outcome == 'success'
    assert ev.llm_error_type is None
    assert ev.llm_prompt_tokens == 10
    assert ev.llm_completion_tokens == 5
    assert isinstance(ev.llm_latency_ms, int) and ev.llm_latency_ms >= 0
    assert ev.llm_correlation_id is None  # Azure has no correlation ID in Phase 2
finally:
    for k in ('AZURE_OPENAI_API_KEY','AZURE_OPENAI_ENDPOINT'):
        os.environ.pop(k, None)
print('TASK 1 OK')
"
```

Must print `TASK 1 OK`. If logger record attributes are not directly accessible (depends on stdlib record protocol), the `extra={}` keys MUST become attributes via the standard `logging.Logger.makeRecord` codepath — this is guaranteed for any name not in the LogRecord's reserved set. The chosen prefix `llm_*` avoids collisions.
  </verify>
  <done>
- `src/llm/azure_openai.py` contains a working `AzureOpenAIClient.complete()` that POSTs to `{endpoint}?api-version={version}` with `api-key` header, returns the unstripped content string, and emits one `logger.info("llm_call", extra={...})` event per call (success or error).
- `_extract_model_from_endpoint()` and `_log_llm_call()` exist as module-level private helpers.
- Pre-flight check raises `LLMConfigError` with Azure-specific remediation text embedded (RESEARCH.md OQ-1) so the Plan 02 compat layer can pass `str(e)` through as `QueryError.message`.
- HTTP error mapping is correct: 401/403 → `LLMAuthError`; 429/5xx → `LLMTransientError`; `requests.Timeout` → `LLMTimeoutError`; connection errors → `LLMTransientError`.
- `repr(AzureOpenAIClient())` returns `"AzureOpenAIClient()"` (no key leak).
- Satisfies ADP-01 (parity-preserving extraction), ERR-02 (HTTP→typed-error mapping for Azure), OBS-02 (one structured event per call).
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement AzureOpenAIClient.classify_with_tool() with prompt-based JSON parsing (ADP-02)</name>
  <files>src/llm/azure_openai.py</files>
  <action>
In the same `src/llm/azure_openai.py` file, implement the `classify_with_tool()` method. Per ADP-02 (locked in CONTEXT.md / requirements), Azure uses **prompt-based JSON parsing** — not provider-side strict-tools — to preserve existing Azure behavior. The method builds a prompt from the `ToolSchema`, calls the adapter's own `complete()`, JSON-parses the result, validates against the tool's `input_schema` via `jsonschema.validate`, and returns a `ToolCall`.

Why this is in Phase 2 even though no call site uses it yet (RESEARCH.md OQ-4): ADP-02 is a Phase 2 requirement; the method must exist and be functional so the adapter is no longer a stub. The parity gate (Plan 04) does NOT need to compare `classify_with_tool` against a pre-refactor baseline (no existing baseline — Phase 1 had `NotImplementedError`); a unit test in Plan 04 covers the happy path + a malformed-JSON case.

Implementation:

```python
def classify_with_tool(
    self,
    messages: list[dict],
    tool: ToolSchema,
    *,
    tool_name: str,
    **kwargs: Any,
) -> ToolCall:
    """Prompt-based JSON classification for Azure (ADP-02).

    Phase 4 reserves provider-side strict-tools for the Anthropic adapter
    only. The Azure path stays on prompt + JSON parse to preserve existing
    behavior; this keeps the parity gate scoped to complete() alone.

    Builds a system-prompt addendum instructing the model to respond as
    JSON matching tool.input_schema, calls complete(), strips markdown
    code fences if present, json.loads(), validates via jsonschema, and
    returns a ToolCall.

    Raises:
        LLMSchemaError: response was not valid JSON, or did not match
            tool.input_schema.
    """
    import json

    import jsonschema

    # Append a strict JSON-mode instruction as a system message. Existing
    # CLASSIFICATION_PROMPT in query_router.py already instructs the model
    # to "Respond with JSON" — this is the same pattern, generalized.
    enriched = list(messages) + [
        {
            "role": "system",
            "content": (
                f"You are calling the tool `{tool.name}`. "
                f"Respond ONLY with a JSON object matching this schema:\n"
                f"{json.dumps(tool.input_schema)}\n"
                f"Do not include markdown code fences or commentary."
            ),
        }
    ]
    raw = self.complete(enriched, **kwargs)

    # Strip markdown code fences if the model included them anyway.
    content = raw.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMSchemaError(
            f"Azure OpenAI did not return valid JSON for tool {tool.name!r}: {e}",
            provider="azure_openai",
        ) from e

    try:
        jsonschema.validate(parsed, tool.input_schema)
    except jsonschema.ValidationError as e:
        raise LLMSchemaError(
            f"Azure OpenAI tool response failed schema validation for {tool.name!r}: {e.message}",
            provider="azure_openai",
        ) from e

    return ToolCall(
        tool_name=tool_name,
        input=parsed,
        raw_response={"content": raw},
    )
```

Notes:
- `import json` and `import jsonschema` are local to the method (not module-level) because `jsonschema` is only used in this codepath and is already a project dependency (CFG-06 — `jsonschema>=4.26.0,<5` is in `requirements.txt`).
- The method DOES NOT call `validate_config` — Phase 1 decision: validation is explicit at app boot, not per-call.
- `raw_response` is set to `{"content": raw}` (debug-only; `field(repr=False)` on `ToolCall` ensures it stays out of `repr()`).
- The enriched system message is added at the END of the existing messages list — the Azure model honors the most-recent system instruction for tool-style output. This matches the existing prompt-engineering pattern in `query_router.py` CLASSIFICATION_PROMPT and `sql_generator.py` SYSTEM_PROMPT.
  </action>
  <verify>
Run from project root:

```
python -c "
import os
os.environ['AZURE_OPENAI_API_KEY'] = 'dummy-key'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://x.openai.azure.com/openai/deployments/test/chat/completions'

from src.llm.azure_openai import AzureOpenAIClient
from src.llm.types import ToolSchema
from src.llm.errors import LLMSchemaError
from unittest.mock import patch, MagicMock

# Tool with a simple input schema (matches the kind of shape Phase 4 will derive from ClassificationResultV1)
tool = ToolSchema(
    name='classify_intent',
    description='Classify a query',
    input_schema={
        'type': 'object',
        'properties': {
            'intent': {'type': 'string', 'enum': ['structured', 'semantic', 'hybrid']},
            'confidence': {'type': 'number'},
        },
        'required': ['intent', 'confidence'],
    },
)

client = AzureOpenAIClient()

# Happy path: model returns valid JSON
mock_resp = MagicMock()
mock_resp.status_code = 200
mock_resp.raise_for_status = lambda: None
mock_resp.json.return_value = {
    'choices':[{'message':{'content':'{\"intent\":\"structured\",\"confidence\":0.9}'}}],
    'usage':{'prompt_tokens':50,'completion_tokens':10},
}
with patch('requests.post', return_value=mock_resp):
    tc = client.classify_with_tool([{'role':'user','content':'count incidents'}], tool, tool_name='classify_intent')
assert tc.tool_name == 'classify_intent', f'tool_name wrong: {tc.tool_name!r}'
assert tc.input == {'intent':'structured','confidence':0.9}, f'input wrong: {tc.input!r}'
# raw_response is debug-only and excluded from repr (ToolCall.raw_response repr=False)
assert 'structured' not in repr(tc) or 'raw_response' not in repr(tc), f'raw_response leaked: {repr(tc)}'

# Markdown code fence: model wraps response — adapter must strip the fences.
mock_resp.json.return_value = {
    'choices':[{'message':{'content':'\`\`\`json\\n{\"intent\":\"hybrid\",\"confidence\":0.7}\\n\`\`\`'}}],
    'usage':{},
}
with patch('requests.post', return_value=mock_resp):
    tc = client.classify_with_tool([{'role':'user','content':'mixed'}], tool, tool_name='classify_intent')
assert tc.input == {'intent':'hybrid','confidence':0.7}, f'fence stripping failed: {tc.input!r}'

# Malformed JSON → LLMSchemaError
mock_resp.json.return_value = {
    'choices':[{'message':{'content':'this is not json'}}],
    'usage':{},
}
with patch('requests.post', return_value=mock_resp):
    try:
        client.classify_with_tool([{'role':'user','content':'x'}], tool, tool_name='classify_intent')
        raise AssertionError('expected LLMSchemaError')
    except LLMSchemaError as e:
        assert 'classify_intent' in str(e), f'schema error msg missing tool name: {e}'

# Valid JSON but schema mismatch → LLMSchemaError
mock_resp.json.return_value = {
    'choices':[{'message':{'content':'{\"intent\":\"WRONG_VALUE\",\"confidence\":0.5}'}}],
    'usage':{},
}
with patch('requests.post', return_value=mock_resp):
    try:
        client.classify_with_tool([{'role':'user','content':'x'}], tool, tool_name='classify_intent')
        raise AssertionError('expected LLMSchemaError for schema violation')
    except LLMSchemaError:
        pass
print('TASK 2 OK')
"
```

Must print `TASK 2 OK`. This proves classify_with_tool handles the happy path, markdown fence stripping, JSON parse failures, and schema validation failures — and raises `LLMSchemaError` (not a generic `Exception` or `LLMError`) for both failure modes.
  </verify>
  <done>
- `AzureOpenAIClient.classify_with_tool()` builds an enriched message list with a JSON-mode system instruction, calls `self.complete()`, strips markdown fences, `json.loads()` the result, validates against `tool.input_schema` with `jsonschema.validate`, and returns a `ToolCall`.
- Malformed JSON and schema-validation failures both raise `LLMSchemaError` with the tool name embedded in the message.
- `ToolCall.raw_response` carries the raw `complete()` return value for debugging; `repr(ToolCall)` does NOT leak this (ABS-03 / Phase 1 `field(repr=False)`).
- Satisfies ADP-02.
- No call site changes in this plan — Plan 03 rewrites the three call sites.
  </done>
</task>

</tasks>

<verification>
After both tasks, run from project root:

```
python -c "
import os
# Confirm the adapter is no longer a stub.
from src.llm.azure_openai import AzureOpenAIClient
from src.llm.base import LLMClient
import abc, inspect

# Class still satisfies the ABC
assert issubclass(AzureOpenAIClient, LLMClient)
assert AzureOpenAIClient.__abstractmethods__ == frozenset(), 'AzureOpenAIClient is still abstract'

# Methods are no longer NotImplementedError stubs
src_complete = inspect.getsource(AzureOpenAIClient.complete)
src_classify = inspect.getsource(AzureOpenAIClient.classify_with_tool)
assert 'NotImplementedError' not in src_complete, 'complete() still a stub'
assert 'NotImplementedError' not in src_classify, 'classify_with_tool() still a stub'

# Required signals are in the source
assert 'requests.post' in src_complete
assert 'logger.info' in inspect.getsource(__import__('src.llm.azure_openai', fromlist=['_log_llm_call'])._log_llm_call) or 'logger.info' in src_complete
assert 'LLMTimeoutError' in src_complete
assert 'LLMAuthError' in src_complete
assert 'LLMTransientError' in src_complete
assert 'jsonschema.validate' in src_classify
print('PLAN 02-01 VERIFICATION OK')
"
```

Must print `PLAN 02-01 VERIFICATION OK`.

Also confirm Phase 1's acceptance gate (`tests/test_llm_seam.py`) still passes — the adapter overhaul must not break it:

```
python -m pytest tests/test_llm_seam.py -v
```

All 6 Phase 1 tests must still pass. If `test_no_api_keys_in_repr` fails, the `__repr__` override is missing or incorrect.

LOCKED files (`src/query_router.py`, `src/sql_generator.py`, `app.py`, top-level `config.py`) MUST NOT be modified by this plan:

```
git diff --name-only HEAD src/query_router.py src/sql_generator.py app.py config.py 2>&1 | head
```

Must produce no output (no diff against HEAD for those files).
</verification>

<success_criteria>
- `src/llm/azure_openai.py` is no longer a stub; `AzureOpenAIClient.complete()` and `.classify_with_tool()` are functional.
- `complete()` extracts `response.json()["choices"][0]["message"]["content"]` and returns it WITHOUT `.strip()` (Pitfall 1 — call sites strip; double-strip would break byte-identity).
- One `logger.info("llm_call", extra={...})` event is emitted per `complete()` call (success or error path) — verified by adding a handler to `src.utils.logger` and counting records.
- Typed errors raised at HTTP boundary: 401/403 → `LLMAuthError`; 429/5xx → `LLMTransientError`; `requests.Timeout` → `LLMTimeoutError`; missing config → `LLMConfigError` with Azure-specific remediation text embedded.
- `classify_with_tool()` returns a `ToolCall` for valid JSON-mode responses; raises `LLMSchemaError` for malformed JSON or schema violations.
- `repr(AzureOpenAIClient())` does NOT include the API key (Phase 1 OBS-03 test still passes).
- Phase 1 acceptance gate (`tests/test_llm_seam.py`) still runs green (6/6 passing).
- LOCKED files (`src/query_router.py`, `src/sql_generator.py`, `app.py`, `config.py` at project root) NOT modified by this plan — Plan 03 owns those.

Maps to: Success criterion #4 (full — adapter emits the log event); #3 (partial — adapter raises typed errors that Plan 02's compat layer translates); ADP-01 (parity-preserving extraction), ADP-02 (prompt-based classify_with_tool), ERR-02 (Azure subset), OBS-02.
</success_criteria>

<output>
After completion, create `.planning/phases/02-azure-extraction-parity-gate/02-01-SUMMARY.md` documenting:
- Final line count of `src/llm/azure_openai.py` (stub was 47 lines; real implementation should be ~150-200 lines).
- Confirmation that `requests.post`, `logger.info("llm_call", ...)`, all four typed errors (`LLMConfigError`, `LLMAuthError`, `LLMTransientError`, `LLMTimeoutError`), and `jsonschema.validate` are all present in the implementation.
- Confirmation that the adapter does NOT call `.strip()` on its return value (Pitfall 1 guard).
- Confirmation that Phase 1's `tests/test_llm_seam.py` still passes (6/6).
- Confirmation that LOCKED files (`src/query_router.py`, `src/sql_generator.py`, `app.py`, `config.py`) have ZERO diff against HEAD for this plan.
- A line-by-line summary of which Phase 2 success criteria each part of the implementation contributes to.
</output>
</content>
</invoke>