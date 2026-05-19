# Architecture Research

**Domain:** Multi-provider LLM abstraction in a layered Streamlit/Python app (requests-based HTTP, no vendor SDKs)
**Researched:** 2026-05-19
**Confidence:** HIGH for structural recommendations (grounded in the existing codebase + standard Python patterns); MEDIUM for build-order details (specific to this app, but verified against current call sites)

## Standard Architecture

### System Overview (target state, after refactor)

```
+-------------------------------------------------------------------+
|                       UI Layer (Streamlit)                         |
|                                                                    |
|  app.py                                                            |
|    +-- render_sidebar()  -- new: provider dropdown                 |
|    |     writes st.session_state["llm_provider"]                   |
|    +-- process_query()                                             |
|          reads provider from session, calls route_query(..., llm=) |
+--------------------------------+----------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                  Orchestration Layer (existing)                    |
|                                                                    |
|  src/query_router.py        src/sql_generator.py                   |
|    classify_intent(llm)       generate_sql(llm)                    |
|    generate_executive_         (uses llm.complete)                 |
|      summary(llm)                                                  |
|                                                                    |
|    -- NO direct HTTP. Calls llm.complete() / llm.classify_intent() |
+--------------------------------+----------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                  NEW: LLM Abstraction Layer (src/llm/)             |
|                                                                    |
|  src/llm/__init__.py         -- public surface, get_llm() factory  |
|  src/llm/base.py             -- LLMClient Protocol, dataclasses    |
|  src/llm/azure_openai.py     -- AzureOpenAIClient adapter          |
|  src/llm/anthropic_mgti.py   -- AnthropicMGTIClient adapter        |
|  src/llm/errors.py           -- LLMError -> mapped to QueryError   |
+--------------------------------+----------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                  Network Layer (existing: requests)                |
|                                                                    |
|   Azure OpenAI endpoint            MGTI Apigee/Bedrock proxy       |
|   POST {endpoint}?api-version=...  POST {endpoint}/messages        |
|   header: api-key                  header: X-Api-Key               |
|   body: messages, temp, max_tokens body: anthropic_version,        |
|                                          model, max_tokens,        |
|                                          system, messages,         |
|                                          [tools, tool_choice]      |
+-------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|---------------|------------------------|
| `src/llm/base.py` | Define provider-agnostic interface and data shapes | `LLMClient` Protocol + `ToolSchema`/`ToolCall` dataclasses |
| `src/llm/azure_openai.py` | Wrap existing `_call_azure_openai` logic behind interface | Adapter class that owns its endpoint/key/version |
| `src/llm/anthropic_mgti.py` | Speak MGTI Apigee/Bedrock-proxied Anthropic Messages API | Adapter class with `/messages` suffix, X-Api-Key, `anthropic_version="bedrock-2023-05-31"`, `eu.`-prefix model, system top-level |
| `src/llm/errors.py` | Common error type for adapter-layer failures | `LLMError(Exception)` with `provider`, `status`, `details` |
| `src/llm/__init__.py` | Factory + module-level resolver | `get_llm(provider: str \| None) -> LLMClient` |
| `src/query_router.py` (modified) | Orchestrate routing; accept injected `llm` | Pass `llm` through to sub-calls instead of calling `_call_azure_openai` |
| `src/sql_generator.py` (modified) | Build SQL prompts; accept injected `llm` | Drop `_call_azure_openai`; use `llm.complete()` |
| `app.py` (modified) | Read provider selection from session, pass to router | New `_resolve_llm()` helper, call `route_query(..., llm=...)` |
| `config.py` (modified) | Add Anthropic credentials + default-provider env var | `LLM_PROVIDER_DEFAULT`, `ANTHROPIC_ENDPOINT`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `scripts/smoke_llm.py` (new) | End-to-end smoke test of each provider | Standalone Python script: round-trip text + classify for both providers |

## Recommended Project Structure

```
snow_query/
+-- app.py                          # MODIFIED: provider dropdown + llm wiring
+-- config.py                       # MODIFIED: + Anthropic / default-provider envs
+-- src/
|   +-- __init__.py                 # unchanged
|   +-- utils.py                    # unchanged (QueryError stays the call-site error)
|   +-- query_router.py             # MODIFIED: accept llm param, drop _call_azure_openai
|   +-- sql_generator.py            # MODIFIED: accept llm param, drop _call_azure_openai
|   +-- semantic_search.py          # unchanged (no LLM calls)
|   +-- embeddings.py               # unchanged
|   +-- ingest.py                   # unchanged
|   +-- chart_generator.py          # unchanged
|   +-- llm/                        # NEW: provider abstraction
|       +-- __init__.py             # get_llm() factory, re-exports
|       +-- base.py                 # LLMClient Protocol + dataclasses
|       +-- azure_openai.py         # AzureOpenAIClient
|       +-- anthropic_mgti.py       # AnthropicMGTIClient
|       +-- errors.py               # LLMError
+-- scripts/
    +-- smoke_llm.py                # NEW: provider round-trip smoke test
