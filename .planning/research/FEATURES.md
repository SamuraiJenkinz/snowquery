# Feature Research: Multi-Provider LLM Abstraction

**Domain:** Multi-provider LLM integration layer inside a local-first Streamlit app
**Researched:** 2026-05-19
**Confidence:** HIGH on industry patterns (web-verified + skill-validated), HIGH on app-specific call-site impact (codebase mapped 2026-05-19), MEDIUM on a few quirk decisions noted inline.

## Scope Reminder

This research covers features of the **LLM abstraction itself** — the layer that lets `classify_intent()`, `generate_sql()`, and `generate_executive_summary()` work against either Azure OpenAI or Anthropic Claude. The base app's CSV/SQL/semantic/chart features are out of scope.

**Three call sites that consume this abstraction:**

1. **CS1** — `src/query_router.py::classify_intent()` → structured dict (intent, confidence, filters, chart hints). Strict-tools candidate.
2. **CS2** — `src/sql_generator.py::generate_sql()` → SQL string (text mode, post-parse-and-validate).
3. **CS3** — `src/query_router.py::generate_executive_summary()` → free-form prose.

All references below tag features with the call site(s) they touch.

## Feature Landscape

### Table Stakes (Must Have — Feature Is Broken Without It)

Features where missing them makes the milestone feel incomplete or unsafe.

