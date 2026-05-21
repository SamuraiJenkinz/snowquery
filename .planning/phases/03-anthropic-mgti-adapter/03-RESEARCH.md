# Phase 3: Anthropic MGTI Adapter — Research

**Researched:** 2026-05-21
**Domain:** Anthropic MGTI Apigee proxy adapter, codebase wiring, test gate structure
**Confidence:** HIGH (all findings from direct codebase reads and the mgti-anthropic-integration skill)

---

## Summary

Phase 3 replaces the Phase 1 `AnthropicMGTIClient` stub (27 lines, raises `NotImplementedError`) with a full implementation. The wiring infrastructure is almost entirely pre-built: `src/llm/__init__.py` already registers `"anthropic_mgti": "src.llm.anthropic_mgti:AnthropicMGTIClient"`, `src/llm/config.py` already declares and loads all 8 Anthropic env vars into `LLMSettings`, and `_compat.py` already handles the `LLMAuthError` hardcoding issue (noted and left for Phase 3 to decide). The only files that need modification are `src/llm/anthropic_mgti.py` (full rewrite of the stub) and `.env.example` (add 9 vars). The test gate `tests/test_phase3_adapter.py` is a net-new file following the Phase 1/2 pattern.

The MGTI proxy contract is fully documented in the mgti-anthropic-integration skill: endpoint is `POST {base_url}/model/{model}/messages` (the `/messages` suffix is mandatory, the original spec PDF omitted it), auth is `X-Api-Key` (not `Authorization: Bearer`), `anthropic_version: "bedrock-2023-05-31"` is required in the body, and error envelopes are `{"error": {"title", "detail", "status"}}` — not the native Anthropic SDK shape.

**Primary recommendation:** Write `anthropic_mgti.py` by cloning the structure of `azure_openai.py` line-for-line, then substituting Anthropic-specific request construction, response parsing, and error mapping. The `_log_llm_call` function must be copied verbatim per the Phase 2 decision.

---

## Codebase Touchpoints

### Files to MODIFY

| File | Change | Notes |
|------|--------|-------|
| `src/llm/anthropic_mgti.py` | Full rewrite (stub → real implementation) | Currently 47 lines; Phase 1 stub raises `NotImplementedError` |
| `.env.example` | Add 9 Anthropic vars + `LLM_PROVIDER_DEFAULT` | Currently only has 4 Azure vars + LOG_LEVEL |

### Files to READ (NOT modify) — planner must reference these

| File | What the planner needs from it |
|------|-------------------------------|
| `src/llm/azure_openai.py` | `_log_llm_call` signature to copy verbatim; `complete()` try/except/finally structure to mirror |
| `src/llm/config.py` | All 8 Anthropic fields already in `LLMSettings` and `load_settings()` — adapter uses `load_settings()` directly |
| `src/llm/__init__.py` | Factory already registers `"anthropic_mgti"` — no changes needed |
| `src/llm/errors.py` | All 6 typed error classes already defined — no changes needed |
| `src/llm/_compat.py` | `LLMAuthError` branch hardcodes Azure text — Phase 3 must decide dispatch strategy |
| `tests/test_phase2_parity.py` | Pattern to replicate for test gate structure (autouse fixtures, cache clear, env strip) |

### Files NOT touched by Phase 3

`src/llm/base.py`, `src/llm/types.py`, `src/query_router.py`, `src/sql_generator.py`, `app.py`, `config.py` — Phase 3 does not modify call sites; they already use `get_llm()` generically.

---

## Existing Patterns to Replicate

### `_log_llm_call` — copy verbatim from `azure_openai.py:52-64`

```python
# src/llm/azure_openai.py lines 52-64 — copy verbatim into anthropic_mgti.py
def _log_llm_call(extra: dict) -> None:
    """Emit one structured log event per LLM call (OBS-02).
    ...
    Phase 3's AnthropicMGTIClient copies this function verbatim into
    src/llm/anthropic_mgti.py. If both adapters are ever unified, extract here.
    """
    logger.info("llm_call", extra=extra)
```

