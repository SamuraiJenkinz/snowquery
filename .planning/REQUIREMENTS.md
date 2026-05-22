# Requirements: snow_query — Multi-Provider LLM Integration

**Defined:** 2026-05-19
**Core Value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.

## v1 Requirements

Requirements for this milestone (adding Anthropic Claude as a selectable provider alongside Azure OpenAI). Each maps to a roadmap phase.

### Abstraction (ABS)

- [x] **ABS-01**: `src/llm/` subpackage exists with `__init__.py`, `base.py`, `errors.py`, `azure_openai.py`, `anthropic_mgti.py`
- [x] **ABS-02**: `LLMClient` ABC defines exactly two methods: `complete(messages: list[dict], *, max_tokens: int = 500, temperature: float = 0.1, **kwargs) -> str` and `classify_with_tool(messages: list[dict], tool: ToolSchema, *, tool_name: str, **kwargs) -> ToolCall` — `system` prompts stay inline in `messages` with `role: "system"` (Anthropic adapter extracts and promotes to top-level internally; preserves parity with current Azure call sites)
- [x] **ABS-03**: `ToolSchema`, `ToolCall`, and `IntentResult` are `@dataclass(frozen=True, slots=True)` types used at the adapter boundary
- [x] **ABS-04**: `get_llm(provider: str) -> LLMClient` factory with module-level instance cache; resolution order is explicit kwarg > Streamlit session state > `LLM_PROVIDER_DEFAULT` env var
- [x] **ABS-05**: Adapters return only `str` or `ToolCall` — raw HTTP JSON never crosses the adapter boundary
- [ ] **ABS-06**: `_call_azure_openai` is removed from `src/query_router.py` and `src/sql_generator.py`; all three LLM call sites consume `LLMClient` via dependency injection

### Adapters (ADP)

- [ ] **ADP-01**: `AzureOpenAIClient` implements both `LLMClient` methods; `complete` preserves byte-identical output to today's `_call_azure_openai` for the same input (parity gate)
- [ ] **ADP-02**: `AzureOpenAIClient.classify_with_tool` initially uses prompt-based JSON parsing to preserve existing Azure OpenAI behavior — no provider-side strict-tools requirement on the OpenAI path in v1
- [ ] **ADP-03**: `AnthropicMGTIClient.complete` calls `POST {base_url}/model/{model}/messages` with `X-Api-Key`, `Content-Type: application/json`, `X-Correlation-Id`, and a fresh UUID per call
- [ ] **ADP-04**: `AnthropicMGTIClient` body shape is correct: `anthropic_version: "bedrock-2023-05-31"`, top-level `system`, `max_tokens` required, `temperature` honored
- [ ] **ADP-05**: `AnthropicMGTIClient` validates the configured model name starts with `eu.anthropic.claude-` and raises `LLMConfigError` at construction otherwise
- [ ] **ADP-06**: `AnthropicMGTIClient` omits `temperature`, `top_p`, and `top_k` from the request body when the model name matches `eu.anthropic.claude-opus-4-7*`
- [x] **ADP-07**: `AnthropicMGTIClient.classify_with_tool` uses Anthropic strict-tools: `tools=[tool]`, `tool_choice={"type": "tool", "name": tool.name, "disable_parallel_tool_use": True}`
- [ ] **ADP-08**: `AnthropicMGTIClient` translates `stop_reason == "guardrail_intervened"` into `LLMGuardrailError` (HTTP 200 response with empty content does NOT count as success)
- [x] **ADP-09**: `AnthropicMGTIClient` extracts `tool_use` block input from a strict-tools response and returns it as a `ToolCall`; missing tool_use block raises `LLMSchemaError`

### Configuration (CFG)