```

### Structure Rationale

- **`src/llm/` as a subpackage (not a single module):** Three reasons. (1) Each adapter is ~80-150 LOC including request shaping and response normalization — a flat `src/llm.py` would balloon past 300 LOC quickly. (2) The codebase convention is "one module per concern" (see `src/ingest.py`, `src/embeddings.py`); adapters are concerns of the abstraction, not of the abstraction layer itself. (3) Adding a third provider later (e.g., local Ollama for offline dev) is a new file, not a diff inside a fat module.
- **Not under `src/providers/`:** The word "provider" is overloaded (data provider, auth provider). `llm/` is unambiguous and matches how the rest of the ecosystem names this (LangChain `llms/`, LlamaIndex `llms/`).
- **Not in `src/utils.py`:** `utils.py` is for cross-cutting helpers (formatting, logging, exceptions). LLM calls are a layer, not a utility — putting them there would couple unrelated concerns and bloat the file beyond its current ~210 LOC.
- **`scripts/` at repo root (not under `src/`):** Matches Python community convention for non-importable runnable entry points. Keeps the smoke test out of the import graph so it can't be accidentally pulled in by the app. The repo has no existing `tests/` or `scripts/` directory — creating `scripts/` (rather than `tests/`) signals "manual/CI-runnable verification" rather than "pytest suite", which matches the current testing posture in `.planning/codebase/TESTING.md` (no test framework configured).
- **`errors.py` separate from `base.py`:** Errors are imported by adapters, by call sites (for mapping), and by the smoke test. A separate module avoids circular imports when the base Protocol imports nothing provider-specific and adapters import errors directly.

## Architectural Patterns

### Pattern 1: Adapter Behind a Protocol (the core pattern)

**What:** Define a `typing.Protocol` in `src/llm/base.py` that both adapters structurally implement. Call sites depend on the Protocol, not the concrete class.

**When to use:** Always — this is the load-bearing pattern of the refactor.

**Trade-offs:**
- (+) Duck-typed; no inheritance, no abstract base class boilerplate.
- (+) Mypy/Pyright check structural conformance without runtime overhead.
- (+) Matches the rest of the codebase, which uses plain functions + duck-typed dicts (no ABCs anywhere today).
- (-) Protocol violations surface only at the call site, not at adapter-definition time. Mitigation: the smoke test exercises every interface method against every provider.

**Example shape (illustrative, not final code):**
```python
# src/llm/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolSchema:
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON schema


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


class LLMClient(Protocol):
    provider_name: str  # "azure_openai" | "anthropic_mgti"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> str:
        """Plain-text completion. Returns the assistant text."""
        ...

    def classify_with_tool(
        self,
        messages: list[dict[str, str]],
        *,
        tool: ToolSchema,
        system: str | None = None,
        max_tokens: int = 500,
    ) -> ToolCall:
        """Strict structured output. Returns the tool call (name + args dict)."""
        ...
