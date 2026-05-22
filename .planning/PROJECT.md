# snow_query

## What This Is

A local-first Streamlit app for querying ServiceNow incident CSVs in natural language. The app classifies user intent, routes to SQL (DuckDB), semantic search (ChromaDB), or a hybrid of both, and produces tables, charts, and executive summaries. All data stays local; only the LLM call leaves the machine. As of v2.1, operators choose between Azure OpenAI and Anthropic Claude (via the MGTI Apigee/Bedrock proxy) per session.

## Core Value

Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.

## Current State

**Shipped:** v2.1 (2026-05-22) — Multi-provider LLM integration. Anthropic Claude available alongside Azure OpenAI; provider toggle in sidebar; per-message provenance preserved across mid-session switches; missing-env warning disables chat input; smoke script (`scripts/smoke_llm.py`) gates production deploy.

**Open pre-prod gate:** Operator-run live smoke against staging MGTI gateway (`python scripts/smoke_llm.py --provider both --verbose`). Smoke script artifact is structurally verified; live execution requires staging credentials not present in CI/dev. See `.planning/milestones/v2.1-MILESTONE-AUDIT.md` §7.

## Next Milestone Goals

To be defined. Candidate areas (v2 backlog from v2.1):
- **Resilience**: Retry with exponential backoff on `LLMTransientError` (429 / 5xx) — wait for production logs to show signal before scoping.
- **Provider features**: Per-call-site model selection (Haiku for `classify_intent` / Sonnet for `generate_executive_summary`) — needs production cost/latency data.
- **Opus 4.7 with adaptive thinking** — pending Hubble entitlement and tested use case.
- **Connection-test button**: Sidebar widget that runs a minimal Create Message call and reports latency — depends on smoke test stability.

Run `/gsd:new-milestone` to start questioning → research → requirements → roadmap.

## Requirements

### Validated

<!-- Existing capabilities inferred from .planning/codebase/ARCHITECTURE.md + STACK.md, plus everything shipped in v2.1. -->

Existing (pre-v2.1):

- ✓ CSV ingestion into DuckDB with multi-encoding fallback and schema inference
- ✓ Password-protected sidebar upload (`SNOWGREP_UPLOAD_PASSWORD`)
- ✓ Local semantic embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`) + ChromaDB
- ✓ Intent classification via Azure OpenAI with heuristic fallback
- ✓ NL → SQL generation via Azure OpenAI with few-shot examples
- ✓ SQL execution against DuckDB with SELECT-only security gate
- ✓ Semantic search with metadata filters (priority, assignment_group)
- ✓ Hybrid query mode (SQL + semantic, deduplicated)
- ✓ Chart inference and Altair rendering (pie / bar / line, dark theme)
- ✓ Executive summary generation via Azure OpenAI
- ✓ Streamlit chat UI with persistent session state
- ✓ Persistent storage for DuckDB and ChromaDB on local disk
- ✓ Corporate proxy / Windows cert store support via `python-certifi-win32`

Shipped in v2.1 (2026-05-22):

- ✓ Provider-agnostic LLM seam (`src/llm/`) — `LLMClient` ABC, 6 typed errors, frozen+slots boundary types — v2.1
- ✓ Azure OpenAI extracted into adapter with byte-identical parity gate; all 3 LLM call sites route through `get_llm()` — v2.1
- ✓ Anthropic Claude (via MGTI Apigee/Bedrock proxy) wired with `X-Api-Key` auth, `X-Correlation-Id` per call, `eu.anthropic.claude-` prefix enforcement, opus-4-7 sampling-param omission — v2.1
- ✓ Per-provider typed-error mapping: 401/403 → auth, 429/5xx → transient, timeout → timeout, `stop_reason=guardrail_intervened` → guardrail, missing tool_use → schema — v2.1
- ✓ Strict-tools intent classification with `INTENT_TOOL` derived programmatically from `ClassificationResultV1`; `chart_requested`/`chart_type` excluded from LLM schema (heuristic-only) — v2.1
- ✓ Sidebar provider dropdown with session_state persistence + active-model caption; default `LLM_PROVIDER_DEFAULT=azure_openai` for byte-identical upgrade — v2.1
- ✓ Missing-env warning that disables `st.chat_input` with "QUERY DISABLED — see sidebar warning" placeholder — v2.1
- ✓ `@st.cache_resource` 4-arg tuple cache key (provider, base_url, model, api_key_fingerprint) — switching ANY of these re-resolves the adapter — v2.1
- ✓ Per-message provenance caption (`via **Provider** · \`model\``) that survives mid-session provider switches via stored-dict reads (AST-locked invariant: helper never reads session_state) — v2.1
- ✓ `_compat.py` per-provider QueryError dispatch on `e.provider` — Anthropic timeouts surface as "Anthropic API call failed", not "Azure OpenAI API call failed" — v2.1
- ✓ Env-flag escape hatch `ANTHROPIC_TOOLS_SUPPORTED=false` falls back to text-mode + JSON parse for classify_intent if MGTI proxy regresses on tool pass-through — v2.1
- ✓ `scripts/smoke_llm.py` operator-run live-credential gate (`--provider azure_openai|anthropic_mgti|both`) with service-info + complete + classify_with_tool checks — v2.1
- ✓ README + USER_GUIDE document provider selection, MGTI-only constraint, smoke script, warning resolution; 7 locked UI strings preserved verbatim in both docs — v2.1
- ✓ Comprehensive test coverage: 91 tests across Phases 1-5 in 8.13s, zero live HTTP / LLM / Streamlit / subprocess / network — v2.1