The `logger` import is `from src.utils import logger` — same import as in `azure_openai.py`.

### `complete()` try/except/finally skeleton — mirror from `azure_openai.py:90-212`

The Azure adapter's `complete()` uses this structure (Anthropic adapter replicates with adapted field names):

```python
t0 = time.monotonic()
extra: dict = {
    "llm_provider": "anthropic_mgti",   # changed from "azure_openai"
    "llm_model": self._model,
    "llm_latency_ms": 0,
    "llm_outcome": "error",             # overwritten on success
    "llm_error_type": None,
    "llm_prompt_tokens": None,          # from response usage.input_tokens (normalized name)
    "llm_completion_tokens": None,      # from response usage.output_tokens (normalized name)
    "llm_correlation_id": None,         # populated per-call from UUID
}
try:
    response = requests.post(...)
    # ... parse response ...
    return text
except requests.exceptions.Timeout as e:
    ...
except requests.exceptions.HTTPError as e:
    ...
except requests.exceptions.RequestException as e:
    ...
finally:
    extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
    _log_llm_call(extra)
```

Key difference from Azure: Anthropic adapter does NOT call `response.raise_for_status()` and let `HTTPError` fire. Instead it checks `response.status_code` directly (because the 4xx/5xx dispatching must examine the MGTI error envelope to extract `title`/`detail`, which happens before raising the typed error).

### `__init__` — no-op pattern plus model validation

```python
# Azure adapter __init__ pattern (azure_openai.py:76-84) — adapt for Anthropic
def __init__(self) -> None:
    settings = load_settings()
    self._base_url: str = settings.anthropic_base_url
    self._api_key: str = field(default="", repr=False)  # settings.anthropic_api_key
    self._model: str = settings.anthropic_model
    self._version: str = settings.anthropic_version
    self._max_tokens: int = settings.anthropic_max_tokens
    self._temperature: float = settings.anthropic_temperature
    self._timeout_s: int = settings.anthropic_timeout_s
    self._tools_supported: bool = settings.anthropic_tools_supported
    # SC #2: model name validation — raises LLMConfigError at construction time
    if self._model and not self._model.startswith("eu.anthropic.claude-"):
        raise LLMConfigError(
            "Anthropic model must start with 'eu.anthropic.claude-' "
            "(Claude 4.5+ on EU Bedrock). Got: {self._model!r}",
            provider="anthropic_mgti",
        )
```

Note: The Azure adapter does NOT validate at construction (no-op pattern). Phase 3 breaks from that pattern for model name validation only — the CONTEXT.md SC #2 says "Constructing `AnthropicMGTIClient` with a model name not starting `eu.anthropic.claude-` raises `LLMConfigError`". An empty model (no env var set) should NOT raise at construction (pre-flight check in `complete()` handles that, matching the Azure precedent).

### Test autouse fixtures — copy from `test_phase2_parity.py:50-82`

```python
@pytest.fixture(autouse=True)
def _clear_factory_cache():
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()

@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch):
    for name in (
        "LLM_PROVIDER_DEFAULT",
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "API_VERSION",
        "ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
        "ANTHROPIC_VERSION", "ANTHROPIC_MAX_TOKENS", "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_TIMEOUT_S", "ANTHROPIC_TOOLS_SUPPORTED",
    ):
        monkeypatch.delenv(name, raising=False)

@pytest.fixture
def anthropic_env(monkeypatch):
    """Set realistic Anthropic env so AnthropicMGTIClient constructs without error."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ANTHROPIC_MODEL", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
```

### Log event field naming — normalized to Azure names

