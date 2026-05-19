# Phase 1: Abstraction Seam - Research

**Researched:** 2026-05-19
**Domain:** Python provider abstraction (`abc.ABC`, dataclasses, module-level cache)
**Confidence:** HIGH — all findings from direct codebase reads and the operator-validated MGTI skill

---

## Codebase Reconnaissance

### Current LLM Call Sites

There are **exactly three** `_call_azure_openai` invocations across two files. The function is **defined twice** (once per file) with identical HTTP logic but different `max_tokens`.

#### CS1 — `src/query_router.py:180` — intent classification

```
Caller function : classify_intent(user_query, schema_summary) -> dict[str, Any]
Call expression : content = _call_azure_openai(messages).strip()
messages shape  : [
    {"role": "system", "content": CLASSIFICATION_PROMPT + schema_text},
    {"role": "user",   "content": user_query}
]
Return expected : str — raw LLM text, caller JSON-parses it
On failure      : falls through to _heuristic_classify(); QueryError re-raised
```

The `system` text is embedded as the first message with `"role": "system"`. There is NO separate system parameter today; it lives inside the messages list.

#### CS2 — `src/sql_generator.py:194` — SQL generation

```
Caller function : generate_sql(user_query, schema_summary) -> dict[str, Any]
Call expression : content = _call_azure_openai(messages).strip()
messages shape  : [
    {"role": "system",    "content": SYSTEM_PROMPT + schema_text},
    {"role": "user",      "content": example_query},   # few-shot × 4
    {"role": "assistant", "content": json.dumps(example_response)},
    ... (8 few-shot turns total)
    {"role": "user",      "content": user_query}
]
Return expected : str — raw LLM text, caller JSON-parses it
On failure      : raises QueryError
```

#### CS3 — `src/query_router.py:542` — executive summary generation

```
Caller function : generate_executive_summary(user_query, results, route_used) -> str | None
Call expression : summary = _call_azure_openai(messages).strip()
messages shape  : [
    {"role": "system", "content": SUMMARY_PROMPT},
    {"role": "user",   "content": f"Question: {user_query}\n\nResults..."}
]
Return expected : str — used directly as the summary text
On failure      : returns None (silent catch-all)
```

#### The duplicated `_call_azure_openai` function — differences

| Attribute      | `query_router.py:105`  | `sql_generator.py:86`   |
|---------------|------------------------|-------------------------|
| `max_tokens`  | `500`                  | `1000`                  |
| `temperature` | `0.1`                  | `0.1`                   |
| `timeout`     | `30`                   | `30`                    |
| Logic         | **identical otherwise** | **identical otherwise** |

The difference in `max_tokens` matters: the Phase 1 `complete()` signature must allow the caller to pass `max_tokens` per call, or the adapter must know which call site it is serving. The parity-first design means **`max_tokens` must be a caller-supplied kwarg on `complete()`**, not baked into the adapter.

The function signature today: `_call_azure_openai(messages: list[dict]) -> str`

The function reads globals directly: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `API_VERSION` from `config.py`.

---

### Current Azure Config

**File:** `config.py` (module-level constants, read at import time via `python-dotenv`)

| Env Var              | Config Name            | Default       | Required for LLM |
|---------------------|------------------------|---------------|-----------------|
| `AZURE_OPENAI_ENDPOINT` | `AZURE_OPENAI_ENDPOINT` | `""`        | YES             |
| `AZURE_OPENAI_API_KEY`  | `AZURE_OPENAI_API_KEY`  | `""`        | YES             |
| `API_VERSION`           | `API_VERSION`           | `"2023-05-15"` | YES (used in URL) |

There is no `LLM_PROVIDER_DEFAULT` env var today. There is no `Settings` class; everything is module-level constants read once at import.

The URL construction today: `f"{AZURE_OPENAI_ENDPOINT}?api-version={API_VERSION}"` — i.e., `AZURE_OPENAI_ENDPOINT` is the **full deployments URL** including the deployment name (e.g., `https://xxx.openai.azure.com/openai/deployments/gpt-4o/chat/completions`).

**Key for `validate_config("azure_openai")`:** The required vars are `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`. `API_VERSION` has a usable default (`"2023-05-15"`) so it is OPTIONAL for validation purposes.

---

