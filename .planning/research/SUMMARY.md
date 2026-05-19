# Project Research Summary

**Project:** snow_query — multi-provider LLM integration (Anthropic via MGTI Apigee/Bedrock proxy alongside Azure OpenAI)
**Domain:** Provider abstraction inside a layered Streamlit/Python app (`requests`-based HTTP, no vendor SDKs)
**Researched:** 2026-05-19
**Confidence:** HIGH

## Executive Summary

snow_query already has a working Azure OpenAI integration via raw `requests` (`_call_azure_openai`, duplicated across `query_router.py` and `sql_generator.py`). The milestone is to add Anthropic Claude — accessed through MGTI's Apigee front of AWS Bedrock — as a session-selectable alternative provider, without losing the existing OpenAI flow. Research across stack, features, architecture, and pitfalls converges on a single sequencing principle: **build the abstraction seam first against the existing OpenAI flow, prove byte-for-byte parity, then add Anthropic alongside.** Inverting that order — wiring Anthropic before extracting Azure into an adapter — is the highest-leverage way to spend 2–3x the engineering effort and end up with provider-specific `if` branches scattered across every call site.

The recommended approach is deliberately narrow: a `src/llm/` subpackage exposing a two-method interface (`complete` for text generation, `classify_with_tool` for strict-tools structured output), two concrete adapters speaking their providers' native HTTP shapes (not a translation layer), a `get_llm()` factory cached at module level, and per-request resolution via Streamlit session state. Only one new pip dependency is required (`jsonschema>=4.26.0,<5`, optional defence-in-depth for strict-tools), and `dataclasses` + `abc.ABC` + `requests` carry the rest. We explicitly exclude streaming, per-call provider routing, automatic failover, cost dashboards, semantic caches, and the official `anthropic` SDK — each rejection has documented reasoning tied to the app's single-user local-first deployment posture and the MGTI proxy's auth model.

