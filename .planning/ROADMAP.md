# Roadmap: snow_query — Multi-Provider LLM Integration

## Overview

This milestone adds Anthropic Claude (via MGTI Apigee/Bedrock proxy) as a session-selectable provider alongside the existing Azure OpenAI integration. The five-phase structure follows a strict **seam → Azure extraction (parity-tested) → Anthropic adapter (no UI) → strict-tools + smoke test → UI toggle** sequence. The abstraction seam lands first against the existing OpenAI flow to prevent interface drift; a hard parity gate after Phase 2 confirms byte-identical Azure behavior before Anthropic is introduced; the smoke test gates Phase 5 so users never see a provider toggle that hasn't been live-tested end-to-end. The existing Azure OpenAI flow remains functional and default-selected throughout — no behavior change for current users until the user explicitly opts into Anthropic in Phase 5.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Abstraction Seam** — Build `src/llm/` interface, typed errors, dataclasses, config foundation (no behavior change)
- [x] **Phase 2: Azure Extraction + Parity Gate** — Extract existing Azure OpenAI flow into adapter; swap call sites; verify byte-identical output
- [x] **Phase 3: Anthropic MGTI Adapter** — Add Anthropic adapter with text-mode `complete()`, correlation IDs, typed error mapping (no UI exposure)
- [x] **Phase 4: Strict-Tools + Smoke Test** — Strict-tools mode for intent classification; live-credential smoke test gating Phase 5
- [ ] **Phase 5: Sidebar UI Toggle + Documentation** — User-facing provider dropdown; README + USER_GUIDE updated

## Phase Details

### Phase 1: Abstraction Seam

**Goal**: Establish the provider-agnostic interface and supporting types in `src/llm/` so all subsequent provider work plugs into a stable seam. No call sites change yet; no behavior change ships.

**Depends on**: Nothing (first phase)

**Requirements**: ABS-01, ABS-02, ABS-03, ABS-04, ABS-05, ERR-01, TOOL-01, CFG-01, CFG-03, CFG-05, CFG-06, OBS-03

**Success Criteria** (what must be TRUE):
  1. `src/llm/` package exists with `__init__.py`, `base.py`, `errors.py` and is importable from a Python REPL inside the project venv
  2. `LLMClient` ABC enforces the two-method contract (`complete`, `classify_with_tool`) at construction time — instantiating a subclass missing either method raises `TypeError`
  3. `get_llm(provider)` returns a cached `LLMClient`, resolving the provider per the explicit-kwarg > session-state > env-default order; `LLM_PROVIDER_DEFAULT` falls back to `azure_openai`
  4. `validate_config(provider)` raises `LLMConfigError` listing every missing variable for the requested provider when called at app boot
  5. No log line or `repr()` output across the package exposes an API key in any form (full, prefix, or fingerprint pre-image)

**Plans**:
- [x] 01-PLAN-01-package-skeleton.md - Create src/llm/ package skeleton: __init__.py, base.py (LLMClient ABC), errors.py (6 typed errors), types.py (4 frozen+slots dataclasses)
- [x] 01-PLAN-02-config-factory-stubs.md - Wire LLMSettings + validate_config (src/llm/config.py), get_llm factory with lazy-import registry (src/llm/__init__.py), adapter stubs (azure_openai.py, anthropic_mgti.py), add jsonschema to requirements.txt
- [x] 01-PLAN-03-smoke-verification.md - tests/test_llm_seam.py: pytest module proving all 5 Phase 1 success criteria with zero live external dependencies

### Phase 2: Azure Extraction + Parity Gate

**Goal**: Extract the duplicated `_call_azure_openai` logic into `AzureOpenAIClient` and route the three call sites through `LLMClient`, with a hard verification step that 5–10 representative queries produce byte-identical output to the pre-refactor baseline.

**Depends on**: Phase 1

**Requirements**: ABS-06, ADP-01, ADP-02, ERR-04, OBS-02

**Success Criteria** (what must be TRUE):
  1. `_call_azure_openai` is gone from `src/query_router.py` and `src/sql_generator.py` (grep returns zero hits); all three call sites consume `LLMClient` via dependency injection
  2. Five representative queries (covering structured / semantic / hybrid intents and the executive-summary path) produce byte-identical output to the pre-refactor capture — parity gate passed
  3. Existing user-visible error contract is preserved: when the Azure endpoint times out or returns 5xx, the call site re-raises `QueryError` (not `LLMError`)
  4. Adapter emits one structured log event per call containing provider name, model, latency in ms, outcome, and (when available) token counts