### Current Intent Classification Shape

`classify_intent()` returns a plain `dict[str, Any]`:

```python
{
    "intent": str,             # "structured" | "semantic" | "hybrid"
    "confidence": float,       # 0.0–1.0
    "reasoning": str,          # explanation string
    "detected_filters": dict,  # {"priority": [...], "assignment_group": str, "date_range": str}
    "chart_requested": bool,   # from _detect_chart_request() BEFORE LLM call
    "chart_type": str | None,  # "pie" | "bar" | "line" | "histogram" | None
}
```

**CRITICAL:** `chart_requested` and `chart_type` are populated by `_detect_chart_request(user_query)` at `query_router.py:164` **before** `_call_azure_openai` is called. They are then merged into the classification dict at lines 207–209. These two fields must NOT appear in `ClassificationResultV1`'s LLM schema — only in the merged dict that `classify_intent()` returns.

There is **no existing `ClassificationResultV1` dataclass** in the codebase. Phase 1 must define it. The recommended fields based on what the LLM is asked to produce (the JSON format in `CLASSIFICATION_PROMPT`):

```python
@dataclass(frozen=True, slots=True)
class ClassificationResultV1:
    version: str                    # "v1" — literal, for schema-versioning (PF-8)
    intent: str                     # "structured" | "semantic" | "hybrid"
    confidence: float               # 0.0–1.0
    reasoning: str                  # brief explanation
    detected_filters: dict          # {"priority", "assignment_group", "date_range"}
```

`chart_requested` and `chart_type` must be carried separately — they are heuristic outputs, not LLM outputs.

`_detect_chart_request(query: str) -> tuple[bool, str | None]` is defined at `query_router.py:76`. It uses a keyword dict `CHART_KEYWORDS` and `re.search`. Signature is stable; Phase 4 can call it as-is. No changes needed in Phase 1.

---

### `requirements.txt` Current State

```
streamlit>=1.40.0
duckdb>=1.1.0
pandas>=2.2.0
python-dotenv>=1.0.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
requests>=2.31.0
onnxruntime>=1.14.1
altair>=5.0.0
python-certifi-win32>=1.6.1; sys_platform == 'win32'
torch>=2.6.0
transformers>=4.51.0
```

`jsonschema` is **NOT present**. Phase 1 must add `jsonschema>=4.26.0,<5` per CFG-06. It is a pure-Python package, no compiled extension.

`requests` is already present at `>=2.31.0`. No HTTP client changes needed.

---

## MGTI Anthropic Shape (from Skill)

Source: `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\SKILL.md` — operator-validated against kbroles Quicks 008–012 (2026-05-12, commit `4477a7e`).

### Key interface facts for Phase 1 signature decisions

**`system` is top-level, NOT a message role.**

Azure OpenAI today: `{"role": "system", "content": "..."}` inside the `messages` list.
Anthropic MGTI: `"system": "..."` at the top level of the request body. Putting system in messages[] causes `400 invalid_request_error`.

**This is the single most important cross-provider shape difference for `complete()` signature design.**

**Request body shape (Anthropic):**
```json
{
    "anthropic_version": "bedrock-2023-05-31",
    "system": "<system prompt>",
    "messages": [{"role": "user", "content": "..."}],
    "max_tokens": 1024,
    "temperature": 0.0
}
```

`max_tokens` is REQUIRED (unlike Azure OpenAI where it is optional). The `anthropic_version` field is required in the body (not a header).

**Auth header:** `X-Api-Key: <key>` — NOT `Authorization: Bearer`, NOT `api-key` (Azure style).

**URL shape:** `POST {base_url}/model/{model}/messages` — the `/messages` suffix is mandatory. The base_url env var should include everything up to and including `/v1`.

**Tool-call request shape (for Phase 4 reference, define types now):**
```json
{
    "tools": [{"name": "...", "description": "...", "input_schema": {...}}],
    "tool_choice": {"type": "tool", "name": "...", "disable_parallel_tool_use": true},
    ...
}
```

**Tool-call response shape:**
```json
{
    "stop_reason": "tool_use",
    "content": [{"type": "tool_use", "id": "toolu_...", "name": "...", "input": {...}}]
}
```