```

Two methods, not one. `complete` covers SQL generation and executive summary (text in, text out — both providers handle this trivially). `classify_with_tool` covers the strict-tools path for `classify_intent` only. This split is the smallest interface that satisfies actual call-site needs and avoids forcing JSON-mode emulation onto OpenAI for parity with Anthropic's tools.

### Pattern 2: Normalize at the Adapter Boundary (not at the call site)

**What:** Adapters return Python-native types (`str`, `ToolCall`), never the raw HTTP JSON. The OpenAI vs Anthropic response-shape divergence dies inside `azure_openai.py` and `anthropic_mgti.py`.

**When to use:** Always. The whole point of the abstraction collapses if call sites have to branch on provider.

**Trade-offs:**
- (+) Call sites stay identical to today's code (modulo the call swap from `_call_azure_openai(messages)` to `llm.complete(messages)`).
- (+) Adapter is the single place that knows about `choices[0].message.content` vs `content[*].text` vs `content[*].input`.
- (-) Adapters must absorb provider-specific edge cases (empty content arrays, refusals, guardrail interventions). Acceptable — that's exactly their job.

**Specific normalizations the adapters must perform:**

| Concern | OpenAI shape | Anthropic shape | Normalized to |
|---------|--------------|-----------------|---------------|
| Text response | `r["choices"][0]["message"]["content"]` | concat `r["content"][*]["text"]` where `type == "text"` | `str` |
| Tool call | not used (we use plain-text JSON-in-prompt today) | find `r["content"][*]` where `type == "tool_use"`, return `{name, input}` | `ToolCall(name, arguments)` |
| System prompt | first `{"role": "system", ...}` in messages | top-level `system` field; messages must not contain `role: system` | adapter strips system from messages, passes via `system=` kwarg |
| Max tokens | optional, OpenAI defaults | **required** by Anthropic Messages API | both adapters require it; call sites already pass it |
| Stop reason | `choices[0].finish_reason` | `stop_reason` | not normalized (not used by current call sites) |
| Bedrock guardrail | n/a | `stop_reason == "guardrail_intervened"` | adapter raises `LLMError(reason="guardrail")` |

### Pattern 3: Factory Function with Module-Level Resolution

**What:** `src/llm/__init__.py` exposes `get_llm(provider: str | None = None) -> LLMClient`. When `provider is None`, reads `LLM_PROVIDER_DEFAULT` from config. Adapters are instantiated lazily on first use and cached at module level (same pattern as `_model` / `_chroma_client` in `src/embeddings.py`).

**When to use:** This is the bridge between the Streamlit session-state choice and the call sites.

**Trade-offs:**
- (+) Matches the existing module-level-cache convention exactly (`_model`, `_chroma_client`, `_collection` in `embeddings.py`).
- (+) Call sites stay testable: pass an explicit `llm=fake_llm` for any future testing; omit it to fall back to the factory.
- (-) Module-level cache is per-process. Fine for Streamlit (single process per session) — there's no multi-tenant concern because credentials come from env vars, not per-request.

**Resolution order (explicit > implicit):**
1. Explicit argument: `route_query(..., llm=some_client)` wins.
2. Session selection: `app.py` calls `get_llm(st.session_state["llm_provider"])` and passes that down.
3. Env default: `get_llm()` with no arg reads `LLM_PROVIDER_DEFAULT` (default value: `"azure_openai"` to preserve current behavior).

This avoids a global singleton with a setter (which would be hostile to future test isolation) while still being trivial to use from the UI.

### Pattern 4: Keep Existing Flow Byte-Identical Until Cutover (parity-first refactor)

**What:** Phase the work so that at every commit, the Azure OpenAI flow still produces the same outputs it does today. The Anthropic adapter and UI toggle are the *last* things to land, not the first.

**When to use:** Whenever you're refactoring a working integration into an abstraction. This is the discipline that prevents "we rebuilt it and now classify_intent silently changed behavior."

**How:** The Azure adapter (`azure_openai.py`) is a *literal extraction* of today's `_call_azure_openai` — same URL, same headers (`api-key`), same payload keys, same temperature, same timeout. The first interface-rollout commit replaces `_call_azure_openai(messages)` with `llm.complete(messages, ...)` where `llm` is the Azure adapter. No behavior change. Then Anthropic gets added alongside.

**Trade-offs:**
- (+) Each step is independently revertable.
- (+) You can verify parity (run a few queries, diff outputs) *before* introducing Anthropic, isolating the source of any regression.
- (-) Slower than "rip out both call sites and rewrite as multi-provider in one shot." Acceptable cost.

## Data Flow

### Request Flow (after refactor, semantic example)

```
User types query in Streamlit chat
   |
   v