**Plans**:
- [x] 02-PLAN-01-azure-adapter-implementation.md - Implement AzureOpenAIClient.complete() + classify_with_tool() in src/llm/azure_openai.py with typed-error mapping, structured log helper, and prompt-based JSON parsing (ADP-01, ADP-02, ERR-02, OBS-02)
- [x] 02-PLAN-02-error-translation-seam.md - Create src/llm/_compat.py with llm_to_query_error() context manager — the single LLMError→QueryError translation point (ERR-04)
- [x] 02-PLAN-03-call-site-migration.md - Delete _call_azure_openai from src/query_router.py + src/sql_generator.py; route all 3 call sites through get_llm() + llm_to_query_error(); remove unused imports (ABS-06)
- [x] 02-PLAN-04-acceptance-gate.md - tests/test_phase2_parity.py + 5 fixtures in tests/fixtures/parity/: pytest module proving all 4 Phase 2 success criteria, headlined by the five-fixture parity test

### Phase 3: Anthropic MGTI Adapter

**Goal**: Add `AnthropicMGTIClient` with text-mode `complete()` against the MGTI Apigee proxy, full typed-error mapping from MGTI HTTP responses, and observability hooks. The adapter is reachable via `get_llm("anthropic_mgti")` but no UI exposes it yet.

**Depends on**: Phase 2 (parity gate must pass before introducing Anthropic)

**Requirements**: ADP-03, ADP-04, ADP-05, ADP-06, ADP-08, ERR-02, ERR-03, CFG-02, CFG-04, OBS-01, OBS-04, TOOL-07

**Success Criteria** (what must be TRUE):
  1. `get_llm("anthropic_mgti").complete(...)` performs a `POST {base_url}/model/{model}/messages` with `X-Api-Key`, `Content-Type: application/json`, and a fresh `X-Correlation-Id` UUID per call
  2. Constructing `AnthropicMGTIClient` with a model name not starting `eu.anthropic.claude-` raises `LLMConfigError`; constructing with an `eu.anthropic.claude-opus-4-7*` model results in `temperature`/`top_p`/`top_k` being omitted from the request body
  3. MGTI HTTP 401/403 maps to `LLMAuthError`; 429/5xx maps to `LLMTransientError`; `requests.Timeout` maps to `LLMTimeoutError`; `stop_reason == "guardrail_intervened"` maps to `LLMGuardrailError` (HTTP 200 + empty content does NOT count as success)
  4. `.env.example` lists every new Anthropic variable (`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_VERSION`, `ANTHROPIC_MAX_TOKENS`, `ANTHROPIC_TEMPERATURE`, `ANTHROPIC_TIMEOUT_S`, `ANTHROPIC_TOOLS_SUPPORTED`, `LLM_PROVIDER_DEFAULT`) with documented defaults
  5. App startup logs the configured base URL for each loadable provider exactly once; `generate_sql` and `generate_executive_summary` call only `complete()` on whichever provider is active (no tool-use wrapping on either side)

**Plans**:
- [x] 03-PLAN-01-env-and-startup-log.md - Extend .env.example with the 9 Phase 3 variables (LLM_PROVIDER_DEFAULT + 8 ANTHROPIC_*); add llm_provider_loaded startup log to AzureOpenAIClient.__init__ — the SC #4 file shape + Azure half of SC #5 (CFG-02, CFG-04, OBS-01, OBS-04)
- [x] 03-PLAN-02-compat-provider-dispatch.md - Add per-provider dispatch on e.provider in src/llm/_compat.py for LLMAuthError, LLMTimeoutError, LLMTransientError, and the catch-all LLMError branch — pays down Phase 2 known debt; Anthropic timeouts no longer surface as "Azure OpenAI API call failed" (ERR-02, ERR-03 — call-site half)
- [x] 03-PLAN-03-anthropic-adapter.md - Replace the Phase 1 stub src/llm/anthropic_mgti.py with full AnthropicMGTIClient: __init__ with model-prefix validation + startup log, complete() with MGTI HTTP + correlation UUID + structured log + guardrail-before-emptiness response handling, classify_with_tool stub preserved; plus tests/manual/observe_correlation_echo.py for the X-Correlation-Id echo observation (ADP-03, ADP-04, ADP-05, ADP-06, ADP-08, ERR-02, ERR-03, OBS-01, OBS-04, TOOL-07)
- [x] 03-PLAN-04-acceptance-gate.md - tests/test_phase3_adapter.py: pytest module proving all 5 Phase 3 success criteria + end-to-end Plan 02 dispatch (21 tests, zero live HTTP, inline mock responses, no fixture files)

### Phase 4: Strict-Tools + Smoke Test

**Goal**: Wire Anthropic strict-tools for intent classification (single Python source of truth, `chart_requested`/`chart_type` stay out of the LLM schema) and ship `scripts/smoke_llm.py` as the live-credential gate that must pass for both providers before Phase 5.

**Depends on**: Phase 3