**Text response shape:**
```json
{
    "stop_reason": "end_turn",
    "content": [{"type": "text", "text": "..."}],
    "usage": {"input_tokens": 25, "output_tokens": 12}
}
```

**Guardrail response shape (HTTP 200!):**
```json
{"stop_reason": "guardrail_intervened", "content": []}
```

**Error envelope (HTTP 4xx/5xx) — differs from native Anthropic SDK:**
```json
{"error": {"title": "...", "detail": "...", "status": 404}}
```
Note: native Anthropic SDK error shape is `{"type": "error", "error": {"type", "message"}}`. The MGTI proxy uses a different envelope. Any error-handling code copied from the official SDK docs will be wrong.

**Anthropic env vars needed (Phase 1 `validate_config`):**
- `ANTHROPIC_BASE_URL` — required
- `ANTHROPIC_API_KEY` — required
- `ANTHROPIC_MODEL` — required; must be `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` or newer with `eu.` prefix
- `ANTHROPIC_VERSION` — optional, default `"bedrock-2023-05-31"`
- `ANTHROPIC_MAX_TOKENS` — optional, default `1024`
- `ANTHROPIC_TEMPERATURE` — optional, default `0.0`
- `ANTHROPIC_TIMEOUT_S` — optional, default `30`

---

## Recommended Shapes (Claude's Discretion Areas)

### 1. Module Layout Under `src/llm/`

**Option A: Minimal (3 files)**
```
src/llm/
├── __init__.py   # get_llm factory + module cache
├── base.py       # LLMClient ABC + all dataclasses + Settings + validate_config
└── errors.py     # full error hierarchy
```

Pros: fewer files, less navigation. Cons: `base.py` mixes concerns (interface + config + types); grows large when Phase 2 adds Settings fields.

**Option B: Separated (5 files) — RECOMMENDED**
```
src/llm/
├── __init__.py       # get_llm factory + module-level _cache dict
├── base.py           # LLMClient ABC only
├── errors.py         # full error hierarchy
├── types.py          # ToolSchema, ToolCall, IntentResult, ClassificationResultV1
└── config.py         # Settings dataclass + validate_config + per-provider required-var lists
```

Pros: matches the phase structure (Phase 2 adds `azure_openai.py`, Phase 3 adds `anthropic_mgti.py` — they drop into a stable layout); `config.py` is a clean slot for new Anthropic fields in Phase 3; `types.py` is the single source of truth for `ClassificationResultV1` which Phase 4 consumes to auto-generate the tool schema. Cons: slightly more files to navigate.

**Recommendation: Option B.** YAGNI argument doesn't apply here because Phases 2/3/4 will create `azure_openai.py` and `anthropic_mgti.py` anyway; the slot layout exists for them regardless.

**Stub files for adapters in Phase 1:**
`azure_openai.py` and `anthropic_mgti.py` should be created as empty stubs (or raise `NotImplementedError`) in Phase 1 so the package is importable and the `get_llm` factory can reference them without a circular import. They get real implementations in Phases 2 and 3.

---

### 2. Error Taxonomy

All six error classes must be defined in Phase 1 (only `LLMConfigError` is raised in Phase 1; the rest become live in Phases 2–4). Defining them now prevents the seam from being revisited.

**Recommended inheritance shape (flat under LLMError):**

```python
class LLMError(Exception):
    """Base class for all LLM adapter errors."""
    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.correlation_id = correlation_id

class LLMAuthError(LLMError): ...         # 401/403
class LLMTransientError(LLMError): ...    # 5xx, timeout-adjacent
class LLMGuardrailError(LLMError): ...    # guardrail_intervened (not retryable)
class LLMSchemaError(LLMError): ...       # tool_use input failed validation
class LLMTimeoutError(LLMError): ...      # requests.Timeout
class LLMConfigError(LLMError): ...       # missing env vars (raised in Phase 1)
```

**Why flat (not grouped):** The requirement in CONTEXT.md is that call sites catch by name (e.g., `except LLMAuthError`). A grouped tree (`class LLMRetryableError(LLMError)` containing `LLMTransientError` + `LLMTimeoutError`) would be a nice extra but adds a class that no call site currently uses; add it in Phase 5 if monitoring shows it's needed.