```python
# CORRECT — normalized field names (from CONTEXT.md)
extra["llm_prompt_tokens"] = usage.get("input_tokens")      # Anthropic calls this input_tokens
extra["llm_completion_tokens"] = usage.get("output_tokens") # Anthropic calls this output_tokens
extra["llm_correlation_id"] = correlation_id                 # populated (Azure had None)

# WRONG — do NOT use Anthropic-native names here
extra["input_tokens"] = ...    # breaks cross-provider log grep
extra["output_tokens"] = ...   # breaks cross-provider log grep
```

---

## MGTI Proxy Contract

Source: mgti-anthropic-integration skill (production-validated, kbroles 2026-05-11/12).

### Endpoint

```
POST {ANTHROPIC_BASE_URL}/model/{model}/messages
```

`ANTHROPIC_BASE_URL` is the full base including path prefix, e.g.:
- Non-prod: `https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`
- Prod: `https://int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`

The adapter appends `/model/{model}/messages` to whatever value is in env. The URL builder is `f"{self._base_url.rstrip('/')}/model/{self._model}/messages"`.

### Required Headers

```python
headers = {
    "Content-Type": "application/json",
    "X-Api-Key": self._api_key,           # NOT "Authorization: Bearer", NOT "api-key"
    "X-Correlation-Id": correlation_id,   # fresh uuid.uuid4() per call
}
```

### Request Body Shape

```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "system": "<concatenated system messages>",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 1024,
  "temperature": 0.0
}
```

Rules:
- `system` is top-level, NOT a `{"role": "system", ...}` message in `messages[]`
- `system` key OMITTED entirely when no system messages present (not sent as `""`)
- `max_tokens` is always required (no Anthropic API default)
- `anthropic_version` is always required — Bedrock-specific constant, not a date header
- `temperature`/`top_p`/`top_k` OMITTED for models matching `eu.anthropic.claude-opus-4-7*`
- For other models: `temperature` sent, `top_p`/`top_k` only if explicitly passed

### Successful Response Shape

```json
{
  "id": "msg_013Zva2CMHLNnXjJJKqJ2EF",
  "type": "message",
  "role": "assistant",
  "model": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "content": [
    {"type": "text", "text": "The capital of France is Paris."}
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {"input_tokens": 25, "output_tokens": 12}
}
```

### Guardrail Response (HTTP 200, empty content)

```json
{
  "id": "msg_...",
  "content": [],
  "stop_reason": "guardrail_intervened",
  "usage": {"input_tokens": 18, "output_tokens": 0}
}
```

Note: `usage` is still present even on guardrail responses. Log `prompt_tokens` and `completion_tokens` before raising `LLMGuardrailError`.

### Error Envelope (HTTP 4xx/5xx)

```json
{
  "error": {
    "title": "Model not supported",
    "detail": "The modelName must be a Claude 4.5+ model with the eu. prefix.",
    "status": 404
  }
}
```

This is the MGTI proxy envelope — NOT the native Anthropic SDK shape (`{"type": "error", "error": {"type", "message"}}`). Error extraction:

```python
try:
    err = response.json().get("error", {})
    title = err.get("title", "unknown")
    detail = err.get("detail", response.text[:200])
    msg = f"{title}: {detail}"
except (ValueError, AttributeError):
    msg = response.text[:200]
```

---

## `_compat.py` — LLMAuthError Branch Decision

**Current state** (`_compat.py:78-89`): `LLMAuthError` hardcodes Azure remediation text:
```python
raise QueryError(
    "Azure OpenAI API key not configured",
    "Set the AZURE_OPENAI_API_KEY environment variable.",
) from e
```

**Phase 3 decision required**: The CONTEXT.md notes this and says "Phase 3 must decide: dispatch on `e.provider`, or leave Phase 5 to fix."

**Research finding**: The `LLMError` base class (and all subclasses) already carries `self.provider` (set at raise time). So dispatching is straightforward:

```python
except LLMAuthError as e:
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError(
            "Anthropic API key not configured or not authorised",
            "Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.",
        ) from e
    raise QueryError(
        "Azure OpenAI API key not configured",
        "Set the AZURE_OPENAI_API_KEY environment variable.",
    ) from e
```