| # | Feature | Why Table Stakes | Complexity | Call Sites | Notes |
|---|---------|------------------|------------|-----------|-------|
| TS-1 | **Provider abstraction interface** (single `LLMProvider` protocol exposing the operations call sites need) | Three call sites today, more later. Per-site `if provider == ...` branches will spiral. Industry consensus: normalize requests/responses across APIs at the seam, not at the call site. | MEDIUM | CS1, CS2, CS3 | Recommend two methods, not one. See ARCHITECTURE.md for shape; rationale in dependency notes below. |
| TS-2 | **Two concrete adapters: OpenAI (existing) + Anthropic (new)** | The whole point of the milestone. Anthropic native Messages shape, not an OpenAI translation layer — the skill is explicit about this. | MEDIUM | CS1, CS2, CS3 | Anthropic adapter ≈ copy of `mgti_anthropic.py` from the skill. OpenAI adapter ≈ extracted from existing `_call_azure_openai` (currently duplicated in two files). |
| TS-3 | **Sidebar provider dropdown with session-wide selection** | Decided. Operators need to A/B providers per session as latency / quality / quota shifts. Env-var-only would lock everyone to one provider per deploy. | LOW | All (via session state) | Default from env var (`LLM_PROVIDER`); user overrides per session. Streamlit `st.selectbox` + `st.session_state["llm_provider"]`. |
| TS-4 | **Env-var configuration for both providers** (Anthropic vars added; existing Azure vars retained) | Standard practice. `.env.example` must document new vars or new developers will silently fail. The skill spells out the required set: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, plus sensible defaults for version / max_tokens / temperature / timeout. | LOW | All (via `config.py`) | Both providers must be configurable simultaneously — they coexist, not toggle. |
| TS-5 | **Strict-tools structured output for `classify_intent`** | Decided. The intent JSON is already a parse-failure cliff in the current code (`_heuristic_classify` is the silent fallback). API-level schema enforcement eliminates the cliff. Anthropic: `tools` + `tool_choice` + `input_schema` confirmed working through MGTI as of 2026-05-12 per skill provenance. OpenAI: `response_format: {type: 'json_schema', strict: true}`. | MEDIUM | CS1 only | The provider interface needs a `complete_structured(schema, ...)` method or equivalent — see TS-1 dependency. |
| TS-6 | **Text-mode generation for SQL + summary** | Decided. SQL is text by nature; existing few-shot prompt already returns a JSON-wrapped SQL but the wrapping isn't load-bearing — could be plain text. Summaries are prose. No win from structured output here. | LOW | CS2, CS3 | Same provider interface, second method (`complete_text`). |
| TS-7 | **`/messages` URL suffix and `eu.`-prefix model — built into the Anthropic adapter, not exposed to call sites** | These are the two top-of-list failure modes in the skill (Quick 010 + Quick 011). Hard-coding the construction inside the adapter prevents any future call site from accidentally bypassing it. | LOW | n/a (adapter-internal) | Builder: `url = f"{base_url.rstrip('/')}/model/{model}/messages"`. Model-name validation can warn at boot if `eu.` prefix missing — see TS-13. |
| TS-8 | **Top-level `system` prompt + required `max_tokens` + `anthropic_version=bedrock-2023-05-31` in Anthropic adapter** | Three of the validated pitfalls in the skill. Wrong placement → 400 `invalid_request_error`. Missing `max_tokens` → 400. Wrong `anthropic_version` → 400. All three must be enforced inside the adapter, opaque to call sites. | LOW | n/a (adapter-internal) | All three already correctly handled in the skill's reference `create_message()` — copy that shape. |
| TS-9 | **Auth header per provider — `X-Api-Key` (Anthropic) vs `api-key` (Azure OpenAI)** | Different ingresses, different conventions. Per the skill: `Authorization: Bearer` and `api-key` are both wrong for the Anthropic proxy. Per the existing code: `api-key` is right for Azure OpenAI. The adapter, not the call site, owns this. | LOW | n/a (adapter-internal) | Sanity check at boot — fail fast if a required key is missing for the selected provider. |
| TS-10 | **Smoke-test script (three curls or three Python calls)** | The single highest-ROI feature per the skill's own provenance — caught the `/messages` and `eu.`-prefix bugs in kbroles where unit tests had hardcoded mocks and didn't. Required reading in the README. | LOW | n/a (standalone) | Three steps: GET service-info (gateway reachable), GET spend (auth works), POST minimal Create Message (model + URL + body shape). Runnable from `scripts/smoke_anthropic.py` or equivalent. |
| TS-11 | **Common error vocabulary — typed exceptions raised by adapters, caught by call sites** | Three call sites, two providers = six error paths in pessimistic theory. Without normalization, each call site grows two `except` arms over time. Industry consensus: error-class consistency is a primary value of the abstraction layer (instructor, AbstractCore, LiteLLM all do this). Recommend: `LLMAuthError`, `LLMTransientError` (retry-eligible), `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMConfigError`. Map provider HTTP responses to these. | MEDIUM | All (catch sites) | Existing `QueryError` is too coarse — covers auth, transient, and parse failures with the same class. New hierarchy lives in `src/llm/errors.py`. |
| TS-12 | **Bedrock guardrail handling — `stop_reason == "guardrail_intervened"` mapped to non-retryable refusal** | Skill pitfall #7. Bedrock returns HTTP 200 with `content: []` when it blocks — looks like a successful empty response. If the adapter doesn't translate this to an exception, downstream parse code will crash on `content[0]` access or silently produce empty results. Critical for CS1 (classification) where empty content → heuristic fallback obscures the real cause. | LOW | All (raised by adapter) | Maps to `LLMGuardrailError` in TS-11's hierarchy. Bedrock guardrails can false-positive on near-blank inputs per the skill — pre-filter empty queries before calling. |
| TS-13 | **Fail-fast config validation at app boot** | The skill's `from_env()` already does this — missing required vars → clear error, not first-request mystery 500. Bedrock model-name `eu.` prefix check at boot is also cheap (regex). | LOW | n/a (`config.py` / startup) | Don't validate the inactive provider's credentials at boot — only the default. The other provider gets validated when the user switches to it (lazy). |
| TS-14 | **README + USER_GUIDE updated for provider selection** | Already on the Active list in PROJECT.md. Without it, the sidebar dropdown looks magic and operators won't know about model names, env vars, or smoke test. | LOW | n/a (docs) | Document: (a) how to set env vars for both providers, (b) how to pick provider in sidebar, (c) how to run smoke test, (d) MGTI-only constraint. |

### Differentiators (Nice Edge — Not Required, But Buys Real Value)

Features that aren't required to ship but materially improve operability, debuggability, or future-proofing.