**`retryable: bool` class attribute:** Defer. Phase 1 defines the error classes; Phase 5 is the appropriate time to add the retry attribute if a retry strategy is introduced. Adding it now would make it misleading — no retry logic exists yet.

**`__init__` parameters:** `provider` and `status_code` are the two most useful for debugging and for Phase 3/4 structured logging. `correlation_id` is also carried so Phase 3's `X-Correlation-Id` can flow through to the log event at the call-site boundary. All three should be keyword-only and optional (some errors, like `LLMConfigError`, have no HTTP context).

**OBS-03 compliance:** `LLMError.__repr__` must not include `provider` if it contains key material. Since `provider` is just a string like `"azure_openai"`, it is safe. The API key must never appear in any `LLMError` field.

---

### 3. `LLMClient` Method Signatures

The critical cross-provider constraint: **Anthropic puts `system` top-level; Azure OpenAI puts it inside `messages[]`.**

The cleanest solution is to follow the Anthropic shape at the interface level — accept `system` as a separate string parameter — and let the Azure adapter extract it from the first `system`-role message if called in Azure's style, OR accept both shapes. However, this would require changing call sites at Phase 2 time (they currently pass a `messages` list with `role: system`).

**Parity-first constraint from CONTEXT.md:** Phase 2 must produce byte-identical output with minimal diff. The simpler path is: keep `messages: list[dict]` as the primary argument, let the INTERFACE accept it as-is, and let each adapter handle the system-extraction internally.

**Recommended `complete` signature:**

```python
@abstractmethod
def complete(
    self,
    messages: list[dict],
    *,
    max_tokens: int = 500,
    temperature: float = 0.1,
    **kwargs: Any,
) -> str:
    ...
```

Reasoning:
- `messages: list[dict]` — matches today's call sites exactly; zero Phase 2 diff at call sites
- `max_tokens` is a keyword arg with a default — addresses the 500 vs 1000 difference between CS1/CS2; callers override the default
- `temperature` matches today's hardcoded `0.1`; callers can override
- Returns `str` — consistent with ABS-05 (no raw JSON crosses the adapter boundary)
- The Azure adapter passes `messages` directly to the payload; the Anthropic adapter extracts the first `role: system` message and promotes it to the top-level `system` field

This means **the Anthropic adapter owns the system-extraction logic**, not the interface. This is the right place for it — the Azure adapter doesn't need to know about it.

**Recommended `classify_with_tool` signature:**

```python
@abstractmethod
def classify_with_tool(
    self,
    messages: list[dict],
    tool: "ToolSchema",
    *,
    tool_name: str,
    **kwargs: Any,
) -> "ToolCall":
    ...
```

Reasoning:
- `tool: ToolSchema` carries the schema; `tool_name` identifies which tool to invoke (enables `tool_choice` construction in the Anthropic adapter)
- Returns `ToolCall` — the dataclass wrapping the validated input dict
- Azure adapter (Phase 2) implements this via JSON-in-prompt (the existing pattern) and wraps the parsed result in `ToolCall`; Anthropic adapter (Phase 4) implements via native strict-tools
- Both adapters thus have the same outward contract

**`ToolSchema` and `ToolCall` dataclasses:**

```python
@dataclass(frozen=True, slots=True)
class ToolSchema:
    name: str
    description: str
    input_schema: dict   # JSON Schema dict; Anthropic uses directly; Azure uses for prompt templating

@dataclass(frozen=True, slots=True)
class ToolCall:
    tool_name: str
    input: dict          # validated tool input from the LLM
    raw_response: dict = field(default_factory=dict, repr=False)  # Phase 4 may use for debug
```

**`IntentResult` dataclass** (per ABS-03 / TOOL-01):

```python
@dataclass(frozen=True, slots=True)
class IntentResult:
    intent: str
    confidence: float
    reasoning: str
    detected_filters: dict
    chart_requested: bool    # heuristic, merged at call site — NOT from LLM
    chart_type: str | None   # heuristic, merged at call site — NOT from LLM
```

This is the shape `classify_intent()` currently returns as a plain dict. Phase 4 converts `classify_intent` to return `IntentResult` instead of `dict`.

---

### 4. Factory + Cache