- [x] **CFG-01**: `config.py` exposes a `Settings` object (or equivalent module-level constants) with all existing Azure OpenAI fields plus new Anthropic fields
- [ ] **CFG-02**: New env vars: `LLM_PROVIDER_DEFAULT`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_VERSION`, `ANTHROPIC_MAX_TOKENS`, `ANTHROPIC_TEMPERATURE`, `ANTHROPIC_TIMEOUT_S`, `ANTHROPIC_TOOLS_SUPPORTED`
- [x] **CFG-03**: `validate_config(provider)` is called at app boot for the default provider; raises `LLMConfigError` with a human-readable list of missing variables
- [ ] **CFG-04**: `.env.example` (or equivalent template) is updated with the new variables and documented defaults
- [x] **CFG-05**: `LLM_PROVIDER_DEFAULT` defaults to `azure_openai` so existing deployments are byte-identical after upgrade
- [x] **CFG-06**: `jsonschema>=4.26.0,<5` is added to `requirements.txt`

### Errors (ERR)

- [x] **ERR-01**: `src/llm/errors.py` defines `LLMError` plus `LLMAuthError`, `LLMTransientError`, `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMConfigError`
- [ ] **ERR-02**: Adapters map HTTP responses to these typed errors at the adapter boundary (401/403 → `LLMAuthError`; 429/5xx → `LLMTransientError`; `requests.Timeout` → `LLMTimeoutError`; missing/invalid response shape → `LLMSchemaError`)
- [ ] **ERR-03**: Anthropic MGTI proxy error envelope `{"error": {"title", "detail", "status"}}` is handled (not assumed to match the native Anthropic SDK shape)
- [ ] **ERR-04**: Call sites in `query_router.py` and `sql_generator.py` catch `LLMError` and re-raise as the existing `QueryError` — preserving the current exception contract

### Tools & Schema (TOOL)

- [x] **TOOL-01**: `ClassificationResultV1` dataclass (frozen, slotted) is the single Python source of truth for intent-classification output; `IntentResult` is built from it
- [x] **TOOL-02**: `INTENT_TOOL` (`ToolSchema`) is derived programmatically from `ClassificationResultV1` — no hand-written JSON schema duplication
- [x] **TOOL-03**: `chart_requested` and `chart_type` are NOT in the LLM tool's `input_schema`; they continue to be populated by the heuristic `_detect_chart_request()` before the LLM call
- [x] **TOOL-04**: `classify_intent` receives the heuristic-populated `chart_requested`/`chart_type` and merges them with the LLM result; LLM output cannot overwrite the heuristic for these two fields
- [x] **TOOL-05**: When `ANTHROPIC_TOOLS_SUPPORTED=false`, `AnthropicMGTIClient.classify_with_tool` falls back to text mode + JSON parse — escape hatch if MGTI proxy regresses on tool pass-through
- [x] **TOOL-06**: Strict-tools responses are validated with `jsonschema.validate` against the same `INTENT_TOOL.input_schema` before being returned as a `ToolCall` (defence-in-depth)
- [ ] **TOOL-07**: `generate_sql` and `generate_executive_summary` use only `complete()` (text mode) on both providers — no tool-use wrapping

### Observability (OBS)

- [ ] **OBS-01**: Every Anthropic request includes a freshly generated `X-Correlation-Id` header; the same UUID is logged with the app-side request log via `logger.info`
- [ ] **OBS-02**: Adapters log a single structured event per call: provider name, model, latency in ms, input/output token counts when available, correlation ID, outcome (success / typed-error-class)
- [x] **OBS-03**: API keys are NEVER logged (no full key, no key prefix, no `repr(Settings)` that includes keys)
- [ ] **OBS-04**: Configured base URL is logged once at app startup (helps catch stage-vs-prod misconfiguration)

### UI (UI)

- [x] **UI-01**: Sidebar contains an `st.selectbox` labeled "LLM provider" with options "Azure OpenAI" and "Anthropic Claude (MGTI)"
- [x] **UI-02**: Selected provider is stored in `st.session_state["llm_provider"]` and initialized from `LLM_PROVIDER_DEFAULT` env on first session
- [x] **UI-03**: Currently active model name is displayed under the provider selector (read-only)
- [x] **UI-04**: Switching the provider mid-session takes effect on the next user query (not retroactively on in-flight or historical results)
- [x] **UI-05**: Selecting a provider whose required env vars are missing shows a clear inline warning in the sidebar and prevents query submission while the warning is active
- [x] **UI-06**: `@st.cache_resource`-decorated adapter instances are keyed on `(provider, base_url, model, api_key_fingerprint)`; selecting a different provider re-resolves the adapter
- [x] **UI-07**: Every assistant message displays which provider produced it (e.g. small caption with provider + model)

### Smoke Test (SMK)

- [x] **SMK-01**: `scripts/smoke_llm.py` exists; runnable as `python scripts/smoke_llm.py [--provider azure_openai|anthropic_mgti|both]`
- [x] **SMK-02**: For each selected provider, smoke test exercises BOTH `complete()` and `classify_with_tool()` against the live endpoint using credentials from `.env`
- [x] **SMK-03**: For Anthropic, smoke test additionally hits the service-info `GET /coreapi/llm/anthropic/v1/` endpoint to confirm gateway reachability (the kbroles-validated first-step diagnostic)
- [x] **SMK-04**: Smoke test prints clear pass/fail per check with the captured response shape; exits non-zero on any failure
- [x] **SMK-05**: Smoke test must pass for both providers before the sidebar dropdown is wired (gates Phase 5)

### Documentation (DOC)

- [x] **DOC-01**: README updated with the provider selection feature, sidebar location, default behavior, and supported Claude models
- [x] **DOC-02**: USER_GUIDE updated with how to switch providers, expected behavior differences, and what to do when a provider warning appears
- [x] **DOC-03**: Document the MGTI-only constraint (no direct Anthropic API in this app context) and the Hubble onboarding link for future operators
- [x] **DOC-04**: Document how to run the smoke test and when to do it (any time `.env` Anthropic vars change; before every prod deploy)

## v2 Requirements

Deferred to a future milestone. Tracked but not in current roadmap.

### Resilience (RES)

- **RES-01**: Retry with exponential backoff on `LLMTransientError` (429 / 5xx) — defer until production logs show signal
- **RES-02**: Sidebar "test connection" button that runs a minimal Create Message call and reports latency — depends on smoke test stability

### Provider features (PRV)

- **PRV-01**: Per-call-site model selection (e.g. Haiku for `classify_intent`, Sonnet for `generate_executive_summary`) — needs production cost/latency data before scoping
- **PRV-02**: Opus 4.7 support with `thinking.type: "adaptive"` — pending Hubble entitlement and tested use case

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Direct `api.anthropic.com` access | Not authorized in MMC corporate app context; MGTI proxy only |
| Claude models below 4.5 | MGTI proxy returns `404 Model not supported`; not a snow_query choice |
| Per-call automatic provider routing | Adds complexity with no proven payoff; user picks one provider per session |
| Removing Azure OpenAI | Both providers stay first-class; no migration |
| Streaming responses (Server-Sent Events) | Current call sites are request/response; streaming would require new UI plumbing |
| Official `anthropic` Python SDK | Incompatible with `X-Api-Key` auth + MGTI URL shape; raw `requests` is the correct path |
| Auto-failover between providers | Would silently bypass content policy (guardrails); user must consciously switch |
| OpenAI-shape translation layer | Each adapter speaks its provider's native shape; no compatibility middleware |
| Cost dashboard / usage analytics across providers | Token logging via `logger.info` is sufficient for v1; defer dashboards |
| Semantic cache of LLM responses | App-level caching would compromise data-privacy invariants |
| Streamlit plugin system for additional providers | Two providers only; YAGNI |
| OpenTelemetry trace export | Log-based correlation IDs are sufficient for single-user local-first app |
| Mid-session provider switching mid-query (e.g. retry with the other provider) | Confusing behavior; user-initiated swap-then-resend is the explicit pattern |
| Free-form `chat(message)` method on the interface | Not what the existing call sites need; would invite shape drift |
| Embedding-model swap to Bedrock embeddings | Local `sentence-transformers` stays for data-privacy reasons |
| Async LLM calls | Streamlit is synchronous; no benefit until we move off it |
| Async migration of `query_router.py` | Out of scope for this milestone |
| Porting `app_brutalist.py` / `fixedapp.py` / `designui.py` variants | They may consume the new abstraction later; not in scope here |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ABS-01 | Phase 1 | Complete |
| ABS-02 | Phase 1 | Complete |
| ABS-03 | Phase 1 | Complete |
| ABS-04 | Phase 1 | Complete |
| ABS-05 | Phase 1 | Complete |
| ABS-06 | Phase 2 | Complete |
| ADP-01 | Phase 2 | Complete |
| ADP-02 | Phase 2 | Complete |
| ADP-03 | Phase 3 | Pending |
| ADP-04 | Phase 3 | Pending |
| ADP-05 | Phase 3 | Pending |
| ADP-06 | Phase 3 | Pending |
| ADP-07 | Phase 4 | Complete |
| ADP-08 | Phase 3 | Pending |
| ADP-09 | Phase 4 | Complete |
| CFG-01 | Phase 1 | Complete |
| CFG-02 | Phase 3 | Pending |
| CFG-03 | Phase 1 | Complete |
| CFG-04 | Phase 3 | Pending |
| CFG-05 | Phase 1 | Complete |
| CFG-06 | Phase 1 | Complete |
| ERR-01 | Phase 1 | Complete |
| ERR-02 | Phase 3 | Pending |
| ERR-03 | Phase 3 | Pending |
| ERR-04 | Phase 2 | Complete |
| TOOL-01 | Phase 1 | Complete |
| TOOL-02 | Phase 4 | Complete |
| TOOL-03 | Phase 4 | Complete |
| TOOL-04 | Phase 4 | Complete |
| TOOL-05 | Phase 4 | Complete |
| TOOL-06 | Phase 4 | Complete |
| TOOL-07 | Phase 3 | Pending |
| OBS-01 | Phase 3 | Pending |
| OBS-02 | Phase 2 | Complete |
| OBS-03 | Phase 1 | Complete |
| OBS-04 | Phase 3 | Pending |
| UI-01 | Phase 5 | Complete |
| UI-02 | Phase 5 | Complete |
| UI-03 | Phase 5 | Complete |
| UI-04 | Phase 5 | Complete |
| UI-05 | Phase 5 | Complete |
| UI-06 | Phase 5 | Complete |
| UI-07 | Phase 5 | Complete |
| SMK-01 | Phase 4 | Complete |
| SMK-02 | Phase 4 | Complete |
| SMK-03 | Phase 4 | Complete |
| SMK-04 | Phase 4 | Complete |
| SMK-05 | Phase 4 | Complete (live execution pending operator) |
| DOC-01 | Phase 5 | Complete |
| DOC-02 | Phase 5 | Complete |
| DOC-03 | Phase 5 | Complete |
| DOC-04 | Phase 5 | Complete |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0

**Per-phase totals:**
- Phase 1 (Abstraction Seam): 12 requirements
- Phase 2 (Azure Extraction + Parity Gate): 5 requirements
- Phase 3 (Anthropic MGTI Adapter): 12 requirements
- Phase 4 (Strict-Tools + Smoke Test): 12 requirements
- Phase 5 (Sidebar UI Toggle + Documentation): 11 requirements

---
*Requirements defined: 2026-05-19*
*Last updated: 2026-05-22 — Phase 5 (Sidebar UI Toggle + Documentation) requirements marked Complete*
