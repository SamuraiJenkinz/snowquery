# Project Milestones: snow_query

## v2.1 Multi-Provider LLM Integration (Shipped: 2026-05-22)

**Delivered:** Anthropic Claude (via MGTI Apigee/Bedrock proxy) shipped as a session-selectable LLM provider alongside the existing Azure OpenAI integration, with provider-agnostic seam, byte-identical Azure parity, strict-tools intent classification, and per-message provenance that survives mid-session switches.

**Phases completed:** 1-5 (20 plans total)

**Key accomplishments:**

- Provider-agnostic LLM seam in `src/llm/` — `LLMClient` ABC, flat typed-error hierarchy (6 errors), frozen+slots adapter-boundary dataclasses, factory with single `@st.cache_resource` cache layer keyed on `(provider, base_url, model, api_key_fingerprint)`
- Azure OpenAI extracted into adapter with byte-identical parity gate (5 fixtures across structured/semantic/hybrid/exec-summary call sites); `_call_azure_openai` removed; all 3 LLM call sites route through `get_llm()` + `llm_to_query_error()`
- Anthropic MGTI adapter against `apis.mmc.com/coreapi/llm/anthropic/v1` with `X-Api-Key` auth, `X-Correlation-Id` per call, `eu.anthropic.claude-` prefix enforcement, opus-4-7 sampling-param omission, full typed-error mapping (401/403/429/5xx/timeout/guardrail/schema)
- Strict-tools intent classification — `INTENT_TOOL` derived programmatically from `ClassificationResultV1` (single source of truth, `chart_requested`/`chart_type` heuristic-only); env-flag `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch to text-mode + JSON parse
- Sidebar provider dropdown with session_state persistence, missing-env warning that disables `st.chat_input`, per-message provenance caption (`via **Provider** · \`model\``) that survives mid-session provider switches via stored-dict reads (never session_state)
- `scripts/smoke_llm.py` operator-run live-credential gate (Anthropic service-info + complete + classify_with_tool; Azure complete + classify_with_tool); README + USER_GUIDE document MGTI-only constraint, first-time Anthropic checklist, warning resolution
- Full test coverage: 91 tests in 8.13s, zero live HTTP / LLM / Streamlit / subprocess / network

**Stats:**

- 80 files changed (+26,275 / -250)
- ~1,964 LOC new Python in `src/llm/` + 470 LOC `scripts/smoke_llm.py` + ~3,050 LOC tests
- 5 phases, 20 plans, 91 tests
- 3 days from start to ship (2026-05-19 → 2026-05-22)

**Git range:** `feat(01-01)` → `docs(05)`

**What's next:** Operator-run smoke gate against staging MGTI gateway before production deploy. Next milestone TBD — candidate areas include resilience (retry-with-backoff on `LLMTransientError`), per-call-site model selection (Haiku for classify_intent / Sonnet for executive summary), Opus 4.7 with adaptive thinking (pending Hubble entitlement).

---