app.py::process_query(user_query, mode)
   |
   |   1. llm = get_llm(st.session_state["llm_provider"])
   |
   v
src/query_router.py::route_query(user_query, schema, mode, llm=llm)
   |
   |   2. classification = classify_intent(user_query, schema, llm=llm)
   |          |
   |          v
   |       src/llm/<adapter>.py::classify_with_tool(messages, tool=INTENT_TOOL)
   |          |
   |          v
   |       HTTP POST -> Azure OpenAI OR MGTI/Bedrock proxy
   |          |
   |          v
   |       returns ToolCall(name="classify", arguments={"intent": ..., ...})
   |
   |   3. Based on intent, dispatch to query_with_sql / semantic_query / hybrid
   |          If SQL path: sql_generator.generate_sql(query, schema, llm=llm)
   |                          -> llm.complete(messages) -> returns SQL string
   |
   |   4. (back in app.py::process_query)
   |      generate_executive_summary(query, results, route, llm=llm)
   |          -> llm.complete(messages) -> returns prose string
   |
   v
Render results + chart + summary in Streamlit
```

### State Management

```
+----------------------+
| st.session_state     |
|----------------------|
| llm_provider: str    |  <-- written by sidebar dropdown
| schema, messages,    |
| data_loaded, etc.    |
+----------+-----------+
           |
           |  read at top of process_query()
           v
       get_llm(provider)
           |
           v
       module-level cache in src/llm/__init__.py
       {
         "azure_openai": AzureOpenAIClient(...),
         "anthropic_mgti": AnthropicMGTIClient(...),
       }