| # | Feature | Value Proposition | Complexity | Call Sites | Notes |
|---|---------|-------------------|------------|-----------|-------|
| DF-1 | **`X-Correlation-Id` per Anthropic request, logged with the app-side request id** | The skill flags this as the trace key the Core API team uses to investigate suspected guardrail false-positives. Without it, escalating a bad-content blockage costs you the round trip of asking the user to reproduce. With it: one log line links app → proxy → Bedrock. | LOW | All (via adapter) | UUID4 per call. Log line: `logger.info("llm_request", extra={"correlation_id": cid, "provider": ...})`. Optional: also send for OpenAI (`x-ms-client-request-id`) for symmetric tracing. |
| DF-2 | **Retry with exponential backoff on transient errors only** | 429 / 5xx / network timeouts deserve retry; guardrail blocks / 401 / 400 do not. The TS-11 typed errors make this trivial — `LLMTransientError` is the only retry-eligible class. Industry standard: 1s, 2s, 4s, jitter, max 3 attempts. | MEDIUM | All (via adapter) | Critical for Anthropic: Bedrock guardrails sometimes false-positive on whitespace queries. The fix is pre-filter input (see TS-12 + PF-style design), NOT retry — retrying a guardrail block just wastes a token round-trip. Distinguish in code. |
| DF-3 | **Token / cost usage logging — capture `usage.input_tokens` / `usage.output_tokens` per call** | Both providers return usage in the response. Logging per-call usage at INFO level gives a cheap "is this provider getting expensive?" answer without needing a dashboard. Aligns with the 2026 industry signal that cost observability is now table-stakes-adjacent. | LOW | All (via adapter return) | Don't build a dashboard (that's anti-feature AF-3). Just log to stdout. A grep-able log line is enough for one-user, low-volume use. |
| DF-4 | **Health-check endpoint for the active provider** (extension of TS-10 smoke test, surfaced as a sidebar button) | Operators want a "is the provider working right now?" answer without restarting the app. A sidebar button that fires the minimal GET-service-info + minimal POST-create-message call and shows the result solves this. | LOW | n/a (sidebar) | Re-uses the smoke-test plumbing from TS-10. Don't auto-run on every page load — only on click (one Bedrock token-consuming call per click is fine; per-page-load is not). |
| DF-5 | **Schema-validation defence-in-depth on tool-use responses** | Bedrock validates `input_schema` upstream, but the skill recommends `jsonschema.validate` as defence-in-depth — catches the rare proxy/schema-version mismatch. ~5 lines of code, prevents a class of debugging traps where the schema and downstream code drift apart. | LOW | CS1 only | Already in the skill's reference code. Use the same schema the downstream `classify_intent` dict consumer expects — no duplication. |
| DF-6 | **Per-provider model identifier visible in the UI** | Sidebar dropdown shows "OpenAI (gpt-4o)" / "Anthropic (claude-sonnet-4-5)" not just "OpenAI" / "Anthropic". When two providers give different answers, the operator wants to know exactly which model produced which. Trivial. | LOW | n/a (sidebar) | Read model name from config; render alongside provider name. |
| DF-7 | **`ANTHROPIC_TOOLS_SUPPORTED` env-flag escape hatch** | The skill explicitly recommends this. Strict-tools is undocumented in the MGTI proxy quickstart but works as of 2026-05-12. If the proxy regresses, an env-var flip → text mode + post-validate parses → app stays up, no redeploy. | LOW | CS1 (adapter behavior switch) | When `false`, the Anthropic classify path emits a text response with a JSON instruction in the system prompt and the adapter does `json.loads` + jsonschema validate. Slower path, but a safety net. |
| DF-8 | **Streamlit cache for adapter instances (`@st.cache_resource`)** | Adapters are stateless config holders + a `requests.Session`. Caching them across script reruns avoids needless reconstruction. Free perf, mostly cleanliness. | LOW | n/a (startup) | One cache key per provider, not per session. Session state stores only "which provider is active." |
| DF-9 | **Provider-mismatch warning when user-selected provider lacks credentials** | If sidebar shows both options but one provider's env vars aren't set, switching to it should produce a clear inline warning, not a crash on first query. Better UX than the existing "API key not configured" QueryError at first call. | LOW | n/a (sidebar) | Check at selection time, not at call time. `if provider == "anthropic" and not ANTHROPIC_API_KEY: st.warning(...)`. |