The planner must decide whether to do this in Phase 3 or defer. The test gate SC #3 for Phase 2 (in `test_phase2_parity.py:354-363`) checks the exact Azure text — that test MUST still pass. The Phase 3 test gate can check Anthropic-specific text when `anthropic_mgti` is the provider.

**Recommendation**: Dispatch on `e.provider` in Phase 3. It's a 5-line change to `_compat.py`, it makes the file live up to its own comment ("Phase 3 may revisit this branch"), and it unblocks writing a meaningful SC #3 test for Anthropic auth errors.

---

## `.env.example` — Required Additions

Current `.env.example` (4 vars):
```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
API_VERSION=2023-05-15
LOG_LEVEL=INFO
```

Phase 3 adds 9 vars. The SC #4 test reads `.env.example` and asserts all 9 are present with non-empty default-value comments:

```bash
# Anthropic MGTI (Claude 4.5+ via MMC Apigee gateway)
# Provider selector — set to anthropic_mgti to route to Claude
LLM_PROVIDER_DEFAULT=azure_openai

# Full URL up to /v1. Adapter appends /model/{name}/messages.
# Prod: https://int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1
# Non-prod: https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1
ANTHROPIC_BASE_URL=https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1

# Issued via Hubble (https://hubble.mmc.com/apps) after coreapi-infrastructure merge
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Must be Claude 4.5+ with eu. prefix (EU Bedrock region)
ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0

# Bedrock-required constant — do not change
ANTHROPIC_VERSION=bedrock-2023-05-31

# Max tokens per response (required by Anthropic API, unlike OpenAI)
ANTHROPIC_MAX_TOKENS=1024

# Sampling temperature (omitted automatically for opus-4-7 models)
ANTHROPIC_TEMPERATURE=0.0

# HTTP timeout in seconds
ANTHROPIC_TIMEOUT_S=30

# Set to false if proxy regresses on tools support (escape hatch for Phase 4)
ANTHROPIC_TOOLS_SUPPORTED=true
```

---

## SC #5 Startup Logging — Where to Wire It

**What SC #5 requires**: "App startup logs the configured base URL for each loadable provider exactly once."

**Current state**: `app.py` has no provider startup logging. `init_session_state()` (`app.py:361`) is the earliest app lifecycle hook, but it's inside a Streamlit session. The `get_llm()` factory constructs the adapter on first call — a good place to log but would require modifying `__init__.py`.

**Options for implementation** (planner chooses):

1. **Log in `AnthropicMGTIClient.__init__`** — mirrors what will likely be Phase 2's Azure adapter. Log: `logger.info("llm_provider_loaded", extra={"provider": "anthropic_mgti", "base_url": self._base_url})`. The test patches `logger` before constructing via `get_llm("anthropic_mgti")` and asserts one log event.

2. **Log in `get_llm()` factory** — single place; logs for every provider on first construction. Requires modifying `__init__.py`.

3. **Log in `AzureOpenAIClient.__init__`** and `AnthropicMGTIClient.__init__`** — symmetric, no `__init__.py` change. This is the path of least resistance. Each adapter logs once at construction; the factory cache ensures construction happens exactly once per provider.

**Research finding**: The test gate must verify "exactly once per loadable provider" — option 3 (log in each `__init__`) is easiest to test because constructing `get_llm("anthropic_mgti")` twice in a test still only logs once (cache hit on second call). Option 1 and 3 are the same thing. Option 2 needs `__init__.py` edit.

The test for SC #5 on "no tool wrapping" can be verified by inspecting `inspect.getsource(generate_sql)` and `inspect.getsource(generate_executive_summary)` for absence of `classify_with_tool` — same pattern as Phase 2's `test_call_azure_openai_eliminated`.

---

## Pitfalls Beyond CONTEXT.md

These are implementation-level gotchas that affect how tasks should be decomposed or guarded:

### Pitfall 1: `response.raise_for_status()` pattern from Azure does not port cleanly