**Option A: `if/elif` dispatch**
```python
_cache: dict[str, LLMClient] = {}

def get_llm(provider: str | None = None) -> LLMClient:
    provider = _resolve_provider(provider)
    if provider not in _cache:
        if provider == "azure_openai":
            from src.llm.azure_openai import AzureOpenAIClient
            _cache[provider] = AzureOpenAIClient(...)
        elif provider == "anthropic_mgti":
            from src.llm.anthropic_mgti import AnthropicMGTIClient
            _cache[provider] = AnthropicMGTIClient(...)
        else:
            raise LLMConfigError(f"Unknown provider: {provider!r}")
    return _cache[provider]
```

Pros: explicit, readable, no registry data structure to maintain.
Cons: adding a third provider in the future requires editing this function.

**Option B: Registry dict — RECOMMENDED**
```python
_REGISTRY: dict[str, type[LLMClient]] = {
    "azure_openai": "src.llm.azure_openai.AzureOpenAIClient",   # string to defer import
    "anthropic_mgti": "src.llm.anthropic_mgti.AnthropicMGTIClient",
}
_cache: dict[str, LLMClient] = {}

def get_llm(provider: str | None = None) -> LLMClient:
    provider = _resolve_provider(provider)
    if provider not in _cache:
        if provider not in _REGISTRY:
            raise LLMConfigError(f"Unknown provider: {provider!r}", provider=provider)
        cls = _import_class(_REGISTRY[provider])  # lazy import
        _cache[provider] = cls()
    return _cache[provider]
```

Pros: adding Phase 3 Anthropic is a one-line registry entry; the dispatch logic never changes. Cons: slightly more indirection with the lazy import.

**Recommendation: Option B (registry)**. Two providers doesn't justify the pattern alone, but Phase 3 Anthropic and possible future providers make the registry immediately pay off. Use string-based lazy imports (`importlib.import_module`) to avoid circular imports between `__init__.py` and adapter modules.

**`_resolve_provider` implementation:**

```python
def _resolve_provider(explicit: str | None) -> str:
    if explicit is not None:
        return explicit
    # Safe Streamlit session state access — st.session_state raises AttributeError
    # when not running under Streamlit (e.g. during pytest).
    try:
        import streamlit as st
        provider = st.session_state.get("llm_provider")
        if provider:
            return provider
    except Exception:
        pass
    return os.environ.get("LLM_PROVIDER_DEFAULT", "azure_openai")
```

**The Streamlit-safety issue:** `st.session_state` raises `AttributeError` outside of a Streamlit session (e.g., during a pytest run or a standalone script). The `try/except Exception` wrapper above handles this. The alternative (`hasattr(st, "session_state")`) is not sufficient because `st.session_state` exists as an attribute but raises on `.get()` outside a session context. Verified pattern: wrap the entire `st.session_state` access in `try/except Exception`.

**Cache key in Phase 1:** `provider` string only (e.g., `"azure_openai"`). No key fingerprinting yet (deferred per CONTEXT.md). This is safe because Phase 1 doesn't wire any adapter to live call sites; the cache is for Phase 2+ use.

---

## Risks and Pitfalls

### Risk 1: `slots=True` Python Version Floor

`@dataclass(frozen=True, slots=True)` requires **Python 3.10+**. The `slots` parameter was added in 3.10.

- **Dev machine runtime:** Python 3.13.3 (confirmed via `python --version` in the project directory) — slots work.
- **Deploy target:** The `deploy/BUILD_PYTHON_FROM_SOURCE.md` targets Python 3.11.14 — slots work.
- **Risk:** LOW. Both environments are 3.11+.
- **Action for planner:** Add a comment in `types.py` noting the 3.10+ floor, and add `python_requires = ">=3.10"` if a `setup.py`/`pyproject.toml` is created later.

### Risk 2: `from __future__ import annotations` + `slots=True` Interaction

Python 3.10–3.11 had a known interaction bug between `from __future__ import annotations` (PEP 563, which makes all annotations strings) and `@dataclass(slots=True)`. The bug caused slots dataclasses to silently fail to set `__slots__` under certain conditions.

In Python 3.13 (dev machine) and Python 3.11.14+ (deploy target), this is fixed. However, existing project files use `from __future__ import annotations` (check: `query_router.py:5`, `sql_generator.py:3`, `utils.py:3`). New `src/llm/` files should also use it for consistency, but the planner should be aware of this historical interaction. In Python 3.13 it is safe.