```

No setter, no closure, no singleton-with-mutable-state. The UI owns the *choice*; the factory owns *instantiation*; call sites receive an *instance*. Three responsibilities, three places.

### Key Data Flows

1. **Provider selection -> adapter instance:** Sidebar dropdown writes `st.session_state["llm_provider"]`. On the next query, `process_query` calls `get_llm(...)` which returns the cached adapter (or constructs it on first use). The choice is read fresh on every query, so the user can flip providers mid-session and the next query honors it.
2. **Adapter -> normalized response:** Each adapter encapsulates URL construction (Anthropic must append `/messages` to the endpoint base; Azure uses `?api-version=` query string), auth header naming (`api-key` vs `X-Api-Key`), payload shaping (system top-level vs system-in-messages), and response unwrapping. Call sites receive `str` or `ToolCall` — never a dict, never a response object.
3. **Error mapping:** Adapter catches `requests.exceptions.RequestException` and Anthropic-specific failures (HTTP 4xx with `error.type`, `guardrail_intervened` stop reason). Raises `LLMError(provider, status, message, details)`. Call sites in `query_router.py` and `sql_generator.py` catch `LLMError` and re-raise as `QueryError` — preserving the existing exception contract that `app.py` already handles.

## Build Order

Implementation dependencies dictate the sequence. Each step is independently mergeable and keeps the app working.

### Step 1: Define the interface (no behavior change)
- Create `src/llm/__init__.py`, `src/llm/base.py`, `src/llm/errors.py`.
- Define `LLMClient` Protocol, `ToolSchema`, `ToolCall`, `LLMError`.
- Define `get_llm()` factory that initially supports only `"azure_openai"`.
- **Verification:** module imports cleanly; `get_llm()` returns something whose type satisfies the Protocol (mypy or runtime `hasattr` check).

### Step 2: Extract the Azure OpenAI adapter
- Create `src/llm/azure_openai.py`. Move the body of `_call_azure_openai` (from both `query_router.py` and `sql_generator.py` — they're duplicates today) into `AzureOpenAIClient.complete()`.
- For now, `classify_with_tool` on the Azure adapter can build the existing JSON-in-system-prompt request (since today's `classify_intent` already parses JSON from text) — this preserves byte-identical behavior. Strict tools support for OpenAI is out of scope per the spec.
- **Verification:** instantiate `AzureOpenAIClient`, call `.complete()` with the same messages today's code uses, confirm identical output.

### Step 3: Wire call sites through the abstraction (Azure only)
- Add `llm: LLMClient | None = None` parameter to `route_query`, `classify_intent`, `query_with_sql`, `generate_sql`, `generate_executive_summary`. Default to `get_llm()` when None.
- Replace `_call_azure_openai(messages)` calls with `llm.complete(messages, ...)` and (in `classify_intent`) eventually `llm.classify_with_tool(...)`.
- Remove the now-duplicate `_call_azure_openai` private functions.
- `app.py::process_query` does not need changes yet — `route_query` falls back to `get_llm()` which resolves to Azure.
- **Verification (parity gate):** run 5-10 representative queries through the app. Outputs must be identical to pre-refactor. If they aren't, stop and find out why before continuing.

### Step 4: Add the Anthropic adapter
- Create `src/llm/anthropic_mgti.py`. Implement `complete()` using the Messages API: append `/messages` to endpoint base, `X-Api-Key` header, body with `anthropic_version="bedrock-2023-05-31"`, `model` (must be `eu.`-prefixed per MGTI Bedrock), `max_tokens` (required), `system` (top-level, extracted from messages), `messages` (filtered to non-system roles).
- Implement `classify_with_tool()` using `tools` + `tool_choice={"type": "tool", "name": tool.name}` + `input_schema`. Find the `tool_use` block in the response and return `ToolCall(name, input)`.
- Handle `guardrail_intervened` stop reason -> `LLMError(reason="guardrail")`.
- Add `"anthropic_mgti"` to `get_llm()` factory.
- Add `ANTHROPIC_ENDPOINT`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` to `config.py`.
- **Verification:** Anthropic adapter constructible from env; not yet exercised from the app.