`azure_openai.py` calls `response.raise_for_status()` and catches `requests.exceptions.HTTPError`. For Anthropic, the error body must be read BEFORE raising, to extract `title`/`detail` from the MGTI envelope. If the adapter also calls `raise_for_status()`, the response body is still accessible via `e.response`, but the code is harder to read. Better pattern (per skill): check `if not response.ok:` after the `requests.post`, read the JSON body in the error branch, raise the appropriate typed error directly. No `raise_for_status()` needed.

### Pitfall 2: Model validation raises at `__init__` but only when `self._model` is non-empty

The no-op pattern from Phase 1 means `complete()` still needs a pre-flight check for empty `self._base_url`, `self._api_key`, and `self._model` (the missing-env-var case, which is detected at HTTP time in Azure). But SC #2 says a non-eu-prefixed model raises at construction. The test fixture (`anthropic_env`) sets a valid model, so construction succeeds. A separate test with a bad model (no env fixtures for model) constructs `AnthropicMGTIClient` directly with `ANTHROPIC_MODEL` set to a bad value.

**Guard**: Empty model must NOT raise at `__init__` (stays consistent with no-op pattern). Non-empty invalid model MUST raise at `__init__`. The distinction: `if self._model and not self._model.startswith("eu.anthropic.claude-"):`.

### Pitfall 3: System message extraction from multi-message list

The `complete()` method receives `messages: list[dict]` where some entries may have `role == "system"`. The extraction must:
1. Filter ALL system messages (not just the first)
2. Concatenate their `content` strings with `"\n\n"`
3. Set the result as the top-level `system` body field
4. Pass remaining messages as the `messages` body field

The bug-prone case: what if `content` is a list (structured content) rather than a string? The CONTEXT.md decision is to concatenate `content` strings — the adapter should guard with `str(m["content"])` if the field could be non-string. For Phase 3 text-mode only, a simple `isinstance(m["content"], str)` check is sufficient; non-string system content → skip or raise `LLMSchemaError` at the caller's boundary.

### Pitfall 4: The `stop_reason` check must happen BEFORE the content emptiness check