### Anti-Features (Deliberately NOT Building — With Reasoning)

Features the multi-provider-LLM space commonly includes that we are explicitly excluding. Each entry covers why excluding it is correct for *this* app at *this* milestone.

| # | Anti-Feature | Why People Build It | Why It's Wrong For Us | What We Do Instead |
|---|--------------|---------------------|-----------------------|-------------------|
| AF-1 | **Streaming responses** | Modern chat UIs use streaming to lower perceived latency. SSE / `stream: true` patterns are 2026 default for AI chat. | All three call sites are request → process → render. The UI integration is synchronous and the results (dataframe, SQL string, summary prose) are consumed whole. Streaming would force partial-state handling in three places for zero UX win on short responses (max_tokens 500–1000). PROJECT.md decision explicitly: not in scope. | Keep request/response. Document as a design choice, not a gap. If chat-style turn-by-turn is added later (out of scope), revisit. |
| AF-2 | **Per-call automatic provider routing** ("use Anthropic for classification, OpenAI for SQL") | LiteLLM / industry pattern: route per task to the cheapest/best provider per call. Optimizes cost or quality per workload. | PROJECT.md decision: user picks one provider per session. Per-call routing is added complexity (routing config, two parallel sets of error handling, two cost streams to reason about) for unproven payoff in a three-call-site app. | Session-wide selection. Sidebar dropdown. Revisit only if A/B data justifies it. |
| AF-3 | **Cost dashboard / usage analytics across providers** | LangFuse / LangSmith / Helicone all sell this. 2026 industry "complete observability" pattern. | One user, local-first, no central server. A dashboard needs persistence, aggregation, and a UI — all built on top of what's effectively `logger.info(usage_dict)`. The dashboard's value-to-effort ratio is poor here. PROJECT.md "possible v2, not in this milestone." | Log usage to stdout per call (DF-3). Grep / tail when curious. Build a dashboard only if usage data ever justifies it. |
| AF-4 | **Direct Anthropic API (`api.anthropic.com`) support alongside the MGTI proxy** | The official Anthropic SDK is well-documented and easier than the proxy. New developers will try to "just point it at api.anthropic.com." | This is an MMC corporate app. Direct API access isn't authorized, and routing customer data through it would be a compliance event. PROJECT.md decision: MGTI proxy only. | Single base URL in config, scoped to `apis.mmc.com`. Refuse to construct an adapter pointed at any other host (boot-time check + clear error). |
| AF-5 | **Auto-failover when one provider returns an error** | Industry "resilience" pattern: 429 from OpenAI → silently fall back to Anthropic. LiteLLM's killer feature. | The two providers can give substantially different answers — silent failover masks "the SQL is wrong because the cheaper model misread the schema." Trust requires the user knowing which provider produced the answer they're looking at. Plus, the smoke-test contract is that the smoke test catches provider issues before runtime, not that the app papers over them. | Surface the error. Let the user manually switch providers in the sidebar. If they're seeing repeated 429s on one, they can switch — explicitly. |
| AF-6 | **OpenAI Chat Completions translation layer in front of the Anthropic adapter** | "Just write everything to OpenAI shape and have the Anthropic adapter accept OpenAI-shaped input" — looks tidy from inside the OpenAI-only codebase that's the starting point. | Translation layer = bugs with no upside (skill, pitfalls section). Translation reorders `messages[]` to extract a system prompt, fakes `max_tokens` defaults that Anthropic actually requires, papers over `anthropic_version`, and adds a fragile mapping layer for tool_use ↔ function_call. Two adapters speaking their native API shapes is cleaner. | Both adapters expose the same Python-level interface (TS-1) but each adapter speaks its native HTTP shape. Translation lives at the Python level, not the HTTP level. |
| AF-7 | **Switching to the official `anthropic` Python SDK** | "There's an SDK, why are we writing raw `requests` calls?" — a recurring question from anyone seeing the adapter for the first time. | The MGTI proxy needs `X-Api-Key` (the SDK sends `Authorization: Bearer ...` or `x-api-key` with different shape), a custom base URL with the `/messages` suffix the SDK doesn't construct that way, and the proxy's error envelope is different from native Anthropic. Fighting the SDK to accept these is more code than the 100-line raw adapter the skill provides. | Raw `requests` adapter modeled on the skill's `mgti_anthropic.py`. ~100 LOC. No abstraction loss. |
| AF-8 | **Async LLM calls** | Streamlit 1.40+ has some async support; aiohttp is fast; the industry default for high-concurrency LLM apps is async. | This is a single-user local Streamlit app. Streamlit's execution model is top-to-bottom on every interaction — async doesn't free the UI thread anyway without significant refactoring (the `CONCERNS.md` notes this is an existing limitation). Three synchronous calls per query → adding async to two adapters returns no perceptible win. | Stay synchronous `requests`. Document as scoped limitation if scaling concerns ever arise. |
| AF-9 | **Built-in semantic-cache for LLM responses** | LiteLLM / Portkey / many gateways cache prompt-keyed responses. Cuts cost on repeated questions. | Three call sites, two of which have small input-space variance (classification of phrased-different-ways queries; SQL generation from same NL with different schema) and one which has high variance (summary). Cache key design is nontrivial (do you cache by prompt? schema? both?) and a cache miss tells you nothing. Cost isn't the problem we're solving — provider choice is. | No cache. If the same query is re-issued, it re-calls the LLM. Acceptable. |
| AF-10 | **Custom-defined provider plugin system** ("anyone can add a provider via a YAML descriptor") | Pluginization is fun and feels architecturally pure. AbstractCore / LiteLLM market themselves on this. | Two providers, no plans for a third (per PROJECT.md scope). Pluginization is overhead with no consumer. The interface contract (TS-1) is small enough that a third provider, if it ever materializes, is one file + an `elif` in the factory — no plugin loader needed. | Concrete factory: `if provider == "openai": return OpenAIAdapter(...) elif "anthropic": return AnthropicAdapter(...)`. Closed for now, easily opened later. |
| AF-11 | **Streaming token-by-token telemetry / detailed traces (OpenTelemetry, LangFuse traces)** | Production observability gold standard. Per the 2026 industry guides, this is what mature LLM apps do. | One user, one box, stdout logging is sufficient (see DF-3). OpenTelemetry collector + a trace backend = infrastructure you don't have and can't easily get on a corporate-Windows-laptop deploy. Solving a problem that doesn't exist at this scale. | INFO-level logging with `correlation_id`, `provider`, `usage`, `latency_ms`, `stop_reason`. Grep is the dashboard. |
| AF-12 | **Mid-session provider switching mid-query** (e.g. "if Anthropic guardrail blocks, retry as OpenAI") | A "smart" retry that pivots provider on guardrail. Feels clever. | Guardrails block for a reason — usually content policy. Silently routing to a provider with different content policy is the kind of behavior that ends up in a postmortem ("why did the app summarize a flagged incident on OpenAI when Anthropic refused?"). Don't do it. | Guardrail blocks raise `LLMGuardrailError` (TS-12). User sees the refusal. They can manually switch provider if they think it's a false positive — explicit action, in the log. |
| AF-13 | **A `chat()` method on the LLMProvider interface that takes free-form messages** | The unifying-SDK style (OpenAI Python SDK shape, AbstractCore, LiteLLM all do this). | Our three call sites don't need free-form chat — they need `complete_text(system, user)` and `complete_structured(system, user, schema)`. Designing the interface around the actual usage keeps it minimal. Free-form chat is dead-code surface area today. | Two-method interface: `complete_text` + `complete_structured`. See TS-1 + ARCHITECTURE.md. |

