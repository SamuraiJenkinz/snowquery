# snow_query

## What This Is

A local-first Streamlit app for querying ServiceNow incident CSVs in natural language. The app classifies user intent, routes to SQL (DuckDB), semantic search (ChromaDB), or a hybrid of both, and produces tables, charts, and executive summaries. All data stays local; only the LLM call leaves the machine. This milestone adds Anthropic Claude (via the MGTI Apigee/Bedrock proxy) as a selectable provider alongside the existing Azure OpenAI integration.

## Core Value

Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.

## Requirements

### Validated

<!-- Existing capabilities inferred from .planning/codebase/ARCHITECTURE.md + STACK.md -->

- ✓ CSV ingestion into DuckDB with multi-encoding fallback and schema inference — existing
- ✓ Password-protected sidebar upload (`SNOWGREP_UPLOAD_PASSWORD`) — existing
- ✓ Local semantic embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`) + ChromaDB — existing
- ✓ Intent classification via Azure OpenAI with heuristic fallback — existing
- ✓ NL → SQL generation via Azure OpenAI with few-shot examples — existing
- ✓ SQL execution against DuckDB with SELECT-only security gate — existing
- ✓ Semantic search with metadata filters (priority, assignment_group) — existing
- ✓ Hybrid query mode (SQL + semantic, deduplicated) — existing
- ✓ Chart inference and Altair rendering (pie / bar / line, dark theme) — existing
- ✓ Executive summary generation via Azure OpenAI — existing
- ✓ Streamlit chat UI with persistent session state — existing
- ✓ Persistent storage for DuckDB and ChromaDB on local disk — existing
- ✓ Corporate proxy / Windows cert store support via `python-certifi-win32` — existing

### Active

<!-- This milestone: add Anthropic Claude as a selectable provider. -->

- [ ] Anthropic Claude provider wired in via the MGTI Apigee proxy (`/coreapi/llm/anthropic/v1/model/{model}/messages`) using `X-Api-Key` auth and `anthropic_version: bedrock-2023-05-31`
- [ ] Provider-agnostic LLM interface so the three existing call sites — `classify_intent`, `generate_sql`, `generate_executive_summary` — work against either Azure OpenAI or Anthropic without per-site `if provider == ...` branching
- [ ] Sidebar UI control lets the user select the active LLM provider per session; default provider configurable via env var
- [ ] Strict-tools mode (Anthropic `tools` + `tool_choice` + `input_schema`) used for **intent classification only**, to eliminate JSON parse failures and lock the response shape
- [ ] SQL generation and executive summaries use text mode against either provider (no structured output)
- [ ] Anthropic configuration via env vars: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_VERSION`, `ANTHROPIC_MAX_TOKENS`, `ANTHROPIC_TEMPERATURE`, `ANTHROPIC_TIMEOUT_S`
- [ ] Anthropic-specific error handling: typed exceptions for auth (401/403), guardrail interventions (`stop_reason == "guardrail_intervened"`), proxy error envelope (`{"error": {"title", "detail", "status"}}`), and schema validation failures
- [ ] `X-Correlation-Id` header sent on every Anthropic request and logged alongside the application request for trace continuity
- [ ] Pre-request smoke test (service-info GET, spend GET, minimal Create Message POST) documented and runnable from the repo to catch URL/auth/model bugs before any prod deploy
- [ ] `.env.example` updated with new Anthropic variables and a documented `LLM_PROVIDER` default
- [ ] README / USER_GUIDE updated with provider selection instructions and the MGTI-only constraint
- [ ] Existing Azure OpenAI flow remains unchanged in behavior — no regression in classification accuracy, SQL output, or summary quality when provider is OpenAI

### Out of Scope

<!-- Explicit exclusions with reasoning. -->

- Direct Anthropic API (`api.anthropic.com`) — only the MGTI Apigee proxy is in scope; this is an MMC corporate app context, and direct access isn't authorized
- Claude models below 4.5 — the MGTI proxy explicitly restricts to Claude 4.5+ with the `eu.` regional prefix
- Per-call automatic provider routing (e.g. "use Anthropic for classification, OpenAI for SQL") — user picks one provider per session; rejected as added complexity without proven payoff
- Removing the Azure OpenAI integration — both providers remain first-class
- Streaming responses — current call sites are request/response; staying request/response keeps the UI integration trivial
- Switching to the official Anthropic Python SDK — corporate proxy headers + custom URL shape means the existing `requests`-based pattern is the right baseline
- Embedding-model swap to Bedrock embeddings — local `sentence-transformers` stays for data-privacy reasons
- Cost dashboards / usage analytics across providers — possible v2, not in this milestone
- Migration of the experimental `app_brutalist.py` / `fixedapp.py` / `designui.py` variants — they may consume the new abstraction once it exists, but porting them is not in scope here