The flow must be:
1. HTTP error? → typed error (401/403/429/5xx)
2. `stop_reason == "guardrail_intervened"`? → `LLMGuardrailError` (content IS empty here — don't check content first)
3. Content empty (and not guardrail)? → `LLMSchemaError`
4. No text blocks in content? → `LLMSchemaError`
5. `stop_reason == "tool_use"` reaching here? → `LLMSchemaError`
6. Unknown `stop_reason`? → `LLMSchemaError`
7. `stop_reason == "max_tokens"`? → success with `outcome="truncated"` in log
8. `stop_reason in ("end_turn", "stop_sequence")`? → success

If content-emptiness check comes before guardrail check, a guardrail response (which always has empty content) triggers `LLMSchemaError` instead of `LLMGuardrailError` — breaking SC #3.

### Pitfall 5: `X-Correlation-Id` must be generated BEFORE the `try` block

The correlation ID is logged in `extra["llm_correlation_id"]` in the `finally` block. Generate it once before entering the try block so it's available in the log even if the `requests.post` call itself raises immediately:

```python
correlation_id = str(uuid.uuid4())
extra["llm_correlation_id"] = correlation_id
t0 = time.monotonic()
try:
    response = requests.post(..., headers={"X-Correlation-Id": correlation_id, ...})
```

### Pitfall 6: `_compat.py` `LLMTimeoutError` and `LLMTransientError` log "Azure" in message

Current `_compat.py:90-93`:
```python
except LLMTimeoutError as e:
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
except LLMTransientError as e:
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
```

These hardcode "Azure OpenAI API call failed" — an Anthropic timeout will show this message to the user. The CONTEXT.md does not call this out. The planner must decide whether Phase 3 fixes the Timeout/Transient messages too (provider-dispatch similar to AuthError fix), or whether to leave it for Phase 5. It does NOT break any current test since no test checks the exact message for these two error types against Anthropic.

### Pitfall 7: `classify_with_tool` stub must remain — do NOT implement it

The Phase 1 stub raises `NotImplementedError("AnthropicMGTIClient.classify_with_tool is implemented in Phase 4")`. Phase 3 only implements `complete()`. The stub stays unchanged; Phase 4 wires tools.

---

## Config Layer — No Changes Required

`src/llm/config.py` already has complete Anthropic support:

```python
# LLMSettings — all fields already declared (config.py:39-48)
anthropic_base_url: str = ""
anthropic_api_key: str = field(default="", repr=False)  # excluded from repr (OBS-03)
anthropic_model: str = ""
anthropic_version: str = "bedrock-2023-05-31"
anthropic_max_tokens: int = 1024
anthropic_temperature: float = 0.0
anthropic_timeout_s: int = 30
anthropic_tools_supported: bool = True

# _REQUIRED_VARS — anthropic_mgti already registered (config.py:58-63)
"anthropic_mgti": (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
),
```

`load_settings()` already reads all 8 Anthropic env vars with correct types (`_int`, `_float`, `_bool` helpers). Phase 3 adapter calls `load_settings()` and reads from the returned `LLMSettings` — no env var reading in the adapter itself.

---

## Factory Registration — No Changes Required

`src/llm/__init__.py:54-57`:
```python
_REGISTRY: dict[str, str] = {
    "azure_openai": "src.llm.azure_openai:AzureOpenAIClient",
    "anthropic_mgti": "src.llm.anthropic_mgti:AnthropicMGTIClient",
}
```

`get_llm("anthropic_mgti")` already works end-to-end via lazy import. Phase 3 only needs to fill in the implementation; the factory plumbing is complete.

---

## Test Gate Structure — `tests/test_phase3_adapter.py`

Pattern from `test_phase2_parity.py`. Phase 3 gate uses `requests.post` patching (Level A), inline Python dicts as response bodies (no fixture files).

### Test Coverage Map (18 Phase 1+2 tests + Phase 3 gate)

| SC | What to Test | Patch Target | Assert |
|----|-------------|-------------|--------|
| SC #1 | URL construction | `requests.post` | `call_args` URL ends with `/model/{model}/messages` |
| SC #1 | Header presence | `requests.post` | `call_args` headers contain `X-Api-Key`, `Content-Type`, `X-Correlation-Id` |
| SC #1 | Fresh UUID per call | `requests.post` (called twice) | two `X-Correlation-Id` values are different |
| SC #2 | Non-eu model at construction | set env `ANTHROPIC_MODEL=gpt-4o` | raises `LLMConfigError` |
| SC #2 | opus-4-7 omits sampling params | `requests.post` | `call_args.kwargs["json"]` lacks `temperature`, `top_p`, `top_k` |
| SC #3 | 401 → `LLMAuthError` | mock 401 response | `pytest.raises(LLMAuthError)` |
| SC #3 | 403 → `LLMAuthError` | mock 403 response | `pytest.raises(LLMAuthError)` |
| SC #3 | 429 → `LLMTransientError` | mock 429 response | `pytest.raises(LLMTransientError)` |
| SC #3 | 503 → `LLMTransientError` | mock 503 response | `pytest.raises(LLMTransientError)` |
| SC #3 | `requests.Timeout` → `LLMTimeoutError` | `side_effect=requests.Timeout` | `pytest.raises(LLMTimeoutError)` |
| SC #3 | `stop_reason=guardrail_intervened` → `LLMGuardrailError` | 200 + empty content + guardrail stop_reason | `pytest.raises(LLMGuardrailError)` |
| SC #3 | HTTP 200 + empty content (non-guardrail) → `LLMSchemaError` | 200 + empty content + `stop_reason=end_turn` | `pytest.raises(LLMSchemaError)` |
| SC #4 | `.env.example` has all 9 vars | read file | assert each var present |
| SC #5 | Startup log per provider | mock logger + `get_llm("anthropic_mgti")` | one `llm_provider_loaded` event with `base_url` |
| SC #5 | No tool wrapping at call sites | `inspect.getsource` | `classify_with_tool` absent from `generate_sql` and `generate_executive_summary` source |

### Mock Response Builder Pattern (inline, no fixture files)

```python
def _make_anthropic_response(
    text: str = "Hello.",
    stop_reason: str = "end_turn",
    input_tokens: int = 25,
    output_tokens: int = 10,
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.ok = True
    resp.json.return_value = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "content": [{"type": "text", "text": text}] if text else [],
        "stop_reason": stop_reason,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    return resp

def _make_error_response(status_code: int, title: str = "Error", detail: str = "detail") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = False
    resp.json.return_value = {"error": {"title": title, "detail": detail, "status": status_code}}
    resp.text = f"{title}: {detail}"
    return resp
```

---

## Open Questions for the Planner

### OQ-1: Startup log — which lifecycle hook?

The CONTEXT.md says "App startup logs the configured base URL for each loadable provider exactly once." The planner must decide whether this log fires in each adapter's `__init__` (simple, already tested by the cache-idempotence behavior) or in `get_llm()` (requires `__init__.py` change). Recommendation: adapter `__init__` — no additional file to modify, consistent with where the adapter knows its own `base_url`.

### OQ-2: `_compat.py` Timeout/Transient message "Azure OpenAI API call failed"

These messages will appear for Anthropic timeouts too. Phase 3 can either:
- Leave it (no SC checks these exact strings for Anthropic; `str(e)` in the `details` field will show the Anthropic error)
- Dispatch like `LLMAuthError` (4 more lines)

The planner should decide based on whether the Phase 3 test gate asserts Anthropic-specific message text for these paths. If the test only checks the error TYPE (not message content), leaving it is safe for Phase 3.

### OQ-3: Correlation echo observation

CONTEXT.md says Phase 3 observes whether MGTI echoes `X-Correlation-Id` in response headers and documents in the commit message. This requires a manual smoke test or a `tests/manual/observe_correlation_echo.py` script. The planner should include a task for this observation step — it's not captured by the mocked acceptance gate.

---

## Sources

### Primary (HIGH confidence)

- `src/llm/azure_openai.py` — direct read; `_log_llm_call` signature, `complete()` structure, `extra` dict field names
- `src/llm/__init__.py` — direct read; factory registry already has `anthropic_mgti`
- `src/llm/config.py` — direct read; all 8 Anthropic fields declared and loaded
- `src/llm/_compat.py` — direct read; `LLMAuthError` hardcoded Azure text confirmed
- `src/llm/anthropic_mgti.py` — direct read; current stub is 47 lines, raises `NotImplementedError`
- `src/llm/errors.py` — direct read; all 6 error classes confirmed with `provider` attr
- `tests/test_phase2_parity.py` — direct read; autouse fixture pattern confirmed
- `.env.example` — direct read; currently 4 vars, needs 9 Anthropic additions
- `mgti-anthropic-integration/SKILL.md` — complete skill read; proxy contract, URL shape, error envelope, pitfalls (production-validated 2026-05-12)

### Secondary (MEDIUM confidence)

- `src/utils.py` — direct read; `logger` is a `logging.Logger` named `"snow_query"` with plain-text StreamHandler
- `config.py` (root) — direct read; calls `load_dotenv()` at import time; `src/llm/config.py` relies on this having already fired

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all imports already in requirements (`requests`, `uuid` stdlib)
- Architecture: HIGH — codebase directly inspected; no surprises
- MGTI proxy contract: HIGH — production-validated skill
- Pitfalls: HIGH — derived from direct code reading plus skill pitfall list
- Test gate pattern: HIGH — Phase 2 gate read directly

**Research date:** 2026-05-21
**Valid until:** Stable — proxy contract and codebase locked for Phase 3