### Active

<!-- Reset at v2.1 close. New active requirements will be defined by /gsd:new-milestone. -->

(None — next milestone scope is TBD)

### Out of Scope

<!-- Explicit exclusions with reasoning. -->

- Direct Anthropic API (`api.anthropic.com`) — not authorized in MMC corporate app context; MGTI proxy only
- Claude models below 4.5 — MGTI proxy explicitly restricts to Claude 4.5+ with the `eu.` regional prefix
- Per-call automatic provider routing (e.g. "use Anthropic for classification, OpenAI for SQL") — user picks one provider per session; rejected as added complexity without proven payoff
- Removing the Azure OpenAI integration — both providers remain first-class
- Streaming responses — current call sites are request/response; staying request/response keeps the UI integration trivial
- Official Anthropic Python SDK — corporate proxy headers + custom URL shape means the existing `requests`-based pattern is correct
- Auto-failover between providers — would silently bypass content policy (guardrails); user must consciously switch
- OpenAI-shape translation layer — each adapter speaks its provider's native shape; no compatibility middleware
- Embedding-model swap to Bedrock embeddings — local `sentence-transformers` stays for data-privacy reasons
- Cost dashboards / usage analytics across providers — possible future milestone, not in v2.1
- Semantic cache of LLM responses — would compromise data-privacy invariants
- OpenTelemetry trace export — log-based correlation IDs sufficient for single-user local-first app
- Mid-session provider switch mid-query — confusing behavior; user-initiated swap-then-resend is the explicit pattern
- Free-form `chat(message)` method on the interface — invites shape drift
- Async LLM calls — Streamlit is synchronous; no benefit until we move off it
- Porting `app_brutalist.py` / `fixedapp.py` / `designui.py` variants — they may consume the new abstraction later; not in scope

## Context

**Infrastructure:**
- MMC corporate app context — runs against Apigee-fronted MGTI gateways
- Azure OpenAI ingress lives at `mgti.mmc.com`
- Anthropic proxy lives at `apis.mmc.com` (different host, different auth header, different request shape — they are NOT interchangeable)
- Stage Anthropic gateway: `https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`
- Prod Anthropic gateway: `https://int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`

**Current LLM call sites:**
1. `src/query_router.py::classify_intent()` — strict-tools mode on Anthropic; prompt-based JSON parse on Azure
2. `src/sql_generator.py::generate_sql()` — text mode on both providers, max_tokens=1000
3. `src/query_router.py::generate_executive_summary()` — text mode on both providers, max_tokens=500; broad `except Exception: return None` invariant preserved

All routed through `LLMClient` via `get_llm()` + `llm_to_query_error()`.

**Test suite:** 91 tests across `tests/test_llm_seam.py`, `tests/test_phase2_parity.py`, `tests/test_phase3_adapter.py`, `tests/test_phase4_strict_tools.py`, `tests/test_phase5_ui.py`. Zero live HTTP / LLM / Streamlit / subprocess / network. Combined run: 8.13s.

**Codebase state after v2.1:**
- ~1,964 LOC in `src/llm/` (8 modules)
- 470 LOC `scripts/smoke_llm.py`
- ~3,050 LOC in v2.1 test files
- 80 files changed in v2.1 range (+26,275 / -250)

## Constraints