## Context

**Why now:** Operators need optionality between LLM providers as procurement, latency, and answer quality vary across Azure OpenAI vs. Anthropic Claude. Picking one upfront locks the app to a single vendor.

**Infrastructure:**
- MMC corporate app context — runs against Apigee-fronted MGTI gateways
- Existing Azure OpenAI ingress lives at `mgti.mmc.com`
- The new Anthropic proxy lives at `apis.mmc.com` (different host, different auth header, different request shape — they are NOT interchangeable)
- Hubble app YAML for this app is merged; `X-Api-Key` for the Anthropic proxy is already in hand
- Stage gateway: `https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`
- Prod gateway: `https://int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`

**Current LLM call sites** (`.planning/codebase/ARCHITECTURE.md` confirms):
1. `src/query_router.py::classify_intent()` — returns dict {intent, confidence, reasoning, detected_filters, chart_requested, chart_type}
2. `src/sql_generator.py::generate_sql()` — returns SQL string with few-shot prompting
3. `src/query_router.py::generate_executive_summary()` — returns free-form prose

All three currently call Azure OpenAI Chat Completions via `requests`, temperature 0.1, max_tokens 500.

**Known failure modes for first-time Anthropic integrators** (mgti-anthropic-integration skill, validated against kbroles Quicks 008–012):
- `/messages` URL suffix is mandatory — omitting it returns `404 rf-route-not-found` (spec PDF was wrong about this; only the smoke test caught it in prior projects)
- Model name needs `eu.` prefix and must be Claude 4.5+ — otherwise `404 Model not supported`
- Auth header is `X-Api-Key`, not `Authorization: Bearer` or `api-key`
- `system` prompt goes at the top level of the body, not inside `messages[]`
- `max_tokens` is required (unlike OpenAI where it's optional)
- `anthropic_version` must be `"bedrock-2023-05-31"`

The smoke-test workflow is the single highest-ROI step — it catches all five above in seconds before any unit test (which can lie against hardcoded mocks) gets a chance to mislead.

## Constraints

- **Tech stack**: Python 3.11, Streamlit ≥1.40, `requests` for HTTP — Existing app foundation; no SDK migration in scope
- **LLM transport**: HTTPS only through MGTI Apigee proxy — Corporate compliance; direct API not permitted
- **Model**: Claude 4.5+ with `eu.` regional prefix — Hard requirement from the MGTI proxy
- **Auth**: `X-Api-Key` header per Anthropic proxy; existing `api-key`-style header stays for Azure OpenAI — Different gateways, different conventions
- **Anthropic request body**: `anthropic_version: bedrock-2023-05-31`, top-level `system`, required `max_tokens` — Bedrock proxy contract
- **Data privacy**: Incident data must not leak beyond the LLM call payload itself — Embeddings stay local; persistence stays local
- **Performance**: New provider path should match Azure OpenAI baseline latency within ~20% — Don't regress UX
- **Backwards compatibility**: Existing OpenAI flow must remain functional and selectable — Don't break what works
- **Secrets**: API keys live in `.env`, never committed — Standard practice; `.env` already git-ignored

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| User-selectable provider in UI (sidebar dropdown) | Operators need to A/B providers per session as conditions shift; per-deploy env-var locking is too coarse | — Pending |
| Both providers stay configured; no replacement | Removes the migration risk and preserves Azure OpenAI as a fallback if the Anthropic proxy degrades | — Pending |
| Strict-tools mode for intent classification only | Classification returns structured JSON — schema enforcement here eliminates parse-failure cascades; SQL/summaries are text by nature and don't benefit | — Pending |
| MGTI Apigee proxy only, no direct Anthropic API | Corporate compliance; this is an MMC app context | — Pending |
| Provider abstraction layer (interface + two adapters) over per-call `if` branches | Three call sites today, more later; keeping site-level code provider-agnostic is the only way to keep it readable | — Pending |
| Anthropic adapter expects native Messages API shape, not an OpenAI translation layer | The skill provides a validated minimal adapter; translating Anthropic-into-OpenAI-shape adds bugs with no upside | — Pending |
| Live smoke test required before any prod deploy | Validated practice from kbroles Quicks 008–012; catches the `/messages` and `eu.`-prefix bugs that unit tests can't | — Pending |
| Default provider stays Azure OpenAI initially | Don't change observable behavior of existing users in the same release that adds the new option | — Pending |

---
*Last updated: 2026-05-19 after initialization*