## Feature Dependencies

```
TS-13 (config validation) ──> TS-4 (env vars)
                                       │
                                       ▼
                              TS-9 (auth per provider)
                                       │
                                       ▼
TS-7 (URL builder)         TS-8 (body shape)
       │                          │
       └──────────┬───────────────┘
                  ▼
       TS-2 (concrete adapters) ◄─── TS-1 (interface)
            │       │
            │       ├──> TS-5 (strict tools for CS1)
            │       └──> TS-6 (text mode for CS2/CS3)
            │
            ├──> TS-11 (error vocabulary) ──> TS-12 (guardrail mapping)
            │           │
            │           └──> DF-2 (retry: transient only)
            │
            ├──> DF-1 (correlation IDs)
            ├──> DF-3 (usage logging)
            └──> DF-5 (schema defence-in-depth — depends on TS-5)

TS-2 ──> TS-10 (smoke test exercises adapter)
              │
              └──> DF-4 (sidebar health-check button — depends on TS-10)

TS-1 + TS-2 ──> TS-3 (sidebar dropdown — needs adapters to switch between)
                       │
                       └──> DF-6 (model name in UI — depends on TS-3)
                       └──> DF-9 (credential-presence warning — depends on TS-3 + TS-13)

DF-7 (tools escape hatch) ──conflicts──> TS-5 (only one of them is active per request)

TS-14 (docs) ──depends on──> everything above being settled
```