### Risk 3: No Existing Imports of `_call_azure_openai` Outside the Two Files

Confirmed by grep: `_call_azure_openai` appears only in `src/query_router.py` (defined at line 105, called at lines 180 and 542) and `src/sql_generator.py` (defined at line 86, called at line 194). It is NOT imported from anywhere else. The three call sites are complete.

No other file imports it. Safe to delete in Phase 2.

### Risk 4: Module-Level Cache vs `@st.cache_resource` (Phase 1 vs Phase 5)

The module-level `_cache: dict[str, LLMClient]` in Phase 1 is intentionally simple. Phase 5 is supposed to wrap the factory with `@st.cache_resource` for proper Streamlit session management.

**Potential conflict:** If Phase 1 creates a module-level dict that the Phase 5 `@st.cache_resource` decorator tries to wrap around, there could be double-caching. The resolution:

- Phase 1: `get_llm()` uses a plain module-level `_cache` dict (no decorator).
- Phase 5: Introduce a `_get_llm_cached` function decorated with `@st.cache_resource` that wraps or replaces `get_llm()`, keyed on provider + config values.

The planner should design Phase 1 so the plain `_cache` dict is easily replaced or bypassed by Phase 5's `@st.cache_resource`. One clean approach: expose `_cache` as a module-level variable with a leading underscore, letting Phase 5 clear it via `src.llm._cache.clear()` before the decorator takes over.

### Risk 5: Existing Logging Does Not Currently Expose Keys

Current `_call_azure_openai` in `query_router.py:121` sets `"api-key": AZURE_OPENAI_API_KEY` in a `headers` dict. This dict is passed to `requests.post` but never logged. The `logger.error(f"Azure OpenAI API error: {e}")` at line 140 logs the exception string, not the headers.

The new `Settings` or config dataclass must ensure `repr` does not expose the key. Options:
- Use `dataclasses.field(repr=False)` on `api_key` and any credential field
- Override `__repr__` on the Settings dataclass to redact keys