- **Tech stack**: Python 3.11, Streamlit ≥1.40, `requests` for HTTP — no SDK migration in scope
- **LLM transport**: HTTPS only through MGTI Apigee proxy — corporate compliance; direct API not permitted
- **Model**: Claude 4.5+ with `eu.` regional prefix — hard requirement from the MGTI proxy
- **Auth**: `X-Api-Key` for Anthropic, `api-key` for Azure OpenAI — different gateways, different conventions
- **Anthropic request body**: `anthropic_version: bedrock-2023-05-31`, top-level `system`, required `max_tokens`
- **Data privacy**: Incident data must not leak beyond the LLM call payload itself — embeddings stay local, persistence stays local
- **Performance**: New provider path matches Azure OpenAI baseline latency within ~20%
- **Backwards compatibility**: Azure OpenAI flow remains functional and default-selected — `LLM_PROVIDER_DEFAULT=azure_openai`
- **Secrets**: API keys live in `.env`, never committed; never logged

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| User-selectable provider in UI (sidebar dropdown) | Operators need to A/B providers per session as conditions shift; per-deploy env-var locking is too coarse | ✓ Good — UI-01..07 shipped in v2.1 Phase 5; no operator escalation requesting deploy-time-only |
| Both providers stay configured; no replacement | Removes the migration risk and preserves Azure OpenAI as a fallback if the Anthropic proxy degrades | ✓ Good — default stays `azure_openai`; existing deployments byte-identical after upgrade |
| Strict-tools mode for intent classification only | Classification returns structured JSON — schema enforcement here eliminates parse-failure cascades; SQL/summaries are text by nature and don't benefit | ✓ Good — 30-test Phase 4 gate covers all branches; env-flag fallback ready if MGTI proxy regresses |
| MGTI Apigee proxy only, no direct Anthropic API | Corporate compliance; this is an MMC app context | ✓ Good — locked into adapter __init__ via `eu.anthropic.claude-` prefix validation |
| Provider abstraction layer (interface + two adapters) over per-call `if` branches | Three call sites today, more later; keeping site-level code provider-agnostic is the only way to keep it readable | ✓ Good — `LLMClient` ABC + `get_llm()` factory; future third adapter triggers `_log_llm_call` extraction (currently duplicated by design) |
| Anthropic adapter speaks native MGTI shape, not an OpenAI translation layer | The skill provides a validated minimal adapter; translating Anthropic-into-OpenAI-shape adds bugs with no upside | ✓ Good — `_compat.py` translates errors only, never request shapes |
| Live smoke test required before any prod deploy | Validated practice from kbroles Quicks 008–012; catches the `/messages` and `eu.`-prefix bugs that unit tests can't | ⚠️ Pending operator — script artifact exists + structurally verified; live run against staging is the open pre-prod gate (SMK-05 in v2.1 audit §7) |
| Default provider stays Azure OpenAI initially | Don't change observable behavior of existing users in the same release that adds the new option | ✓ Good — zero regression reports; upgrade is byte-identical |
| Flat error hierarchy (no retryable grouping) | Retry logic isn't in v2.1 scope; defer grouping until v2 RES-01 lands with production signal | — Pending — retry logic in v2 backlog |
| Single cache layer: `@st.cache_resource` only | Phase 1 module-level `_cache: dict` + Streamlit cache would be double-caching; the dict was anticipated for deletion at Phase 1 close | ✓ Good — Phase 5 deleted the dict; single-cache lock holds |
| `_log_llm_call` duplicated between azure_openai.py and anthropic_mgti.py | No premature extraction until a third adapter exists; both files annotate the duplication | — Pending — extract when third adapter lands |
| `_compat.py` dispatches on `e.provider` for per-provider QueryError wording | Phase 2 hardcoded Azure remediation text; Phase 3 added dispatch to prevent "Azure OpenAI API call failed" appearing for Anthropic errors | ✓ Good — locked by Phase 4 COMPAT-DISPATCH test pair |
| `_render_provenance_caption` must never read `st.session_state` | History messages must keep their original provenance after a mid-session provider switch — caption helper must read from the stored message dict, not current session_state | ✓ Good — AST-based regression test locks the invariant at executable level (test_sc4_render_provenance_caption_does_not_read_session_state) |
| `INTENT_TOOL` derived via `typing.get_type_hints()` not `fields().type` | Under `from __future__ import annotations`, `fields().type` returns strings — `get_type_hints` resolves to types | ✓ Good — Phase 4 Pitfall 1 guard; locked by acceptance gate |
| `chart_requested`/`chart_type` heuristic-populated, excluded from LLM schema | Heuristic outperforms the LLM on these two fields; LLM cannot overwrite the heuristic for them | ✓ Good — TOOL-04 test injects `chart_requested=True` into ToolCall.input and asserts classify_intent reads from heuristic locals (False) |
| Guardrail check BEFORE content-emptiness check in Anthropic HTTP 200 handler | Anthropic returns HTTP 200 + empty content when guardrail intervenes; checking emptiness first would silently succeed on guardrail blocks | ✓ Good — Phase 3 Pitfall 4 guard; locked by paired tests `test_guardrail_intervened_raises_guardrail_error` + `test_empty_content_non_guardrail_raises_schema_error` |

---
*Last updated: 2026-05-22 after v2.1 milestone completion*