**Requirements**: ADP-07, ADP-09, TOOL-02, TOOL-03, TOOL-04, TOOL-05, TOOL-06, SMK-01, SMK-02, SMK-03, SMK-04, SMK-05

**Success Criteria** (what must be TRUE):
  1. `INTENT_TOOL` is derived programmatically from `ClassificationResultV1` (single source of truth); the derived `input_schema` does NOT contain `chart_requested` or `chart_type` fields
  2. `AnthropicMGTIClient.classify_with_tool(...)` sends `tools=[INTENT_TOOL]` and `tool_choice={"type": "tool", "name": ..., "disable_parallel_tool_use": True}`; on success it extracts the `tool_use` block input and returns a `ToolCall` validated via `jsonschema.validate`; a missing tool_use block raises `LLMSchemaError`
  3. With `ANTHROPIC_TOOLS_SUPPORTED=false`, `classify_with_tool` transparently falls back to text-mode + JSON parsing (escape hatch verified working against a fresh dev `.env`)
  4. `classify_intent` merges the heuristic-populated `chart_requested`/`chart_type` AFTER receiving the LLM result — the LLM cannot overwrite the heuristic for these two fields (covered by an explicit verification query)
  5. `python scripts/smoke_llm.py --provider both` exits zero against the staging gateway, exercising `complete()` and `classify_with_tool()` plus the Anthropic `GET /coreapi/llm/anthropic/v1/` service-info diagnostic; pass/fail per check is printed with the captured response shape

**Plans**:
- [x] 04-PLAN-01-intent-tool-and-classify-intent-migration.md - Derive INTENT_TOOL from ClassificationResultV1 (single source of truth, TOOL-02); tighten ClassificationResultV1.intent to Literal enum; migrate src/query_router.py::classify_intent from complete()+json.loads to classify_with_tool() with heuristic-merge AFTER LLM result (TOOL-04)
- [x] 04-PLAN-02-classify-with-tool-strict-tools-and-fallback.md - Replace AnthropicMGTIClient.classify_with_tool NotImplementedError stub with strict-tools path (tools + tool_choice + jsonschema.validate); add env-flag-gated _classify_via_text_mode escape hatch; extract shared _post_messages helper; add tools_supported + llm_tool_mode log fields (ADP-07, ADP-09, TOOL-05, TOOL-06)
- [x] 04-PLAN-03-smoke-script.md - Create scripts/smoke_llm.py operator-run live-credential gate: 3 checks for Anthropic (service-info GET + complete + classify_with_tool), 2 for Azure; CONTINUE-ON-FAILURE; missing-cred SKIP/FAIL matrix per CONTEXT.md (SMK-01, SMK-02, SMK-03, SMK-04, SMK-05)
- [x] 04-PLAN-04-acceptance-gate.md - tests/test_phase4_strict_tools.py: pytest module proving all 5 Phase 4 success criteria + 9 error-matrix rows + COMPAT-DISPATCH pair (LLMSchemaError, LLMGuardrailError); zero live HTTP, no conftest.py, py_compile-only SC #5 check

### Phase 5: Sidebar UI Toggle + Documentation

**Goal**: Expose provider selection in the Streamlit sidebar (Azure OpenAI default), surface model + provider on every assistant message, warn on missing credentials, and document the feature in README and USER_GUIDE.

**Depends on**: Phase 4 (smoke test must pass for both providers)

**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, DOC-01, DOC-02, DOC-03, DOC-04

**Success Criteria** (what must be TRUE):
  1. Sidebar contains an `st.selectbox` labeled "LLM provider" with "Azure OpenAI" and "Anthropic Claude (MGTI)"; selection persists in `st.session_state["llm_provider"]` initialized from `LLM_PROVIDER_DEFAULT`; the active model name is displayed read-only beneath
  2. Switching providers mid-session takes effect on the next query (no retroactive recompute); the `@st.cache_resource`-decorated adapter is re-resolved because its cache key includes `(provider, base_url, model, api_key_fingerprint)`
  3. Selecting a provider with missing env vars renders a clear inline sidebar warning and disables query submission until either the warning resolves or the user switches back
  4. Every assistant message displays a caption showing the provider and model that produced it
  5. README and USER_GUIDE explain provider selection, the MGTI-only constraint, how to run `scripts/smoke_llm.py`, and what to do when a provider warning appears

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Abstraction Seam | 3/3 | Complete ✓ | 2026-05-19 |
| 2. Azure Extraction + Parity Gate | 4/4 | Complete ✓ | 2026-05-20 |
| 3. Anthropic MGTI Adapter | 4/4 | Complete ✓ | 2026-05-21 |
| 4. Strict-Tools + Smoke Test | 4/4 | Complete ✓ (live smoke pending operator) | 2026-05-21 |
| 5. Sidebar UI Toggle + Documentation | 0/TBD | Not started | - |

---
*Roadmap created: 2026-05-19*