The dominant risks are well-characterized and mostly addressable through phase ordering. The MGTI integration has 12 baseline transport-layer pitfalls already validated against the kbroles project (Quicks 008–012, May 2026) — `/messages` URL suffix, `X-Api-Key` header, `eu.`-prefix model IDs, top-level `system`, required `max_tokens`, `anthropic_version: bedrock-2023-05-31`, Bedrock guardrail handling. On top of those, multi-provider-specific pitfalls emerge: interface drift (abstraction leaking raw response shapes upward), strict-tools schema drift between providers, Streamlit session-state vs module-level config capture, default-provider rot when the inactive provider stops getting tested, and `chart_requested`/`chart_type` hallucination if naively added to the classification tool schema (they're heuristic outputs populated BEFORE the LLM call). The single highest-ROI mitigation across all of these is a runnable smoke test (`scripts/smoke_llm.py`) exercising both providers end-to-end against real credentials — codified in PROJECT.md as a hard prerequisite.

## Key Findings

### Recommended Stack

The milestone's stack delta is intentionally minimal — one optional pip dependency on top of the existing Python 3.11 / Streamlit / `requests` / `python-certifi-win32` foundation. No vendor SDKs, no async HTTP client, no pydantic, no LangChain. The MGTI proxy's `X-Api-Key` + `/messages` + `eu.`-prefix-model conventions are deliberately incompatible with the official `anthropic` SDK (which assumes `Authorization: Bearer` or SigV4), so raw `requests` is not just acceptable — it's the right call. See `STACK.md` for verified Claude model IDs (Sonnet 4.5 default; Sonnet 4.6 / Haiku 4.5 / Opus 4.7 as opt-in pending Hubble entitlement) and the conditional-omit logic required for Opus 4.7's dropped `temperature`/`top_p`/`top_k` parameters.

**Core technologies (new for this milestone):**
- **`requests` ≥2.31** (already pinned): HTTP client for both providers — zero churn, identical TLS stack, Windows cert-store integration via `python-certifi-win32` works unchanged for the new `apis.mmc.com` endpoint
- **`dataclasses` + `abc.ABC`** (Python 3.11 stdlib): `@dataclass(frozen=True, slots=True)` for provider configs and return types (`IntentResult`, `ToolCall`); `abc.ABC` with `@abstractmethod` for the `LLMProvider` interface — gives construction-time enforcement (`TypeError` at app boot, not `AttributeError` at first user query)
- **`jsonschema` ≥4.26.0,<5** (NEW, optional): Defence-in-depth validation of Anthropic strict-tools `tool_use.input` payloads; pure Python (~150 KB), Python ≥3.10 — recommended over pydantic (~5 MB compiled) since the project has zero pydantic today
- **Default Anthropic model:** `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` (only operator-validated value per MGTI skill provenance as of 2026-05-12)

### Expected Features

The feature landscape is dominated by **table stakes** — without them the milestone isn't actually selectable, safe, or debuggable. Differentiators are mostly LOW-complexity polish that should be pulled into v1 because they're cheap. Anti-features (streaming, per-call routing, failover, cost dashboards, direct API access, the official SDK) have explicit rejection reasoning grounded in the app's single-user local-first scope.

**Must have (table stakes — TS-1 through TS-14):**
- Provider abstraction (`LLMProvider` ABC with `complete` + `classify_with_tool`) — single seam, both adapters conform
- Two concrete adapters: Azure OpenAI (extracted from existing duplicated `_call_azure_openai`) + MGTI Anthropic (new)
- Sidebar provider dropdown with session-wide selection; env-var default
- Strict-tools structured output for `classify_intent` (eliminates the silent JSON-parse-fallback-to-heuristic cliff that exists today)
- MGTI request-shape correctness owned by the adapter: `/messages` suffix, `X-Api-Key`, top-level `system`, required `max_tokens`, `anthropic_version: bedrock-2023-05-31`, `eu.`-prefix model
- Typed error vocabulary (`LLMAuthError`, `LLMTransientError`, `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMConfigError`) mapped from HTTP responses at the adapter boundary
- Bedrock guardrail handling: `stop_reason == "guardrail_intervened"` → typed exception, NOT retry
- Fail-fast `validate_config()` at app boot for the default provider; lazy for the inactive one
- Smoke test (`scripts/smoke_llm.py`) — the single highest-ROI gate per the kbroles lesson; non-optional
- README + USER_GUIDE updates for provider selection

**Should have (pull into v1 — DF-1, DF-3, DF-5, DF-6, DF-7, DF-8, DF-9):**
- `X-Correlation-Id` per request, logged with app-side request ID (incident-response trace key per MGTI skill)
- Per-call token/usage logging via `logger.info` (no dashboard — that's anti-feature AF-3)
- `jsonschema` defence-in-depth on strict-tools responses
- Per-provider model name visible in sidebar
- `ANTHROPIC_TOOLS_SUPPORTED` env-flag escape hatch (strict-tools is undocumented in MGTI quickstart but works as of 2026-05-12 — fallback to text-mode + JSON parse if proxy regresses)
- `@st.cache_resource` for adapter instances (cache key includes provider + base_url + model + api_key_fingerprint)
- Credential-presence warning when user selects a provider lacking env vars

**Defer past v1 (DF-2, DF-4):**
- Retry with exponential backoff on transient errors (needs production signal to tune; defer until 429s appear in logs)
- Sidebar health-check button (depends on smoke test being stable)

**Explicit anti-features (NOT building — see FEATURES.md AF-1 through AF-13 for full reasoning):**
- Streaming responses, per-call automatic provider routing, cost dashboard, direct `api.anthropic.com` access, auto-failover, OpenAI-shape translation layer, official `anthropic` SDK, async LLM calls, semantic cache, plugin system, OpenTelemetry traces, mid-session provider switching mid-query, free-form `chat()` method

### Architecture Approach

Layered: UI (Streamlit) → orchestration (`query_router`, `sql_generator`) → **NEW** LLM abstraction (`src/llm/`) → network (`requests`). The abstraction is an `abc.ABC` with two methods (`complete`, `classify_with_tool`), two concrete adapters (`AzureOpenAIClient`, `AnthropicMGTIClient`), and a `get_llm()` factory cached at module level (same convention as `_model` / `_chroma_client` in `embeddings.py`). Adapters normalize at the boundary — call sites receive `str` or `ToolCall`, never raw HTTP JSON. `LLMError` at the adapter layer is caught at the call site and re-raised as `QueryError` (preserves existing exception contract; avoids cycle with `utils.py`).

**Major components:**
1. **`src/llm/base.py`** — `LLMClient` interface, `ToolSchema` / `ToolCall` / `IntentResult` dataclasses (frozen, slotted)
2. **`src/llm/azure_openai.py`** — Extracted from the duplicated `_call_azure_openai` in `query_router.py` + `sql_generator.py` (the two copies differ only in `max_tokens` 500 vs 1000); byte-identical behavior preserved
3. **`src/llm/anthropic_mgti.py`** — New adapter; handles `/messages` URL construction, `X-Api-Key`, top-level `system` extraction from messages, required `max_tokens`, `anthropic_version`, `eu.`-prefix validation, `guardrail_intervened` → `LLMGuardrailError`
4. **`src/llm/errors.py`** — Typed exception hierarchy; mapped from provider HTTP responses inside adapters
5. **`src/llm/__init__.py`** — `get_llm(provider)` factory with module-level cache; resolution order: explicit kwarg > session state > env default
6. **`scripts/smoke_llm.py`** — Standalone Python script (NOT pytest — repo has no test framework yet); round-trip both methods against real credentials for both providers
7. **Modified call sites:** `query_router.py` + `sql_generator.py` + `app.py` accept injected `llm: LLMClient` (defaulting to `get_llm()`); `config.py` adds `ANTHROPIC_*` env vars and `LLM_PROVIDER_DEFAULT`

The package name is **`src/llm/`** — NOT `src/providers/` (overloaded with "data provider"/"auth provider") and NOT stuffed into `src/utils.py` (LLM calls are a layer, not a utility). See ARCHITECTURE.md for the full rationale.

### Critical Pitfalls

The mgti-anthropic-integration skill already documents 12 baseline transport-layer pitfalls (Quicks 008–012 validated, 2026-05). On top of those, PITFALLS.md identifies 10 critical + 5 moderate multi-provider-specific issues. Top concerns ordered by how much they constrain phase ordering:

1. **Interface drift (PF-1)** — If the abstraction returns raw HTTP JSON, call sites grow `result["choices"][0]...` vs `result["content"][0]...` branches and the refactor is worthless. **Mitigation:** adapters return `str` / `ToolCall` only; lint rule grepping for `choices[` / `content[0][` outside adapter files. **Phase implication:** the seam must land before the Anthropic adapter integration with call sites.
2. **Strict-tools schema drift between providers (PF-2)** — OpenAI's `response_format` and Anthropic's `input_schema` describe the "same" classification, but the schemas drift in subtle ways (e.g. `detected_filters.priority: array | null` vs `: string`). The existing `chart_requested` / `chart_type` fields are populated by heuristic `_detect_chart_request()` BEFORE the LLM call (`query_router.py:163-164, 207-209`) — if naively added to the tool's `input_schema`, the LLM will hallucinate chart intent and overwrite the heuristic. **Mitigation:** single Python source-of-truth `ClassificationResult` dataclass; both providers' schemas/prompts derive from it; `chart_requested` stays OUT of the LLM schema.
3. **Phase ordering — seam first, Anthropic second (PF-1, PF-6, PF-9 collectively)** — Building the abstraction layer AFTER both adapters exist is a 2–3x rewrite. The seam includes the `LLMClient` interface, `Settings`-based config (replacing module-level constants), normalized logging schema, and typed errors — all must land before either adapter has provider-specific logic.
4. **Parity gate after Azure extraction (architecture Pattern 4)** — The first integration commit replaces `_call_azure_openai(messages)` with `llm.complete(messages)` where `llm` is the Azure adapter, byte-identical behavior, BEFORE Anthropic touches anything. If a tested query produces different output, stop. Don't proceed.
5. **Default-provider rot (PF-4)** — Default stays Azure per PROJECT.md, but if the dev's daily use and tests run with `LLM_PROVIDER=anthropic`, the OpenAI path silently rots. **Mitigation:** smoke test exercises both providers; `.env.example` default matches production default.
6. **Duplicated `_call_azure_openai` (PF-11)** — Currently defined twice (`query_router.py:105-141` and `sql_generator.py:86+`) with subtly different `max_tokens`. The refactor must enumerate all call sites via grep first, not from memory.
7. **Streamlit `@st.cache_resource` stale config (PF-10, PF-17)** — Cache key must include `(provider, base_url, model, api_key_fingerprint)`; sidebar needs a "Reload config" button; existing `@st.cache_*` decorators on LLM-dependent functions must include `provider` in their arguments.
8. **Bedrock guardrail handled as success (baseline #7 + PF-12)** — Bedrock returns HTTP 200 with `content: []` when guardrail blocks. Adapter MUST translate this to `LLMGuardrailError`; heuristic fallback MUST NOT silently route to the other provider (would bypass content policy by ricochet).
9. **Schema versioning (PF-8)** — `ClassificationResult` schema needs a version suffix (`V1`) from day one; cached / logged records include it; downstream dispatch handles `(version, intent)`, not bare `intent`. Retrofitting versioning later is painful.
10. **Mocks that lie (PF-5)** — Hand-written test fixtures don't match production wire format (MGTI proxy error envelope ≠ native Anthropic SDK shape). For this milestone, this manifests as: the smoke test MUST run against real credentials, not mocks. Per the kbroles lesson, smoke > unit for transport-layer bugs.

See PITFALLS.md for the full inventory including 5 moderate (env-var leakage, behavior drift between providers, `.env.example` drift, timeout mismatch, stage-vs-prod URL confusion) and 3 minor pitfalls plus tech-debt patterns, integration gotchas, performance traps, security mistakes, and UX pitfalls.

## Implications for Roadmap

The combined research strongly suggests a **5-phase structure** mirroring the build order in ARCHITECTURE.md, with a hard parity gate after Phase 2 and the smoke test gating Phase 5 (the UI toggle). Phases 1–2 are the seam-before-Anthropic discipline that prevents the dominant interface-drift pitfall. Phase 3 introduces Anthropic without UI exposure. Phase 4 adds strict-tools and the smoke test. Phase 5 is the user-visible flip.

### Phase 1: Build the Abstraction Seam (no behavior change)

**Rationale:** Per ARCHITECTURE.md build order Step 1 and PITFALLS.md PF-1 / PF-6 / PF-9 — the interface, typed errors, normalized logging schema, and `Settings`-based config must land BEFORE either adapter has provider-specific logic. Building this AFTER both adapters exist is a 2–3x rewrite.
**Delivers:** `src/llm/__init__.py`, `src/llm/base.py`, `src/llm/errors.py`, `LLMClient` interface (ABC with `complete` + `classify_with_tool`), `ToolSchema`/`ToolCall`/`IntentResult` dataclasses (frozen, slotted), `LLMError` hierarchy (`LLMAuthError`, `LLMTransientError`, `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMConfigError`), `get_llm()` factory stub (only `azure_openai` supported initially), `ClassificationResultV1` schema with version suffix, normalized log record schema, `Settings` object replacing module-level constants in `config.py`, `validate_config()` startup validator.
**Addresses:** TS-1 (interface), TS-11 (error vocabulary), TS-13 (fail-fast config), schema versioning (PF-8 prerequisite).
**Avoids:** PF-1 (interface drift), PF-6 (env-var leakage), PF-9 (logging inconsistency), PF-13 (`.env.example` drift).

### Phase 2: Extract Azure OpenAI Adapter + Parity Gate

**Rationale:** Per ARCHITECTURE.md build order Steps 2–3 (parity-first refactor — Pattern 4). The Azure adapter is a literal extraction of today's duplicated `_call_azure_openai` (same URL, same `api-key` header, same payload, same timeout). Then call sites swap `_call_azure_openai(messages)` → `llm.complete(messages, ...)`. **Hard parity gate:** run 5–10 representative queries through the app, outputs MUST be byte-identical to pre-refactor. If they aren't, stop and debug before introducing Anthropic.
**Delivers:** `src/llm/azure_openai.py` (`AzureOpenAIClient.complete()` + initial `classify_with_tool` via JSON-in-prompt preserving existing behavior); modified `query_router.py` + `sql_generator.py` accepting injected `llm` kwarg; `_call_azure_openai` deleted from both files.
**Addresses:** TS-2 (Azure adapter), PF-11 (`_call_azure_openai` duplication — first task: grep all references).
**Avoids:** PF-1 (interface drift caught early via parity gate), PF-11 (duplication), interface-drift regression.

### Phase 3: Anthropic MGTI Adapter (not yet UI-exposed)

**Rationale:** Per ARCHITECTURE.md Step 4 — once the seam is proven against Azure, Anthropic gets added alongside without UI exposure. Adapter encapsulates ALL 12 baseline MGTI pitfalls (`/messages` suffix, `X-Api-Key`, `anthropic_version: bedrock-2023-05-31`, top-level `system` extracted from messages, required `max_tokens`, `eu.`-prefix model validation, `guardrail_intervened` → `LLMGuardrailError`, MGTI proxy error envelope mapping). Conditional omit of `temperature`/`top_p`/`top_k` for `eu.anthropic.claude-opus-4-7*` models.
**Delivers:** `src/llm/anthropic_mgti.py` (`AnthropicMGTIClient.complete()` text-mode; strict-tools deferred to Phase 4); `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_VERSION`, `ANTHROPIC_MAX_TOKENS`, `ANTHROPIC_TIMEOUT` in `Settings` and `.env.example`; `X-Correlation-Id` generation per call; `get_llm("anthropic_mgti")` returns instantiable adapter.
**Addresses:** TS-2 (Anthropic adapter), TS-4 (env vars), TS-7 (URL suffix in adapter), TS-8 (system/max_tokens/anthropic_version), TS-9 (auth header), TS-12 (guardrail mapping), DF-1 (correlation IDs).
**Avoids:** All 12 baseline MGTI pitfalls (encapsulated in adapter); PF-1 (Anthropic shape stays inside adapter); PF-15 (startup URL log).

### Phase 4: Strict-Tools Mode + Smoke Test (gate)

**Rationale:** Per ARCHITECTURE.md Steps 5–6. Strict-tools is the Anthropic-only optimization for `classify_intent` — eliminates the JSON-parse-fallback-to-heuristic cliff. The smoke test is the gate that decides whether Phase 5 (UI toggle) is safe to ship — codified as non-optional in PROJECT.md and PITFALLS.md tech-debt table. Critical: `chart_requested`/`chart_type` stay OUT of the tool's `input_schema` (they're populated by `_detect_chart_request()` heuristic before the LLM call).
**Delivers:** `INTENT_TOOL: ToolSchema` derived from `ClassificationResultV1` (single Python source of truth, NOT hand-written JSON); `AnthropicMGTIClient.classify_with_tool()` using `tools` + `tool_choice={"type": "tool", "name": ...}` + `disable_parallel_tool_use`; `classify_intent` branches on `llm.provider_name`; defence-in-depth `jsonschema.validate` on tool_use input; `ANTHROPIC_TOOLS_SUPPORTED` escape-hatch env flag (DF-7); `scripts/smoke_llm.py` exercising `complete` + `classify_with_tool` against both providers; updated `requirements.txt` (`jsonschema>=4.26.0,<5`).
**Addresses:** TS-5 (strict tools CS1), TS-10 (smoke test), DF-5 (jsonschema defence-in-depth), DF-7 (tools escape hatch), DF-3 (usage logging).
**Avoids:** PF-2 (schema drift — single source of truth + `chart_requested` stays out), PF-5 (mocks lie — smoke test gates with real credentials), PF-8 (schema versioning baked in), PF-12 (heuristic fallback policy explicit: only on `network_error`/`timeout`/`auth_error`/`guardrail`, NOT silently to other provider).

### Phase 5: Sidebar UI Toggle + Documentation

**Rationale:** Per ARCHITECTURE.md Step 7 — UI is LAST. The dropdown is useless and dangerous before the smoke test passes. Defaults to `LLM_PROVIDER_DEFAULT=azure_openai` to preserve today's behavior; user opts into Anthropic explicitly.
**Delivers:** `st.selectbox` in sidebar; `st.session_state["llm_provider"]` initialized from env default; `app.py::process_query` resolves `llm = get_llm(st.session_state["llm_provider"])` and passes to `route_query`; `@st.cache_resource` keyed correctly (PF-10); credential-presence warning (DF-9); model name displayed (DF-6); "Reload config" button; README + USER_GUIDE updated; provider name visible on assistant messages (UX pitfall).
**Addresses:** TS-3 (sidebar dropdown), TS-14 (docs), DF-6 (model in UI), DF-8 (cache_resource), DF-9 (credential warning).
**Avoids:** PF-3 (session-state vs module-level config), PF-10 (cache staleness), PF-16 (doc drift), PF-17 (Streamlit cache invalidation on provider switch), PF-18 (error message UX).

### Phase Ordering Rationale

- **Seam before adapter before integration before UI** is the single most important sequencing principle from research. Both ARCHITECTURE.md (Pattern 4: parity-first refactor) and PITFALLS.md (PF-1, PF-6, PF-9 phase-to-phase mapping table) independently arrive at this conclusion.
- **Parity gate after Phase 2 is non-negotiable.** The Azure adapter is a literal extraction. If outputs change, the abstraction has a bug that will compound once Anthropic lands. Catching it at Phase 2 isolates the cause.
- **Smoke test gates Phase 5, not Phase 4.** The smoke test exists *after* Anthropic logic but *before* user exposure. Per kbroles lesson: smoke > unit for transport-layer bugs. Without it, baseline pitfalls #1, #2, #4 (URL suffix, model prefix, system placement) ship to users.
- **Phase 4 is where multi-provider-specific complexity peaks** (schema sourcing, strict-tools, heuristic-fallback policy, tools escape hatch). Front-loading the seam (Phase 1) and the parity-tested Azure path (Phase 2) means Phase 4's complexity is isolated to one provider's path through the existing infrastructure.
- **The duplicated `_call_azure_openai` (PF-11) is handled at Phase 2 by grep-then-migrate**, not by memory. First task of Phase 2: `grep -rn "_call_azure_openai\|AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT"` and enumerate every hit.

### Research Flags

Phases likely needing deeper research during planning (`/gsd:research-phase`):

- **Phase 4 (strict-tools mode):** The MGTI proxy's tool-use behavior is "works as of 2026-05-12 but undocumented in quickstart" (baseline #10) and the `chart_requested`/`chart_type` heuristic interaction with the tool schema needs careful review of `query_router.py:163-164, 207-209`. Also worth verifying: does the MGTI proxy strip Anthropic's `usage` block, and does it pass through `X-Correlation-Id` to logs? Both affect observability design (DF-1, DF-3).
- **Phase 3 (Anthropic adapter):** While the MGTI skill is operator-validated, the Opus 4.7 conditional-omit logic (`temperature`/`top_p`/`top_k` dropped, only `thinking.type: "adaptive"` supported) is new behavior that hasn't yet been exercised in production. If Opus 4.7 ends up in scope as a selectable model, validate the request-builder branch.

Phases with standard patterns (skip research-phase):

- **Phase 1 (abstraction seam):** Standard adapter-pattern + ABC + dataclass mechanics. Codebase conventions are clear (module-level cache like `_model` / `_chroma_client` in `embeddings.py`). No external research needed.
- **Phase 2 (Azure extraction + parity gate):** Pure refactor of existing code. The only research needed is `grep` to enumerate call sites.
- **Phase 5 (UI toggle + docs):** Streamlit `st.selectbox` + `st.session_state` + `@st.cache_resource` are well-understood. The `@st.cache_*` audit needs the `provider` argument added where missing — mechanical change.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All Claude model IDs verified against AWS Bedrock model card pages 2026-05-19; MGTI integration shape operator-validated via kbroles Quicks 008–012; `jsonschema 4.26.0` PyPI-verified; absence of pydantic/boto3/anthropic-sdk in codebase confirmed via direct `requirements.txt` inspection. |
| Features | HIGH | Industry pattern verification across multiple 2026 sources (LiteLLM, AbstractCore, Instructor, Portkey, etc.) — multi-provider strategy, error normalization, correlation IDs, and rejection of streaming/failover/cache for single-user local apps all show multi-source agreement. PROJECT.md decisions explicitly aligned. |
| Architecture | HIGH | Grounded in direct codebase inspection (`query_router.py`, `sql_generator.py`, `utils.py`, `config.py`, `app.py`, codebase-mapping artifacts in `.planning/codebase/`); build order is mechanical from existing call sites + the parity-first refactor pattern. Provider abstraction choice (`abc.ABC` over `typing.Protocol`) explicitly defended in STACK.md against this codebase's "fail fast at startup" convention. |
| Pitfalls | HIGH | 12 baseline pitfalls are kbroles-validated (Quicks 008–012, 2026-05-11/12, operator confirmation). Multi-provider extensions grounded in direct code inspection of the duplicated `_call_azure_openai`, the heuristic chart detection in `query_router.py:163-164`, the JSON-parse-fallback path, and Streamlit `@st.cache_resource` semantics. |

**Overall confidence:** HIGH

### Gaps to Address

- **MGTI proxy strict-tools support stability** — Validated as working 2026-05-12 but undocumented in quickstart. Mitigated by `ANTHROPIC_TOOLS_SUPPORTED` env-flag escape hatch (DF-7); if proxy regresses, flip to text-mode + JSON parse. Worth verifying at Phase 4 against the current stage endpoint before relying on it for production.
- **Hubble app entitlement for non-Sonnet-4.5 models** — Sonnet 4.6 / Haiku 4.5 / Opus 4.7 are confirmed valid on Bedrock itself, but Hubble entitlement may not yet permit them. Treat as "ship as a config option" but document the expected `Model not supported` 404 response if entitlement is missing. Validate per-model before adding to the sidebar selector.
- **MGTI proxy `usage` block pass-through** — Anthropic returns `usage: {input_tokens, output_tokens}` natively; unclear whether the MGTI proxy strips, modifies, or passes through. Affects token-cost logging design (DF-3). Resolve at Phase 3 by capturing a real response from stage and inspecting the proxy response shape.
- **MGTI proxy `X-Correlation-Id` echo** — DF-1 assumes the proxy logs the correlation ID alongside Bedrock's request ID. Verify at Phase 3 with a deliberate correlation-ID test call and proxy-log inspection.
- **No test framework in repo today** — Per `.planning/codebase/TESTING.md`, the project has no pytest setup. Smoke test is a standalone Python script per ARCHITECTURE.md decision, NOT a pytest test. The milestone's verification posture is: parity gate (manual diff) + smoke test (automated round-trip) + grep-based completion verification.
- **`chart_requested` / `chart_type` schema-vs-heuristic interaction** — These fields are populated by `_detect_chart_request()` heuristic BEFORE the LLM call (`query_router.py:163-164, 207-209`). If naively added to the tool's `input_schema`, the LLM will hallucinate chart intent. Confirm at Phase 4 that the `ClassificationResultV1` LLM schema OMITS these two fields, and that the call-site code merges heuristic results AFTER receiving the LLM output.

## Sources

### Primary (HIGH confidence)

- AWS Bedrock model card pages (Sonnet 4.5, Sonnet 4.6, Haiku 4.5, Opus 4.7) — model IDs, context windows, max output tokens, Opus 4.7 parameter restrictions; verified 2026-05-19
- AWS Bedrock Messages API + inference profiles documentation — `anthropic_version: "bedrock-2023-05-31"` requirement, `eu.` prefix routing semantics
- `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\SKILL.md` — operator-validated against kbroles Quicks 008–012 (commit `4477a7e` of `mmctech/coreapi-apigee`, 2026-05-11/12); authoritative for MGTI request shape, 12 baseline pitfalls, smoke test pattern, strict-tools confirmation, error envelope shape, correlation-ID rationale
- `C:\mbrunoapp\snow_query\` codebase direct read — `src/query_router.py` (CS1 + CS3 implementation, `_call_azure_openai` duplicate, `_heuristic_classify` fallback, `_detect_chart_request` heuristic at lines 163-164, 207-209), `src/sql_generator.py` (CS2 implementation, second `_call_azure_openai` duplicate), `src/utils.py` (`QueryError` shape), `config.py` (env-var pattern), `app.py` (session-state, sidebar)
- `.planning/codebase/` artifacts — ARCHITECTURE.md, CONVENTIONS.md, CONCERNS.md, INTEGRATIONS.md, STACK.md, TESTING.md from the just-completed codebase mapping
- `.planning/PROJECT.md` — milestone scope, key decisions (MGTI-only, session-wide selection, default Azure, strict-tools for classify, smoke test mandatory, abstraction over per-call branches)
- `jsonschema 4.26.0` on PyPI — version, Python ≥3.10 requirement, pure-Python distribution verified
- `typing.Protocol` PEP 544 — standard-library structural subtyping reference (alternative considered; ABC chosen)

### Secondary (MEDIUM confidence — multi-source agreement)

- 2026 industry guides on multi-provider LLM abstractions: Interoperability Patterns (brics-econ.org), LLM API Comparison 2026 (myengineeringpath.dev), Unifying 3 LLM APIs in Python (dev.to/inozem), llm_api_adapter (GitHub Inozem), AbstractCore (GitHub lpalbou), LiteLLM Multi-Provider Support (deepwiki)
- Structured-output pattern references: Structured Outputs Practical Guide 2026 (Techsy), DeepFounder 2026 guide, Structured Output Comparison across LLM providers (Glukhov on Medium)
- Resilience and observability references: LLM API Resilience in Production (TianPan), Complete Guide to LLM Observability for 2026 (Portkey), LLM Error Handling and Fallback (BuildMVPFast)
- Python typing best practices (2026) — community consensus on dataclass-for-trusted-internal-data, TypedDict-for-static-only, pydantic-for-trust-boundary

### Tertiary (LOW confidence — single source / inference)

- Streamlit `@st.cache_resource` / `@st.cache_data` behavior across versions ≥1.40 — version-dependent; verify against deployed Streamlit version
- MGTI proxy `usage` block pass-through and `X-Correlation-Id` echo behavior — inferred from MGTI skill but not directly tested; resolve at Phase 3 with real stage-endpoint fixtures
- Hubble app entitlement coverage for Sonnet 4.6 / Haiku 4.5 / Opus 4.7 — Bedrock-side IDs verified, app-side entitlement per-deployment

---
*Research completed: 2026-05-19*
*Ready for roadmap: yes*