### Dependency Notes

- **TS-1 must come before TS-2**: The interface defines what the adapters fulfill. Implementing two adapters without an interface guarantees they drift.
- **TS-11 (error vocabulary) is on the critical path for DF-2 (retry)**: Without typed errors, retry logic has to inspect HTTP status codes everywhere — every call site grows the same `if 429 or 503` arm. Type the errors at the adapter boundary; retry becomes a one-line `except LLMTransientError`.
- **TS-12 (guardrail) is independent of DF-2 (retry)**: Guardrails are NOT transient. The skill is explicit. Don't conflate the two.
- **DF-7 (tools escape hatch) is mutually exclusive with TS-5 per-request**: An env-var flip turns one off and the other on. They can't both be active at the same call.
- **TS-10 (smoke test) is a hard prerequisite for any prod deploy**: Codified in PROJECT.md key decisions. It is *not* optional — DF-4 makes it easier to run, but TS-10 must exist with or without DF-4.
- **Sidebar dropdown (TS-3) is the only feature visible to the user**: Everything else is invisible plumbing. If TS-3 is broken, the milestone visibly failed.

## MVP Definition

### Launch With (Required for This Milestone)

Every TS-*. No exceptions. The milestone is "Anthropic selectable alongside OpenAI" and skipping any table stake means it isn't actually selectable, isn't actually safe, or isn't actually debuggable.

- [ ] TS-1 through TS-14 — see table above.

### Add Alongside If Cheap (Differentiators We Should Strongly Consider For v1)

These are LOW-complexity items that materially improve the milestone without expanding scope much. Recommend pulling them into v1 unless they get blocked.

- [ ] **DF-1** (correlation IDs) — already in the skill's reference adapter; ~3 LOC to wire to the logger. Pull in.
- [ ] **DF-3** (usage logging) — one log line per call. Pull in.
- [ ] **DF-5** (schema defence-in-depth) — already in the skill's reference code. Pull in.
- [ ] **DF-6** (model name in UI) — one line in the sidebar render. Pull in.
- [ ] **DF-7** (tools escape hatch) — already in the skill's reference. Cheap insurance against MGTI proxy regression. Pull in.
- [ ] **DF-8** (`@st.cache_resource` for adapter) — minor perf hygiene. Pull in.
- [ ] **DF-9** (credential-presence warning) — better UX with no real cost. Pull in.

### Defer Past v1 (Differentiators Worth Doing Later)

- [ ] **DF-2** (retry with backoff) — MEDIUM complexity and needs DF-3-style metrics to tune. Defer until we see actual 429s in production logs.
- [ ] **DF-4** (sidebar health-check button) — depends on TS-10 being stable. Easy to add post-v1 once smoke test exists.

### Future Consideration

Items already excluded by PROJECT.md (out-of-scope) or downgraded to anti-features above. Do not pull these into v1 even under pressure:

- All AF-* entries (streaming, per-call routing, cost dashboard, direct API, auto-failover, etc.). Each has reasoning attached — re-read the table before relaxing any of them.

## Feature Prioritization Matrix