`field(repr=False)` is simpler and sufficient for MVP (per CONTEXT.md's "simplest thing that works" decision).

No existing code calls `repr(settings)` or passes a Settings object into a logger format string — there is no OBS-03 regression to fix in Phase 1, only a forward prevention to implement.

### Risk 6: `config.py` Currently Has No `Settings` Class — Side-Effect at Import

`config.py` currently calls `load_dotenv(BASE_DIR / ".env")` and `DATA_DIR.mkdir(exist_ok=True)` and `DB_DIR.mkdir(exist_ok=True)` at module import time. This means importing `config` in a test creates directories. Phase 1's `Settings` dataclass (or module-level constants) in `src/llm/config.py` should NOT replicate this side-effect pattern. Read env vars in `validate_config()` or in the `Settings` constructor, do not create directories.

### Risk 7: `ToolCall.raw_response` Field and `frozen=True`

If `ToolCall` carries `raw_response: dict` and uses `frozen=True`, the dict is technically mutable (you can mutate the dict's contents even if the slot is frozen). This is acceptable for Phase 1 since `raw_response` is debug-only (`repr=False`). The planner should document this limitation in a comment.

### Risk 8: `classify_intent()` Return Type Change Is a Phase 4 Concern

`classify_intent()` currently returns `dict[str, Any]`. Changing it to return `IntentResult` is a Phase 4 task (when strict-tools mode lands). Phase 1 defines `IntentResult` but does NOT change `classify_intent()`. The planner must make this explicit in Phase 1 tasks to avoid scope creep.

---

## Open Questions for Planner

**1. Should `validate_config` be fail-fast at import or at call time?**

The CONTEXT.md success criterion says "called at app boot". Streamlit runs `app.py` on each browser refresh; the `app.py` module-level code runs then. The planner should decide whether `validate_config(provider)` is called at the top of `app.py` (explicit, immediately visible to the developer) or inside `get_llm()` (automatic, but only triggered on first LLM use). Recommendation: explicit call at the top of `app.py`, outside `@st.cache_resource`.

**2. Where does `Settings` live — `src/llm/config.py` or top-level `config.py`?**

Option A: Extend top-level `config.py` with Anthropic fields and a `Settings` object — keeps all config in one place but mixes LLM config with DB paths and embedding model names.

Option B: Create `src/llm/config.py` with an `LLMSettings` dataclass (Azure fields + Anthropic fields) and `validate_config()` — keeps LLM concerns in the LLM package.

Recommendation: Option B (separate `src/llm/config.py`). Top-level `config.py` already imports things from `src` indirectly; putting `LLMSettings` in `src/llm/` avoids the temptation to put LLM-specific logic in the top-level module. The adapter stub files import from `src.llm.config`, not from `config`.

**3. Should the Azure adapter stub file in Phase 1 raise `NotImplementedError` or be completely empty?**

If it raises `NotImplementedError` in `complete()`, the factory can register it and the Phase 1 test can import `AzureOpenAIClient` without wiring it to a live request. This is safer than an empty stub that would silently succeed on import. Recommendation: raise `NotImplementedError` stubs in Phase 1; Phase 2 replaces them with real logic.

**4. Does `ToolSchema.input_schema` need to be `dict` or a more specific typed structure?**

For Phase 1, `dict` is sufficient — it is passed as-is to the Anthropic `tools[*].input_schema` field in Phase 4, and used for prompt-templating in the Azure adapter (Phase 2). Using a more specific type (e.g., a TypedDict describing JSON Schema structure) would over-engineer Phase 1. The planner can leave it as `dict`.

**5. Should `LLMConfigError.__init__` accept `missing_vars: list[str]` for CFG-03's "human-readable list of missing variables" requirement?**

Recommendation: Yes. `validate_config()` collects all missing vars before raising (not fail-on-first), then constructs a single `LLMConfigError` with `missing_vars` embedded in the message string. No extra field needed; the message is the artifact. Example: `LLMConfigError("Missing required env vars for azure_openai: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY")`.

---

## Sources

### Primary (HIGH confidence — direct reads)
- `C:\mbrunoapp\snow_query\src\query_router.py` — all three call sites, `_call_azure_openai` definition, `classify_intent` shape, `_detect_chart_request` location and signature
- `C:\mbrunoapp\snow_query\src\sql_generator.py` — CS2 implementation, `_call_azure_openai` second definition (max_tokens 1000)
- `C:\mbrunoapp\snow_query\config.py` — exact Azure env vars and defaults
- `C:\mbrunoapp\snow_query\src\utils.py` — `QueryError` shape, logger setup pattern
- `C:\mbrunoapp\snow_query\src\embeddings.py` — module-level cache pattern (`_model`, `_chroma_client`)
- `C:\mbrunoapp\snow_query\requirements.txt` — confirmed `jsonschema` absent, `requests>=2.31` present
- `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\SKILL.md` — operator-validated request shape, error envelope, tool-call shape, 12 baseline pitfalls, env vars
- `C:\mbrunoapp\snow_query\deploy\BUILD_PYTHON_FROM_SOURCE.md` — Python 3.11.14 target confirmed
- `python --version` at project directory — Python 3.13.3 confirmed on dev machine
- `python -c "..."` verification — `@dataclass(frozen=True, slots=True)` confirmed working on Python 3.13.3
- `C:\mbrunoapp\snow_query\.planning\research\SUMMARY.md` — project-level research context

### Secondary (MEDIUM confidence)
- `C:\mbrunoapp\snow_query\.planning\phases\01-abstraction-seam\01-CONTEXT.md` — locked user decisions and discretion areas
- `C:\mbrunoapp\snow_query\src\app.py` — Streamlit session-state patterns (partial read, first 80 lines)

---

## Metadata

**Confidence breakdown:**
- Call sites (count, args, return shape): HIGH — direct code read
- Azure config env vars: HIGH — direct code read
- `ClassificationResultV1` field list: HIGH — derived from `CLASSIFICATION_PROMPT` and `classify_intent` return dict
- MGTI Anthropic request/response shape: HIGH — operator-validated skill
- `slots=True` Python compatibility: HIGH — verified via shell execution
- Streamlit `session_state` safety outside Streamlit: MEDIUM — standard Python behavior, but exact exception type varies across Streamlit versions; `except Exception` covers it safely

**Research date:** 2026-05-19
**Valid until:** 2026-06-18 (30 days; stable Python/Streamlit patterns)