### Step 5: Upgrade `classify_intent` to strict tools (Anthropic only)
- For Anthropic, define an `INTENT_TOOL: ToolSchema` with the same fields today's prompt asks for (`intent`, `confidence`, `reasoning`, `detected_filters`).
- `classify_intent` branches: if `llm.provider_name == "anthropic_mgti"`, call `classify_with_tool`; else call `complete` and parse JSON (today's path).
- This is the *one* call site that legitimately knows about the provider — and only for the strict-tools optimization. Document the branch.
- **Verification:** classification with Anthropic returns the same shape of dict that the Azure path returns. `route_query` doesn't notice the difference.

### Step 6: Smoke test
- Create `scripts/smoke_llm.py`. For each provider in `["azure_openai", "anthropic_mgti"]`:
  - Construct via `get_llm(provider)`.
  - Call `.complete([{"role": "user", "content": "Reply with the single word: OK"}], max_tokens=10)` — assert response contains `OK`.
  - Call `.classify_with_tool(...)` with the real intent tool against a sample query — assert returned `ToolCall` has the expected shape.
- Print PASS/FAIL per provider. Exit non-zero on any failure.
- **Verification:** `python scripts/smoke_llm.py` runs to completion against real credentials.

### Step 7: UI toggle wiring (last)
- Add a `st.selectbox("LLM Provider", ["azure_openai", "anthropic_mgti"], ...)` to the sidebar. Initialize `st.session_state["llm_provider"]` from `LLM_PROVIDER_DEFAULT` env var if absent.
- In `process_query`, resolve `llm = get_llm(st.session_state["llm_provider"])` and pass to `route_query(..., llm=llm)`.
- **Verification:** flipping the dropdown mid-session and running a query routes the next request to the chosen provider. Confirm by enabling DEBUG logging on the adapter.

### Build-order dependencies (what enables what)

```
Step 1 (interface)
   |
   v
Step 2 (Azure adapter) ----+
   |                       |
   v                       |
Step 3 (wire call sites)   |  <-- PARITY GATE: existing behavior preserved
   |                       |
   +----+                  |
        |                  |
        v                  |
Step 4 (Anthropic adapter) |
   |                       |
   v                       |
Step 5 (strict tools)      |
   |                       |
   v                       |
Step 6 (smoke test) <------+
   |
   v
Step 7 (UI toggle)
```

Steps 1-3 are a strict chain. Step 4 only depends on Step 1 (the interface) — it could theoretically run in parallel with Step 3, but doing them sequentially makes the parity gate at Step 3 unambiguous. Steps 5 and 6 require Step 4. Step 7 is last because the UI dropdown is *useless and dangerous* until both providers are verified through the smoke test.

## Anti-Patterns

### Anti-Pattern 1: Single `def call_llm(provider, ...)` switch function

**What people do:** Make one function with `if provider == "azure": ... elif provider == "anthropic": ...`. No classes, no Protocol, just a big branch.

**Why it's wrong:** Every new provider widens the switch and bloats one function. Provider-specific state (cached session, retry policy) has nowhere to live. The function becomes the dumping ground for normalization logic from every provider simultaneously.

**Do this instead:** Adapter classes behind a Protocol. State (endpoint, key, model, timeout) lives on the instance. Adding a provider is a new file, not a diff in a megafunction.

### Anti-Pattern 2: Returning raw HTTP JSON from the abstraction

**What people do:** `llm.complete()` returns `response.json()`. Call sites then write `result["choices"][0]["message"]["content"]` or `result["content"][0]["text"]` depending on provider.

**Why it's wrong:** The abstraction leaks. Call sites become provider-aware. The whole refactor was pointless — you've just renamed `_call_azure_openai` to `llm.complete` while keeping every call site broken in the same way.

**Do this instead:** Adapter returns `str` (for `complete`) or `ToolCall` (for `classify_with_tool`). Response unwrapping is the adapter's job, period.

### Anti-Pattern 3: Global mutable singleton with `set_provider()`

**What people do:** A module-level `current_llm` variable that the UI mutates via `set_provider("anthropic")`. Call sites read `current_llm` implicitly.

**Why it's wrong:** Hidden state. Call sites have no explicit dependency on the LLM — you can't tell from a function signature what it talks to. Testing requires monkeypatching. Concurrent calls (if the app ever grows) race on the global.

**Do this instead:** UI reads session state, passes the resolved adapter explicitly down the call chain. Factory is read-only — `get_llm(provider)` returns a (cached) instance, never mutates module state visible to call sites.

### Anti-Pattern 4: Forcing OpenAI to fake Anthropic's tool-use API (or vice versa) for "uniformity"

**What people do:** Define one `call_with_schema()` method on the Protocol, then for OpenAI emulate tools by injecting "respond with JSON matching this schema" into the system prompt.

**Why it's wrong:** You lose the actual benefit of Anthropic's strict tools (guaranteed schema conformance) by hiding it behind an interface that pretends OpenAI has the same guarantee — which it doesn't. The OpenAI path will silently produce malformed JSON sometimes and you'll blame the abstraction.

**Do this instead:** Two methods on the Protocol — `complete` (both providers) and `classify_with_tool` (both implement, but only Anthropic uses native tools; OpenAI implements it via prompted JSON if/when needed, and the call site that uses it is explicitly noted as Anthropic-optimized). The current spec says strict tools are Anthropic-only — that's fine, and the Protocol should reflect it honestly.

### Anti-Pattern 5: Refactoring everything in one commit

**What people do:** "I'll just rewrite query_router.py and sql_generator.py to use the new abstraction AND add Anthropic AND wire the UI toggle, all in one PR."

**Why it's wrong:** When something breaks (and something will break — most likely the Anthropic response shape for `tool_use`), you can't tell which change caused it. The parity gate at Step 3 disappears.

**Do this instead:** Follow the build order above. Each step is independently verifiable. The parity gate at Step 3 is non-negotiable.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Azure OpenAI | `requests.post(endpoint + "?api-version=...")`, header `api-key`, payload `{messages, temperature, max_tokens}`, response unwrap `choices[0].message.content` | Existing; preserve byte-identically in `azure_openai.py` |
| MGTI Apigee/Bedrock-proxied Anthropic | `requests.post(endpoint + "/messages")`, header `X-Api-Key`, payload `{anthropic_version: "bedrock-2023-05-31", model: "eu.<...>", max_tokens, system, messages, [tools, tool_choice]}`, response unwrap `content[*].text` (text) or `content[*].input` (tool_use) | New; `/messages` suffix is easy to forget. `max_tokens` is required (not optional like OpenAI). `system` is top-level (not in messages). `eu.` model prefix is required by MGTI Bedrock. `guardrail_intervened` stop_reason must be handled explicitly. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `app.py` -> `query_router.py` | Direct function call: `route_query(query, schema, mode, llm=llm)` | New `llm` kwarg; defaults to `get_llm()` so legacy callers (if any) keep working |
| `query_router.py` -> `sql_generator.py` | Direct function call: `query_with_sql(query, schema, llm=llm)` | New `llm` kwarg threaded through |
| `query_router.py` / `sql_generator.py` -> `src/llm/` | `llm.complete(...)` or `llm.classify_with_tool(...)` | Sole entry into the abstraction layer |
| `src/llm/<adapter>` -> network | `requests.post(...)` | Same library as today; no new dependencies |
| `src/llm/errors.py::LLMError` -> `src/utils.py::QueryError` | Caught in `query_router`/`sql_generator`, re-raised as `QueryError(message, details)` | Preserves the existing exception contract that `app.py::format_error_message` already handles. No changes to `utils.py` required. |

### Where the LLMError -> QueryError mapping lives

Each call site that invokes `llm.*()` wraps the call in a try/except that catches `LLMError` and raises `QueryError` with the same message+details fields. Example:

```python
# in src/sql_generator.py::generate_sql
try:
    content = llm.complete(messages, max_tokens=1000).strip()
except LLMError as e:
    raise QueryError(f"{e.provider} API call failed", str(e))
```

The mapping is *at the call site*, not inside the adapter. Rationale: the adapter doesn't know whether a failed `complete()` is a query error, an ingestion error, or something else — that depends on what the caller was doing. Keeping the mapping at the call site preserves the existing exception semantics in `utils.py` without making the adapter depend on `utils.py` (which would create a cycle, since `utils.py` is the bottom of the dependency graph today).

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (today) | Module-level adapter cache is fine. Single-process Streamlit. |
| 10 concurrent users | Still fine. Adapters are thread-safe for read operations (no mutable state after construction). `requests` sessions are independent per call. |
| 100+ concurrent users | Replace `requests.post` with a pooled `requests.Session()` per adapter (one connection pool, kept-alive). Consider rate-limit-aware retry in the adapter. Not in scope for this milestone. |

### Scaling Priorities (for this refactor)

1. **First bottleneck (will not hit at current scale):** No connection pooling — each `requests.post` opens a fresh TCP+TLS connection. Per-call overhead is ~100-300ms. Fix only if it matters; today it does not.
2. **Second bottleneck (won't hit):** Module-level cache means the factory builds adapters once per process. Streamlit's auto-reload destroys and recreates the process, so cache is naturally bounded.

The refactor is not motivated by scale — it's motivated by extensibility. Don't over-engineer for scale that doesn't exist.

## Migration Steps (preserving the existing Azure OpenAI flow)

This section restates the build order from the perspective of "what is the running app doing at each checkpoint?"

| Checkpoint | App behavior | Risk if reverted? |
|------------|--------------|-------------------|
| Before any change | App uses Azure OpenAI via `_call_azure_openai` in `query_router.py` and `sql_generator.py` (duplicated body) | n/a (baseline) |
| After Step 1 (interface defined) | App uses Azure OpenAI via `_call_azure_openai` (unchanged). New `src/llm/` exists but is not imported by app code. | Trivially revertable — delete `src/llm/`. |
| After Step 2 (Azure adapter exists) | App still uses `_call_azure_openai`. `AzureOpenAIClient` exists and is testable in isolation but not wired in. | Trivially revertable. |
| **After Step 3 (call sites swapped to `llm.complete`) — PARITY GATE** | App uses Azure OpenAI **via the abstraction layer**. Behavior must be byte-identical. `_call_azure_openai` is deleted. | Revertable to baseline by reverting the swap commit; the smoke test at Step 6 doesn't exist yet, so verification is manual. **Do not proceed if any tested query produces different output.** |
| After Step 4 (Anthropic adapter exists) | App still uses Azure (via abstraction). Anthropic adapter exists but is not selectable. | Revertable. |
| After Step 5 (classify_intent strict tools) | App still uses Azure for everything (since UI toggle doesn't exist yet). The strict-tools branch is dead code unless `provider_name == "anthropic_mgti"`. | Revertable. |
| After Step 6 (smoke test passes) | No app behavior change. We now have automated proof that both providers work end-to-end with real credentials. | n/a (no app change). |
| **After Step 7 (UI toggle live)** | App defaults to Azure (preserving today's behavior via `LLM_PROVIDER_DEFAULT`). User can switch to Anthropic via sidebar. | If Anthropic misbehaves, user (or env override) switches back to Azure with zero code change. |

At no point between Step 0 and Step 7 does the app stop working for Azure OpenAI users. That is the contract.

## Where the Smoke Test Slots In

`scripts/smoke_llm.py`. Runs as a standalone Python script (not a pytest test, because the repo has no pytest setup and this milestone is not the right time to introduce one). Exercises both adapters against real credentials read from `.env`. Two calls per provider: one `complete` (text round-trip), one `classify_with_tool` (strict tools round-trip).

It runs *between* Step 6 (existence) and Step 7 (UI). The smoke test is the gate that decides whether the UI toggle is safe to ship: if Anthropic's smoke test fails, the UI dropdown should not be exposed to users yet.

Long-term, it's also the script a developer runs after rotating credentials, switching MGTI environments, or upgrading the `eu.anthropic.claude-sonnet-4-5` model version — the cheapest possible verification that the integration still works.

## Sources

- `C:\mbrunoapp\snow_query\src\query_router.py` — current `_call_azure_openai`, `classify_intent`, `generate_executive_summary` shape (HIGH; direct read)
- `C:\mbrunoapp\snow_query\src\sql_generator.py` — current `_call_azure_openai` duplicate, `generate_sql` shape (HIGH; direct read)
- `C:\mbrunoapp\snow_query\src\utils.py` — `QueryError`, logging conventions, exception hierarchy (HIGH; direct read)
- `C:\mbrunoapp\snow_query\config.py` — current env var pattern, `python-dotenv` usage (HIGH; direct read)
- `C:\mbrunoapp\snow_query\app.py` — session state initialization, `process_query` call chain, sidebar structure (HIGH; direct read)
- `C:\mbrunoapp\snow_query\.planning\codebase\ARCHITECTURE.md` — confirms layered architecture and existing exception strategy (HIGH; just-mapped codebase)
- `C:\mbrunoapp\snow_query\.planning\codebase\CONVENTIONS.md` — module-level cache convention (`_model`, `_chroma_client`), file naming, type hint style, "from __future__ import annotations" convention (HIGH; just-mapped codebase)
- `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\SKILL.md` — MGTI Apigee/Bedrock proxy request shape (`/messages` suffix, `X-Api-Key`, `anthropic_version: "bedrock-2023-05-31"`, `eu.`-prefixed model, top-level `system`, required `max_tokens`, `guardrail_intervened` stop reason) (HIGH; authoritative for this integration)
- `typing.Protocol` (PEP 544) — structural subtyping in Python (HIGH; standard library)

---
*Architecture research for: multi-provider LLM abstraction refactor in snow_query*
*Researched: 2026-05-19*