Only listing items where prioritization is non-obvious (most table-stakes are P1 trivially).

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| TS-1 Interface | HIGH (enables everything else) | MEDIUM | P1 |
| TS-2 Two adapters | HIGH | MEDIUM | P1 |
| TS-3 Sidebar dropdown | HIGH (only user-visible feature) | LOW | P1 |
| TS-5 Strict tools (CS1) | HIGH (eliminates parse failures) | MEDIUM | P1 |
| TS-10 Smoke test | HIGH (deploy-confidence) | LOW | P1 |
| TS-11 Error vocabulary | MEDIUM (debuggability) | MEDIUM | P1 |
| TS-12 Guardrail handling | MEDIUM (failure mode coverage) | LOW | P1 |
| DF-1 Correlation IDs | MEDIUM (incident response) | LOW | P1 (pull in) |
| DF-3 Usage logging | MEDIUM (cost visibility) | LOW | P1 (pull in) |
| DF-5 Schema defence | LOW (caught by upstream usually) | LOW | P1 (pull in) |
| DF-6 Model name in UI | LOW (clarity) | LOW | P1 (pull in) |
| DF-7 Tools escape hatch | MEDIUM (proxy regression insurance) | LOW | P1 (pull in) |
| DF-2 Retry with backoff | MEDIUM (resilience) | MEDIUM | P2 (defer) |
| DF-4 Health-check button | LOW (smoke test covers it) | LOW | P2 (defer) |

**Priority key:**
- P1: Must have for milestone launch
- P2: Should have, add when actual production signal justifies it
- P3: Future consideration (not used here — anti-features cover this space)

## Competitor / Adjacent Product Pattern Analysis

How established multi-provider abstractions in the 2026 Python ecosystem handle the questions this milestone faces, plus how we compare. Confidence: MEDIUM (web-sourced).

| Concern | LiteLLM | Instructor | AbstractCore | Our Approach |
|---------|---------|------------|--------------|--------------|
| Provider interface | Unified `completion()` taking OpenAI-shape input; translates internally | Wraps each SDK; user picks the SDK | "Code once, run everywhere" — unified | Custom 2-method interface (`complete_text`, `complete_structured`). No translation layer — both adapters speak native HTTP. |
| Strict structured output | Via `response_format` (provider-specific behind the scenes) | Pydantic models + automatic retry on validation failure | Consistent API for tools/structured | Anthropic native tools + `tool_choice` with `disable_parallel_tool_use`; OpenAI `response_format: json_schema strict`. Schema is one Python dict, shared across both. |
| Error normalization | Common exception hierarchy mapped from provider errors | Lets validation errors bubble after retry | Common exception types | Common exception hierarchy (TS-11) — provider HTTP responses mapped at adapter boundary. |
| Retry / backoff | Built-in, configurable | Built-in for validation; external for transport | Built-in | DEFERRED to P2 (DF-2). Trade: simplicity now, add when we see signal. |
| Cost telemetry | Per-call usage + optional callbacks to LangFuse / Helicone | n/a (validation focus) | Per-call usage | Per-call `logger.info` with usage (DF-3). No external sink. |
| Streaming | Yes, normalized | Yes | Yes | Deliberately not. AF-1. |
| Cache | Optional Redis | n/a | Optional | No. AF-9. |
| Failover | Yes, configurable | n/a | Yes | Deliberately not — user-driven switch only. AF-5. |

**Takeaway:** Our approach is much narrower than these libraries by design. They are general-purpose; we are a milestone-scoped abstraction for an app with three call sites. The "no streaming / no failover / no cache" stance is what makes our scope tractable in days rather than weeks. The flip side: if a fourth call site ever appears, the existing interface should hold; if a third provider appears, ~one new file. That's the right shape for this app.

## Open Questions for Phase Planning

These don't block this research but should be answered when the phase plan is written:

1. **Should both providers' adapters live in the same package (`src/llm/`) or as siblings (`src/providers/openai.py`, `src/providers/anthropic.py`)?** Convention question; either works. ARCHITECTURE.md will pick.
2. **Where does the per-session provider state live — `st.session_state["llm_provider"]` only, or also a thread-local for non-Streamlit contexts (smoke test, future tests)?** Recommend session_state in the UI, env-var default for headless contexts. Confirm in phase plan.
3. **Should the smoke-test (TS-10) be a separate script or also a `pytest` test gated by an env flag?** Both have value. Recommend script for human-run prod-gate, pytest test for CI when CI exists (TESTING.md notes there is none currently).
4. **Is the existing `QueryError` retained for backward-compat in `src/utils.py` after TS-11 lands?** It's used by SQL execution paths too, not just LLM. Recommend: keep it for non-LLM errors, layer new LLM exception hierarchy alongside it. Confirm in phase plan.

## Sources

**Skill (HIGH confidence — operator-validated against kbroles Quicks 008-012):**
- `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\SKILL.md` — request shape, pitfalls, smoke test, strict-tools confirmation, error envelope, correlation-id rationale.

**Codebase (HIGH confidence — mapped 2026-05-19):**
- `C:\mbrunoapp\snow_query\src\query_router.py` — CS1 + CS3 current implementation
- `C:\mbrunoapp\snow_query\src\sql_generator.py` — CS2 current implementation
- `C:\mbrunoapp\snow_query\config.py` — current env-var pattern (Azure OpenAI only)
- `C:\mbrunoapp\snow_query\.planning\PROJECT.md` — decided constraints + active requirements
- `C:\mbrunoapp\snow_query\.planning\codebase\ARCHITECTURE.md` + `INTEGRATIONS.md` + `CONCERNS.md` + `STACK.md` — existing layering + integration + risk surface
- `C:\mbrunoapp\snow_query\requirements.txt` — `python-certifi-win32` already in stack (cert-store concern handled)

**Industry pattern verification (MEDIUM confidence — web-sourced, multi-source agreement):**
- [Interoperability Patterns to Abstract LLM Providers](https://brics-econ.org/interoperability-patterns-to-abstract-large-language-model-providers) — normalize at the seam, not at the call site
- [LLM API Comparison 2026 — MyEngineeringPath](https://myengineeringpath.dev/tools/llm-api-comparison/) — multi-provider strategy is now industry default
- [Unifying 3 LLM APIs in Python — DEV Community](https://dev.to/inozem/unifying-3-llm-apis-in-python-openai-anthropic-google-with-one-sdk-4l2) — adapter pattern, error taxonomy, token tracking as standard concerns
- [GitHub: llm_api_adapter](https://github.com/Inozem/llm_api_adapter) — reference implementation showing minimal interface shape
- [GitHub: AbstractCore](https://github.com/lpalbou/AbstractCore) + [AbstractCore docs](https://www.abstractcore.ai/) — reference for what a maximal unified abstraction looks like (we chose smaller)
- [LiteLLM Multi-Provider Support](https://deepwiki.com/openai/openai-agents-python/7.4-litellm-multi-provider-support) — failover / cache / streaming patterns
- [Structured Outputs Practical Guide 2026 — Techsy](https://techsy.io/en/blog/llm-structured-outputs-guide) — Anthropic tool-use as structured output mechanism
- [Structured Outputs in 2026 — DeepFounder](https://deepfounder.ai/structured-outputs-in-2026-how-to-make-llms-return-exactly-what-your-app-needs/) — strict-mode constrained decoding
- [Structured Output Comparison across LLM providers — Medium / Rost Glukhov](https://medium.com/@rosgluk/structured-output-comparison-across-popular-llm-providers-openai-gemini-anthropic-mistral-and-1a5d42fa612a) — Anthropic's tool-input-schema as the schema-enforcement primitive
- [LLM API Resilience in Production — TianPan](https://tianpan.co/blog/2026-03-11-llm-api-resilience-production) — retry / backoff / circuit breaker patterns
- [Complete Guide to LLM Observability for 2026 — Portkey](https://portkey.ai/blog/the-complete-guide-to-llm-observability/) — correlation IDs / traces / metrics as 2026 default
- [LLM Error Handling and Fallback Strategies for Production — BuildMVPFast](https://www.buildmvpfast.com/blog/building-with-unreliable-ai-error-handling-fallback-strategies-2026) — when failover helps vs hurts

---
*Feature research for: Multi-provider LLM abstraction in snow_query*
*Researched: 2026-05-19*
