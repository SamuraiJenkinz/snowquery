# Pitfalls Research — Multi-Provider LLM Refactor (Anthropic + Azure OpenAI)

**Domain:** Adding a second LLM provider (Anthropic via MGTI Apigee/Bedrock proxy) to a Streamlit/Python app that already uses Azure OpenAI
**Researched:** 2026-05-19
**Confidence:** HIGH for items extending the 12 validated baseline pitfalls (kbroles Quicks 008–012, 2026-05-11/12); HIGH-MEDIUM for multi-provider-specific items based on the snow_query codebase shape (`requests`-based, no SDK, no tests yet, three call sites, Streamlit session state).

## Scope of This Document

The mgti-anthropic-integration skill already documents **12 baseline pitfalls** (transport-layer mistakes when calling the MGTI Apigee proxy). They are referenced by number throughout this document but **not re-explained** — see `<pitfalls>` block in `~/.claude/skills/mgti-anthropic-integration/SKILL.md`. Quick index:

| # | Baseline pitfall (one-line) |
|---|---|
| 1 | Missing `/messages` URL suffix → 404 rf-route-not-found |
| 2 | Wrong model prefix / Claude <4.5 → 404 Model not supported |
| 3 | Wrong auth header (`Authorization: Bearer` vs `X-Api-Key`) |
| 4 | `system` inside `messages[]` vs top-level |
| 5 | `max_tokens` missing → 400 |
| 6 | `anthropic_version` missing/wrong → 400 |
| 7 | Blank input → guardrail false positive |
| 8 | Windows cert / corporate proxy TLS handshake |
| 9 | Don't use as Claude Code / IDE backend |
| 10 | Tools support undocumented but works |
| 11 | Error envelope shape differs from native Anthropic SDK |
| 12 | Different host (`mgti.mmc.com` vs `apis.mmc.com`) → different config |

**This document extends those with mistakes specific to running BOTH providers in the same codebase.**

---

## Critical Pitfalls

These cause silent wrong answers, broken provider selection, or full rewrites of the abstraction layer.

### Pitfall 1: Interface drift — abstraction leaks provider-specific shapes upward

**What goes wrong:**
The abstraction looks clean (`provider.complete(messages, ...)`) but it returns the raw provider response unchanged. Call sites end up doing `resp["choices"][0]["message"]["content"]` (OpenAI) or `resp["content"][0]["text"]` (Anthropic), and the `if provider == "anthropic":` branches reappear at every call site — exactly what the abstraction was supposed to prevent. Once that happens, every new call site adds two new bugs (one per provider) instead of zero.

**Why it happens:**
Easiest first cut. Returning the raw dict means "the abstraction works" against one provider in five minutes. The cost is paid later, by the next developer, at the call sites.

**How to avoid:**
- The abstraction returns a small `LLMResponse` dataclass with at minimum: `text: str`, `stop_reason: str` (normalized: `"end"`, `"length"`, `"tool_use"`, `"guardrail"`, `"error"`), `tool_use: dict | None` (parsed JSON if strict-tools mode), `raw: dict` (for debugging only — call sites must not read this in production code).
- Lint rule (or code review checklist item): grep `\bchoices\[\b|\bcontent\[0\]\[\b` outside the two adapter files — any hit is a violation.
- The three existing call sites (`classify_intent`, `generate_sql`, `generate_executive_summary`) get rewritten to consume `LLMResponse.text` and `LLMResponse.tool_use` — nothing else.

**Warning signs:**
- Reviewers see `if provider == ` or `isinstance(resp, ...)` outside the adapters
- Adding a third call site requires copy-paste of provider-detection logic
- Tests for `generate_sql` import `azure_adapter` directly to assert on the raw response

**Phase to address:**
Phase that introduces the provider abstraction (Phase 1 / "build the seam"). MUST land before the Anthropic adapter is wired in — adding the seam after both adapters exist is a 3x rewrite.

**Cross-ref:** Extends nothing — this is purely a multi-provider design pitfall. Indirectly amplifies the impact of baseline #11 (error envelope shape).

---

### Pitfall 2: Strict-tools schema drift — OpenAI `response_format` and Anthropic `input_schema` describe DIFFERENT shapes for the "same" classification

**What goes wrong:**
Today's `classify_intent` returns `{intent, confidence, reasoning, detected_filters, chart_requested, chart_type}`. With strict-tools mode on Anthropic, you write an `input_schema` (JSON Schema) for that. With OpenAI, you either don't enforce or you use `response_format={"type": "json_schema", ...}` — and the two schemas drift apart. Worst case: Anthropic enforces `detected_filters.priority: array | null`, OpenAI's free-form JSON returns `detected_filters.priority: "P1"` (string), and a downstream filter that expects a list silently corrupts queries.

**Why it happens:**
- The OpenAI path was added before strict mode existed and was tolerant by accident (string OR list both worked because downstream code coerced).
- Anthropic strict-tools forces you to commit to a shape, and the path of least resistance is to pick the strictest interpretation — which differs from what OpenAI actually returns in practice.
- `chart_requested` and `chart_type` in the existing code are populated by `_detect_chart_request()` heuristics BEFORE the LLM call (see `query_router.py:163-164, 207-209`). If you naively put them into the tool schema, the LLM will start hallucinating chart requests and overwrite the heuristic.

**How to avoid:**
- **Single source of truth for the schema.** Define a Pydantic model (or dataclass + JSON Schema generator) for `ClassificationResult`. Both adapters consume the SAME schema object — OpenAI's `response_format` and Anthropic's `tools[0].input_schema` are derived from it, not hand-written.
- **Schema = LLM contract only.** `chart_requested` / `chart_type` stay OUT of the LLM schema — they're heuristic outputs that happen at the call site, not LLM outputs.
- **Validate the OpenAI response against the same schema** even though OpenAI doesn't enforce strict mode. Pydantic validation on the way out of both adapters catches drift the first time it happens, not in production.
- Version the schema (`CLASSIFICATION_SCHEMA_V1`) so taxonomy changes are explicit; see Pitfall 8.

**Warning signs:**
- A reviewer asks "does OpenAI also return this field?" and nobody knows
- The heuristic `chart_requested` flag and a `chart_requested` field in the LLM output both exist
- `json.loads(...)` followed by `result.get("intent", "structured")` defaults — defaults hide schema drift

**Phase to address:**
Phase that adds strict-tools mode for `classify_intent`. Specifically the sub-task that defines the `ClassificationResult` schema. Must precede the Anthropic adapter integration with the call site.

**Cross-ref:** Extends baseline #10 (tools work but undocumented) — flagging tools as the primary unenforced contract surface across both providers.

---

### Pitfall 3: Provider selection captured at module import time, not per-request

**What goes wrong:**
`config.py` reads `LLM_PROVIDER` from env once. The user flips the sidebar dropdown to "Anthropic" mid-session, but `classify_intent` still calls OpenAI because the module-level singleton captured "openai" at import. Or worse: works on the dev machine because the dev sets the env var and the dropdown agrees, breaks in prod where they disagree.

**Why it happens:**
Existing code reads `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` at module import (`config.py:16-18`). The temptation is to add `ANTHROPIC_*` symmetrically and read them the same way. But Streamlit's whole UX premise is "user changes a control, the next call reflects the change" — module-level capture breaks that.

**How to avoid:**
- The selected provider name lives in `st.session_state["llm_provider"]` (default from env var on first init).
- The LLM functions take a `provider: str | None = None` parameter; when `None`, they read from `st.session_state.get("llm_provider", DEFAULT_PROVIDER)`.
- A factory function (`get_llm_adapter(provider)`) returns the adapter; it can be cached with `@st.cache_resource` keyed on `(provider, base_url, model)` so credential lookup happens once but selection happens per call.
- The provider's *credentials* (api_key, base_url, model name) come from env vars (immutable per process). The *active provider* is per-session-state.

**Warning signs:**
- Code references `AZURE_OPENAI_API_KEY` or `ANTHROPIC_API_KEY` directly inside a function body that runs per-request
- Test cases set env vars at the top of the module and assume isolation
- Streamlit reruns produce inconsistent behaviour when the user toggles the dropdown

**Phase to address:**
Phase that adds the sidebar provider selector. Before any adapter is integrated with a call site — the call site must be parameterized from day one.

**Cross-ref:** New — Streamlit-session-state-vs-LLM-config specific. Amplifies baseline #12 (host confusion) because per-process module-level capture makes it impossible to A/B the two hosts in the same session.

---

### Pitfall 4: Default-provider choice masks the regression test

**What goes wrong:**
The roadmap commits to "default provider stays Azure OpenAI initially" (PROJECT.md key decisions table). But the *test suite* and the dev's daily use both run with `LLM_PROVIDER=anthropic` because that's the new shiny thing. The OpenAI path silently bit-rots — six weeks later someone toggles back to OpenAI and `classify_intent` raises because a field was renamed in the abstraction and only the Anthropic adapter was updated.

**Why it happens:**
- Default in `.env.example` ≠ default in dev's local `.env`
- Whichever provider you're actively working on gets all the testing
- The "old" provider's path slowly diverges as the abstraction evolves
- Streamlit's auto-rerun makes manual UI testing of "the other provider" feel tedious

**How to avoid:**
- **Parameterized test fixture.** Every LLM-touching test runs against BOTH adapters via `pytest.mark.parametrize("provider", ["openai", "anthropic"])`. A single test file, two providers, no copy-paste.
- **CI matrix:** even with no live LLM access in CI, the adapters can be exercised against recorded fixtures (see Pitfall 7).
- **A daily/PR smoke task** that hits both providers' live endpoints with a canary prompt. Per the kbroles Quicks 008–012 lesson, smoke > unit for transport bugs.
- The default in `.env.example` MUST match the production default. If they diverge, that's a documentation bug.

**Warning signs:**
- `git log` shows the OpenAI adapter file untouched for >2 weeks while the abstraction has evolved
- A test exists only with `provider="anthropic"` hardcoded
- Nobody can confidently answer "does the OpenAI path still work?"

**Phase to address:**
Phase that establishes the test harness — before the Anthropic adapter has any logic worth testing. The parameterized fixture is the harness's most important shape; adding it later means rewriting tests.

**Cross-ref:** New — migration / parallel-operation specific.

---

### Pitfall 5: Mocking that lies — fixtures that don't match production wire format

**What goes wrong:**
Test mocks return the shape the code expects rather than what the providers actually return. The Anthropic adapter passes unit tests because the mock has `{"content": [{"type": "text", "text": "..."}]}` exactly — but production hits baseline pitfall #11 (proxy error envelope `{"error": {"title", "detail", "status"}}`) which the mock never modeled. The test green-lights a 4xx-handling code path that has never seen a real 4xx.

**Why it happens:**
- The dev writes the mock by looking at the code, not by capturing a real response
- The MGTI proxy envelope differs from native Anthropic SDK shape (baseline #11) — if mocks come from Anthropic's public docs, they're already wrong
- `responses.add(...)` / `unittest.mock.patch` mocks happily return whatever JSON you give them
- Streamlit's interactive UX makes "test by clicking" feel sufficient, so mocks never get rigorous

**How to avoid:**
- **Record real fixtures, don't hand-write them.** Use `vcrpy` or save raw `requests.Response` bodies (`.json` files in `tests/fixtures/anthropic/`, `tests/fixtures/openai/`) captured from real (stage) endpoints. Treat them as compiled artifacts — regenerate, don't edit.
- **Fixtures include error responses**, not just happy path: 400 (missing max_tokens), 401 (bad key), 403 (guardrail intervened — baseline #7), 404 (model not supported — baseline #2), 5xx (proxy degraded). One file per status.
- **The mock layer mounts at `requests.Session.send` or via `responses.add`**, NOT at the adapter function — that way the request URL, headers, and body shape are all asserted, catching baseline #1 (`/messages` suffix), #3 (header), #4 (system placement), #5 (max_tokens), #6 (anthropic_version) at unit-test time.
- **One adapter test asserts the OUTGOING request shape** — URL ends with `/messages`, header is `X-Api-Key`, body has top-level `system` and `anthropic_version: bedrock-2023-05-31`, and `max_tokens` is present. That single test catches five of the twelve baseline pitfalls.

**Warning signs:**
- Test fixture files are < 200 bytes (hand-written, not real)
- No fixture file for any 4xx response code
- The phrase "this works locally" appears in PR descriptions for LLM-touching code

**Phase to address:**
Phase that establishes the test harness. Capture the first fixture against the stage endpoint before writing any adapter logic — the fixture drives the adapter, not the other way around.

**Cross-ref:** Extends baselines #1, #3, #4, #5, #6, #11 — all of these become catchable at unit-test time if the mock asserts the outgoing request and uses real recorded responses.

---

### Pitfall 6: Env-var leakage between tests poisons multi-provider isolation

**What goes wrong:**
`test_classify_intent_anthropic` sets `os.environ["ANTHROPIC_API_KEY"] = "test-key"`. The next test (`test_classify_intent_openai`) inherits that env var. The OpenAI test passes because it doesn't read `ANTHROPIC_API_KEY` — until someone adds a startup validator that reads both, and now tests pass or fail based on `pytest` collection order.

Compounded for snow_query specifically: `config.py` imports execute `load_dotenv()` at import time and read env vars into module-level constants. Re-importing the module in a test doesn't re-read env vars in Python (modules are cached in `sys.modules`). Setting env vars after the first `from config import ...` is a no-op.

**Why it happens:**
- `os.environ` is process-global; pytest runs tests in one process by default
- `python-dotenv`'s `load_dotenv()` is called at import time and is a one-shot
- The `config.py` pattern of `X: str = os.getenv("X", "")` captures the value at the moment of import — once captured, env-var changes don't propagate
- Two providers means twice as many env vars to leak

**How to avoid:**
- **Use a config object, not module-level constants.** `Settings` class instantiated per call (or per-test via fixture). `AZURE_OPENAI_API_KEY` becomes `settings.azure.api_key`. Tests inject a `Settings` instance instead of patching env vars.
- **`pytest` fixture with `monkeypatch.setenv` + `monkeypatch.delenv`** at function scope — automatically reverts. Never use bare `os.environ[...] = ...` in tests.
- **Adapter constructors take config explicitly** (`AnthropicAdapter(base_url=..., api_key=..., model=...)`) and the only place env vars are read is at the Streamlit entry point. Tests construct adapters with explicit values.
- **Add a "no global state" lint check**: grep for `os.environ\[` and `os.getenv(` outside `config.py` / `settings.py` and the app entry point — any other usage is a violation.

**Warning signs:**
- `os.environ[...]` appears in any test file
- Tests pass individually but fail when run in a group (or vice versa)
- `config.AZURE_OPENAI_API_KEY` is referenced inside function bodies (not constructor params)

**Phase to address:**
Phase that introduces the provider abstraction — the migration from module-level constants to a `Settings` object is part of "building the seam." Doing this AFTER both adapters exist is a much bigger refactor.

**Cross-ref:** New — testing-pitfall specific. Indirectly enables Pitfall 4 (default-provider drift) when env-var leakage means "which provider got tested" is order-dependent.

---

### Pitfall 7: Subtle behavior differences between providers — temperature, stop sequences, JSON-mode prompt sensitivity

**What goes wrong:**
The exact same prompt at `temperature=0.1` returns:
- OpenAI: clean JSON in `content`, no preamble
- Anthropic: `"Here is the classification:\n\n```json\n{...}\n```"` — wrapped in markdown, with a chatty preface

The existing code at `query_router.py:184-189` has special handling for markdown code blocks ("Handle markdown code blocks"). That handler was written for OpenAI's occasional markdown wrapping and may not cover Anthropic's variations (e.g., `` ```JSON `` capitalised, or quad-backticks). Worse, `temperature=0.1` on Anthropic Claude Sonnet 4.5 is not the same operating point as `temperature=0.1` on Azure OpenAI gpt-4o — Anthropic at low temperature has different verbosity defaults.

**Why it happens:**
- Providers have different RLHF training and different post-processing
- Temperature is *not* a portable parameter — it has provider-specific semantics
- OpenAI has had years of `response_format` / JSON-mode evolution; Anthropic's strict-tools is newer and behaves differently around schemas vs free-form
- The existing few-shot examples (`sql_generator.py:50-83`) were tuned for OpenAI's response style; Anthropic may need different few-shots or none

**How to avoid:**
- **Strict-tools mode for `classify_intent`** (already in PROJECT.md) — eliminates JSON parse failures and preamble issues for the one call site that returns structured data. This is the right call.
- **For SQL and summary (text mode), don't share prompts byte-for-byte.** Define `PROMPTS[provider][function]` — same content, but the Anthropic version explicitly says "Return ONLY the SQL, no explanation, no markdown code fences" (or whatever's needed). Tune each independently against its provider.
- **Provider-specific generation params.** `AnthropicAdapter` and `AzureOpenAIAdapter` each have their own default `temperature`, `top_p`, etc. — don't expose temperature as a portable abstract parameter unless you've measured equivalence.
- **A/B harness**: Run the same 20-query benchmark against both providers and diff the outputs. Surfacing where they disagree is the only way to catch subtle quality drift.
- **Stop sequences**: Anthropic supports `stop_sequences` (array of strings). Don't rely on it for one provider only — either both use it or neither does.

**Warning signs:**
- `json.loads` fails for Anthropic where it succeeded for OpenAI on the same input
- Summary outputs are noticeably longer or include preambles for one provider
- The few-shot examples in `sql_generator.py` produce different SQL shapes per provider
- A single `temperature=0.1` constant is referenced from both adapters

**Phase to address:**
Phase that integrates each adapter with each call site. SQL generation (text mode, prompt-sensitive) is the riskiest — measure before declaring done.

**Cross-ref:** New — behavior-difference specific. Partially mitigated by adopting strict-tools for classification (baseline #10) but ONLY for that one call site.

---

### Pitfall 8: Strict-tools input_schema versioning as classification taxonomy evolves

**What goes wrong:**
The classification taxonomy today is `intent ∈ {structured, semantic, hybrid}`. Three months from now a new intent is added (`comparative`, `temporal_analysis`, whatever). The Anthropic `input_schema` is updated to allow the new enum value. The OpenAI prompt is updated to mention it. But:
- Old session-state cache contains a serialized classification result with the old shape — Pydantic validation raises on load
- A cached result in DuckDB / Chroma metadata references `intent="comparative"` which the downstream filter logic doesn't recognize
- The Anthropic schema is updated but the OpenAI prompt isn't (or vice versa) — providers now classify into different taxonomies
- A logged historical query says `intent="hybrid"` but in v2 hybrid means something subtly different

**Why it happens:**
- JSON Schema doesn't have a built-in "schema version" field
- Enums in `input_schema` look like prose but are wire contracts — changing them is a breaking change
- Multiple sources of truth (OpenAI prompt text, Anthropic JSON Schema, downstream Python dispatch in `route_query`) drift unless explicitly coupled

**How to avoid:**
- **Single Python source of truth.** `class IntentV1(str, Enum)`. Both the OpenAI prompt and the Anthropic schema are generated from it (the prompt enumerates `IntentV1.__members__.keys()`, the schema's `enum:` is derived).
- **Version the schema in the name.** `ClassificationResultV1`, `ClassificationResultV2`. The adapter records which version it sent. Logged/cached results include the version. Downstream `route_query` dispatches on `(version, intent)`, not bare `intent`.
- **Migration path documented.** When V2 is introduced: old V1 results still parse; the dispatch logic handles both; deprecation timeline is explicit.
- **`input_schema` tests**: a snapshot test (`schema_v1.json`) — any change to the generated schema requires updating the snapshot, which forces conscious review.
- **Don't put `confidence` thresholds in the schema** — that's runtime policy. The schema just declares the field exists.

**Warning signs:**
- The string `"structured"` appears in more than two files (drift surface)
- No `_schema_version` field anywhere
- The Anthropic `tools[0].input_schema` is hand-edited in adapter code (not generated)
- Streamlit displays classification results that were cached from a previous app version

**Phase to address:**
Phase that defines the `ClassificationResult` schema and wires strict-tools mode. The versioning convention must be in place at v1 — retrofitting versioning is painful.

**Cross-ref:** Extends baseline #10 (tools work but undocumented) — versioning is the discipline that makes tool-based contracts safe over time.

---

### Pitfall 9: Logging / observability when output shape varies by provider

**What goes wrong:**
Today the log line is `logger.info("Classified as: structured (confidence: 0.92)")` (`query_router.py:201`). With two providers, you also want to know which one answered, how long it took, the correlation ID (baseline correlation_ids section in skill), token usage (different shapes per provider), and the model name. Naive approach: each adapter logs its own thing. Result: log analytics can't compare providers because the fields differ. You can't answer "is Anthropic slower than OpenAI for classification?" without re-parsing two log shapes.

**Why it happens:**
- Anthropic returns `usage: {input_tokens, output_tokens}` (and proxy may pass it through; may not)
- OpenAI returns `usage: {prompt_tokens, completion_tokens, total_tokens}`
- The MGTI proxy strips/adds things relative to native Anthropic — verify per-deployment
- Latency, retries, and HTTP status are not standardized across providers in any wire spec

**How to avoid:**
- **Normalize at the adapter boundary.** Every LLM call emits one structured log record with a fixed schema: `{provider, model, call_site, latency_ms, input_tokens, output_tokens, stop_reason, status, correlation_id, request_id}`. Adapter is responsible for translating its provider's native usage shape into these field names.
- **`X-Correlation-Id` is mandatory** (already in PROJECT.md) — generate per call, log it alongside the application request, send it to Anthropic. For Azure OpenAI, also generate one and log it on the request side even though the upstream doesn't echo it back.
- **Streamlit display**: when "show provider details" is enabled, the UI surfaces `provider | model | latency_ms | tokens` from the normalized record — same display regardless of provider.
- **Sensitive payload redaction**: don't log full prompts (incident data may be in them). Log prompt length and a hash, not content.
- **Token-cost calculation** lives outside the adapters (pricing tables change), keyed on `(provider, model, input_tokens, output_tokens)`.

**Warning signs:**
- Logs contain `prompt_tokens` AND `input_tokens` (two field names for same thing)
- No way to query "average latency per provider over last 24h"
- Correlation ID appears in OpenAI logs but not Anthropic (or vice versa)
- An LLM error log line includes the raw provider payload — that's a data-leak path

**Phase to address:**
Phase that introduces the provider abstraction — observability schema is part of the seam, not an afterthought. The adapter-level structured logger must exist before either adapter has logic.

**Cross-ref:** Extends baseline #11 (error envelope shape) — normalized logging is the place where the proxy's error shape gets translated into a uniform `status` and `error_detail` field.

---

### Pitfall 10: Re-running app.py with cached `@st.cache_resource` adapter holding stale config

**What goes wrong:**
The adapter is cached with `@st.cache_resource`. The user updates `.env` (e.g., rotates `ANTHROPIC_API_KEY` because the previous one was revoked), restarts only Streamlit, sidebar still says "Anthropic," but every call uses the old cached adapter with the old key — 401s flood the logs. Or the dev switches `ANTHROPIC_MODEL` from sonnet to opus, restarts Streamlit, but the cache is keyed on the provider name only, so the model swap doesn't take effect.

**Why it happens:**
- `@st.cache_resource` returns the same object until you explicitly clear it or change the cache key
- Streamlit "restart" via `streamlit run` may or may not reset cache depending on the watch / hot-reload mode
- Cache key derivation is easy to get wrong (e.g., keying on `provider` only, forgetting `base_url` / `model`)

**How to avoid:**
- **Cache key includes everything that affects behavior**: `get_llm_adapter(provider, base_url, api_key_fingerprint, model)`. Use a hash of the API key (last 4 chars + length), never the key itself.
- **Sidebar "Reload config" button** that calls `st.cache_resource.clear()` and re-reads env. Cheap UX, prevents 10 minutes of confused debugging.
- **On startup**, log the active config (with key redacted) so the dev sees what was actually loaded.
- **Don't cache the response, only the client.** Tempting to memoize classification of the same query — don't, because the provider/model affects the answer and you'd cache cross-provider.

**Warning signs:**
- A dev had to fully restart Streamlit to pick up a `.env` change
- A 401 storm appears after a key rotation
- Two devs see different behavior with "the same" config — one is on a cached adapter

**Phase to address:**
Phase that adds the sidebar provider selector — the adapter factory and its caching strategy ship together with the UI control.

**Cross-ref:** New — Streamlit-specific.

---

## Moderate Pitfalls

These cause delays or technical debt but are recoverable.

### Pitfall 11: Duplicated `_call_azure_openai` in `query_router.py` and `sql_generator.py`

**What goes wrong:**
The function `_call_azure_openai(messages)` is currently defined twice — once in `query_router.py:105-141` and once in `sql_generator.py:86-`. They differ slightly (max_tokens 500 vs 1000). When refactoring to the provider abstraction, it's easy to migrate one and miss the other, leaving one call site still hardcoded to Azure OpenAI.

**Why it happens:**
Pre-existing duplication. The abstraction refactor will touch one file, miss the other.

**How to avoid:**
- **Search-then-replace discipline**: before starting the refactor, `grep -rn "_call_azure_openai\|AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT"` and write down every hit. The phase isn't done until every hit has been migrated.
- The adapter's `complete()` takes `max_tokens` as a parameter (with provider-aware defaults) — so call sites that previously had different limits explicitly state them.

**Warning signs:**
- After the migration, `grep` finds any remaining reference to `AZURE_OPENAI_*` outside `config.py` and the Azure adapter
- A user toggles to Anthropic and SQL generation still calls OpenAI (because one of the two call paths was missed)

**Phase to address:**
Phase that integrates adapters with call sites. First task: enumerate all call sites with grep, not from memory.

---

### Pitfall 12: Heuristic fallback (`_heuristic_classify`) tied to OpenAI failure mode

**What goes wrong:**
`classify_intent` falls back to `_heuristic_classify` when the OpenAI call fails or the JSON is unparseable (`query_router.py:194, 215-216`). With two providers, the fallback chain becomes ambiguous:
- Anthropic call fails — do you fall back to heuristic, or try OpenAI?
- Anthropic returns malformed JSON in text mode — heuristic, retry with stricter prompt, or fail loudly?
- Strict-tools mode on Anthropic should NEVER produce unparseable JSON — if it does, that's a different failure class entirely

**Why it happens:**
The original heuristic was added as a safety net for one provider. Two providers means three potential paths (provider A → provider B → heuristic) and unclear policy.

**How to avoid:**
- **Explicit policy decision, documented.** Recommendation: fall back to heuristic only for `network_error` / `timeout` / `auth_error` / `guardrail` from the active provider. Do NOT silently try the other provider — that would mask the fact that the user-selected provider is failing.
- **Strict-tools failures fail loudly.** If Anthropic's strict-tools mode produces invalid output (it shouldn't), raise a typed exception — don't silently downgrade to heuristic. The whole point of strict mode is the guarantee.
- **Surface the fallback to the user.** A subtle UI indicator (e.g., "Classified via heuristic — Anthropic timed out") so users know the answer quality may be different.

**Warning signs:**
- Heuristic fallback fires silently in production logs but users don't notice degraded answers
- Test cases don't cover "provider returns malformed JSON in strict-tools mode"
- The fallback policy is "whatever the code happens to do" rather than a documented decision

**Phase to address:**
Phase that integrates Anthropic adapter with `classify_intent`. The fallback policy is a sub-decision of that integration.

**Cross-ref:** Extends baseline #7 (guardrail false positive) — guardrail is a legitimate fallback trigger that needs its own UI treatment.

---

### Pitfall 13: `.env.example` divergence across the team

**What goes wrong:**
`.env.example` lists `ANTHROPIC_*` but the team has 5 different versions of `.env` locally with different defaults, different model names, different `LLM_PROVIDER` defaults. "Works on my machine" multiplies. The first user-reported bug after deploy is "I get `404 Model not supported`" because `.env.example` was updated but the deployed `.env` wasn't.

**Why it happens:**
- `.env` is git-ignored (correctly)
- No mechanism enforces `.env.example` ↔ deployed `.env` consistency
- Env-var names evolve during the milestone; old `.env` files don't pick up renames

**How to avoid:**
- **Startup validation.** App startup calls `validate_config()` which checks every required env var is present AND has a non-placeholder value (e.g., `XXX-REPLACE-ME` fails). For the inactive provider, check is "warn" not "error" so devs can run with only one provider configured.
- **`.env.example` includes a `# version: 2026-05-19` comment** that's bumped whenever vars are added/renamed; startup logs a warning if local `.env` is older.
- **Smoke test runs `validate_config()` first** — catches missing `ANTHROPIC_VERSION` etc. before the first HTTP call.

**Warning signs:**
- Two devs report different errors for "the same" setup
- A new env var was added in a PR but the deployment instructions weren't updated
- `os.getenv("ANTHROPIC_MODEL", "")` returns empty string and a 404 happens 30s later

**Phase to address:**
Phase that adds env vars (early). The validator and the `.env.example` discipline land together.

**Cross-ref:** Extends baseline #2 (model prefix) and #6 (anthropic_version) — both become catchable at startup if `validate_config()` is rigorous.

---

### Pitfall 14: HTTP timeout / retry policy mismatch between adapters

**What goes wrong:**
Current code: `timeout=30` (`query_router.py:135`). Anthropic adapter (per skill): also 30s. But:
- Anthropic Claude Sonnet 4.5 with `max_tokens=4096` can legitimately take >30s for long summaries
- The MGTI proxy adds latency on top of Bedrock
- One adapter has retries with exponential backoff, the other doesn't
- The same query gives a smooth experience on one provider, hangs the UI on the other

**Why it happens:**
- Defaults copied from existing Azure OpenAI code without re-tuning for Anthropic
- Streamlit blocks the UI thread during HTTP calls — a longer timeout shows up directly as UX
- Retry policy is easy to add to the new adapter while forgetting it on the old

**How to avoid:**
- **Per-adapter timeout config**, with sensible per-provider defaults: Azure OpenAI 30s, Anthropic 60s for text mode (long summaries), 15s for strict-tools (small structured output).
- **Single shared retry helper** (`retry_with_backoff`) used by both adapters — so retry behavior is uniform.
- **Streamlit progress indicator** (`st.spinner` with provider-aware message: "Calling Anthropic Claude..." — sets expectation).
- **The smoke test measures latency** and fails if > 2x provider's nominal SLA — catches regressions in proxy performance.

**Warning signs:**
- A user reports "Anthropic feels slow" and there's no measurement to confirm/deny
- Timeout exceptions appear for one provider but not the other under similar load
- Retry logic is copy-pasted (drift surface)

**Phase to address:**
Phase that integrates each adapter — timeouts and retries are part of "adapter is production-ready," not a polish task.

---

### Pitfall 15: Migration risk — staging vs. prod URL differs by string substring only

**What goes wrong:**
Stage: `https://stage.int.nasa.apis.mmc.com/...`
Prod: `https://int.nasa.apis.mmc.com/...`

The difference is a single `stage.` prefix. A typo in `.env` (or `.env.example`) sends prod traffic to stage and vice versa. Worse: the API key for one may "work" against the other (depending on proxy config), so the request succeeds — against the wrong environment.

**Why it happens:**
- Single-character / single-substring differences are visually hard to spot
- Both URLs validate the same way (both return 200 for valid requests)
- Env-var loading is silent — no log line confirms "I'm pointing at stage" until you read URL logs

**How to avoid:**
- **Startup logs the resolved base URL** prominently (`logger.info("Anthropic base URL: %s", base_url)`).
- **Sidebar / app header shows the active environment** in dev/stage (e.g., a small "STAGE" badge) — invisible in prod.
- **API keys are environment-scoped.** If procurement / MGTI can issue separate stage and prod keys, that's the strongest guard — a stage key against prod URL fails 401.
- **Lint / CI check**: any commit that changes `ANTHROPIC_BASE_URL` in `.env.example` requires an explicit PR description note.

**Warning signs:**
- A query "works" but the response is unexpectedly fast/slow — could be hitting the wrong env
- Stage-only data appears in prod-looking responses (or vice versa)

**Phase to address:**
Phase that adds env vars and the smoke test — startup-time URL logging + smoke test against the configured URL catches misconfig before users do.

**Cross-ref:** Extends baseline #12 (host confusion) — adds the stage/prod axis as a second dimension to get wrong.

---

## Minor Pitfalls

These cause annoyance but are quickly fixable.

### Pitfall 16: README / USER_GUIDE drift between providers

**What goes wrong:**
The README is updated for Anthropic; USER_GUIDE.md keeps its OpenAI-only screenshots. New users read inconsistent docs.

**Prevention:**
- Single "LLM Providers" doc section, both providers covered in the same section
- Update both files in the same PR (and add to the PR checklist)
- Docs PR can be the closing PR of the milestone

**Phase:** Phase that finalizes docs (last phase).

---

### Pitfall 17: Streamlit cache invalidation on provider switch

**What goes wrong:**
`@st.cache_data` on a function that takes the user's query but not the provider name — the second user query (after switching providers) returns the first provider's cached answer.

**Prevention:**
- Any `@st.cache_data` decorator on an LLM-dependent function MUST include `provider` (and `model`) in its arguments
- Better: don't cache LLM answers at the function level — cache only deterministic intermediate steps (e.g., schema summaries)

**Phase:** Phase that adds the sidebar provider selector — review existing `@st.cache_*` decorators in app.py.

---

### Pitfall 18: Error message text exposes provider internals to end users

**What goes wrong:**
A 4xx from the MGTI proxy bubbles up as `"Anthropic API call failed: HTTPError: 404 rf-route-not-found"` in the Streamlit UI. Operators see "Anthropic" and an internal proxy error code — unhelpful and reveals stack.

**Prevention:**
- Adapter raises a typed exception (`LLMError`) with user-facing `message` and developer-facing `details` (existing `QueryError` pattern in `utils.py` already has this — extend it).
- Streamlit displays `message` only; `details` goes to logs.

**Phase:** Phase that integrates Anthropic adapter with call sites.

**Cross-ref:** Extends baseline #11 (error envelope shape) — the translation from proxy envelope to typed exception happens here.

---

## Technical Debt Patterns

Shortcuts that look reasonable for a deadline but pay back badly.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Translate Anthropic responses into OpenAI shape inside the adapter | "Existing call sites don't need to change!" | Every Anthropic-specific feature (tool_use blocks, stop_reason variants, content blocks) gets squashed into a fake OpenAI shape; you fight the impedance mismatch forever | **Never.** Define a neutral `LLMResponse` type instead. (PROJECT.md key decisions already rejects this; flagging here to keep it rejected.) |
| Per-call-site `if provider == "anthropic":` branches "just for now" | Adapter ships in a day | Three call sites today → 6 branches; 8 call sites in 3 months → 16 branches; refactor cost grows superlinearly | Only for a one-line workaround documented as `# TODO: move to adapter when provider X supports Y` |
| Skip the smoke test "because unit tests pass" | Faster PR cycle | Baseline pitfalls #1, #2, #4 land in prod | **Never.** Smoke test runs in CI against stage. Validated lesson from kbroles. |
| Hand-write `tools[0].input_schema` JSON | Adapter ships in a day | Schema drift from Python source of truth → Pitfall 2 and 8 | Only for prototyping; replace with generated schema before the second call site uses it |
| Single shared `temperature` constant across providers | Looks "DRY" | Provider behavior diverges; quality regression invisible | **Never.** Each adapter has its own defaults; only override at the call site with provider context |
| Default to whichever provider the dev was last working on | "Just works for me" | Pitfall 4 — the inactive provider rots | Only during the initial spike; switch to `Settings`-based default before merging |
| Mock the adapter directly in tests (not the HTTP layer) | Tests run fast | All twelve baseline pitfalls are invisible to the test suite | Only for non-LLM-touching tests; LLM tests mock at `requests.Session` or `responses.add` level |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| MGTI Apigee proxy | Reusing `mgti.mmc.com` base URL (Azure OpenAI ingress) for Anthropic | Use `apis.mmc.com` for Anthropic (baseline #12); they are separate gateways, separate auth, separate request shapes |
| Anthropic strict-tools | Treating `tools` as a recommendation; not asserting on `stop_reason == "tool_use"` | Validate that the response actually contains a tool_use block; reject other shapes loudly. Strict mode's value is the guarantee — enforce it. |
| Streamlit session state | Reading `os.getenv("LLM_PROVIDER")` inside a function body that runs on every rerun | Initialize `st.session_state["llm_provider"]` once from env, mutate via UI control thereafter |
| `python-certifi-win32` | Forgetting it's required for the corporate Windows cert store (baseline #8) | Already in `requirements.txt`; verify it's imported before any HTTPS call; check on every dev machine |
| Azure OpenAI Chat Completions API | Assuming response shape is stable across `api-version` values | Pin `API_VERSION` in `.env`; treat changes as breaking |
| Anthropic Messages API via Bedrock proxy | Copy-pasting error handling from the official `anthropic` Python SDK | Proxy error envelope differs (baseline #11); adapter handles its own envelope |
| Both providers' usage / token accounting | Treating `prompt_tokens` and `input_tokens` as the same field | Normalize at adapter boundary; downstream code reads `LLMResponse.input_tokens` only |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous HTTP in Streamlit thread for both providers | UI hangs visibly longer on the slower provider; users assume "it broke" | `st.spinner` with provider name; consider `st.status` for multi-step ops | First concurrent user, or first long summary |
| No retry on transient 5xx | Sporadic "Anthropic call failed" with no recovery | Shared retry helper with exponential backoff + max 3 attempts; only for 5xx and timeouts, never 4xx | Proxy hiccup during demo |
| Building embeddings while LLM call in flight | RAM pressure on a single-process Streamlit app | Disable "Rebuild embeddings" button while a query is in flight | First time anyone rebuilds during an active session |
| Heuristic fallback masks performance degradation | "Classification is fast!" — because it's silently using heuristic, not the LLM | Surface fallback in UI; log heuristic vs. LLM ratio | When the provider's tail latency degrades and 30% of queries silently downgrade |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging full prompts that contain incident data | Incident data (potentially sensitive: customer names, IPs, internal hostnames) ends up in logs that leave the host | Log prompt length + SHA-256 prefix, never content. Apply to BOTH providers' adapters at the same boundary. |
| Logging the API key or `X-Api-Key` header by accident | Key in logs → key compromise | Custom log filter that redacts known sensitive header names; test the filter |
| Switching providers mid-session reveals one provider's data to the other's request | Both adapters share a `requests.Session` with cookies / connection pool | Each adapter owns its own `requests.Session`; don't share at the abstraction layer |
| API key in `.env` committed accidentally | Credential leak | `.env` in `.gitignore`; pre-commit hook scans for `*_API_KEY=` patterns |
| Defaulting to whichever provider the env says, even when sidebar says otherwise | User believes their selection is honored when it isn't — surprise data flow | Sidebar selection is authoritative once the user touches it; env is only the default |
| Sending incident data to a misconfigured / wrong-environment URL (Pitfall 15) | Data potentially routed to a less-controlled environment | Startup-time URL log + smoke test |
| MGTI proxy guardrail blocks a query and the heuristic fallback runs, sending it to "the other provider" | If fallback policy isn't explicit, you may bypass the guardrail by ricochet | Document fallback policy (Pitfall 12); guardrail → user-visible refusal, NOT cross-provider retry |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Provider name not visible in the response display | User doesn't know which provider answered; can't reproduce or compare | Show provider name (and optionally model + latency) on each assistant message |
| Switching providers mid-conversation silently changes answer style | User notices "answers feel different" but can't tell why | When provider changes, post a small inline notice ("Switched to Anthropic Claude for this and following queries") |
| `temperature=0.1` interpreted as "deterministic" but isn't | User expects identical answers, gets variation; loses trust | Document expected non-determinism; don't claim deterministic output |
| Guardrail intervention shown as a generic error | User sees "API error" — assumes app is broken, retries (uselessly) | Distinguish guardrail (= refusal, retry with different wording) from transport error (= app/proxy issue, retry as-is) |
| Long Anthropic responses get truncated at `max_tokens` without warning | User gets half a summary, doesn't know it's truncated | Detect `stop_reason == "length"` (Anthropic) / `finish_reason == "length"` (OpenAI); show a clear "(truncated)" marker; offer "continue" or increase max_tokens |

---

## "Looks Done But Isn't" Checklist

Things that pass casual inspection but are missing critical pieces.

- [ ] **Adapter implementation:** Often missing `X-Correlation-Id` generation and logging — verify a fresh UUID is sent per call AND logged with the application request log line
- [ ] **Adapter implementation:** Often missing handling for `stop_reason == "guardrail_intervened"` — verify guardrail path produces a user-visible refusal, not a retryable error (baseline #7)
- [ ] **Adapter implementation:** Often missing `max_tokens` in request body (baseline #5) — verify the adapter unit test asserts on the outgoing body
- [ ] **Provider abstraction:** Often missing a normalized `LLMResponse` type — verify no call site reads `.choices[0]` or `.content[0]` directly
- [ ] **Strict-tools mode:** Often missing assertion that `stop_reason == "tool_use"` and that the tool_use block matches the requested schema — strict mode's value is the guarantee, must be enforced
- [ ] **Schema definition:** Often missing version suffix (`ClassificationResultV1`) — verify the version is referenced in adapter, prompt template, and any cached/logged record
- [ ] **`.env.example`:** Often missing a new variable when adding it locally — verify the example file lists every variable read by `config.py` / `settings.py`
- [ ] **Smoke test:** Often missing — verify a runnable script (`scripts/smoke_test_anthropic.py`) exists that hits service-info, spend, and a minimal Create Message against the configured URL (validated kbroles Quicks 008–012 pattern)
- [ ] **Tests:** Often missing the parameterize-by-provider fixture — verify every LLM-touching test runs against both providers via a single `@pytest.mark.parametrize("provider", ["openai", "anthropic"])` decorator
- [ ] **Tests:** Often missing real recorded fixtures — verify `tests/fixtures/anthropic/` contains JSON files captured from a live stage call, not hand-written
- [ ] **Tests:** Often missing fixtures for error responses — verify there's a 400, 401, 403 (guardrail), and 404 fixture for each provider
- [ ] **Logging:** Often missing normalized fields across providers — verify a single log query can produce a "latency per provider" report
- [ ] **Sidebar:** Often missing visual indication of the active provider after a rerun — verify the dropdown's selected value persists and is reflected in the next response's metadata
- [ ] **Documentation:** Often missing the "how to switch providers" section — verify USER_GUIDE.md has explicit step-by-step instructions

---

## Recovery Strategies

When pitfalls slip past prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Interface drift (1) — branches at call sites | HIGH | Stop adding new call sites. Audit existing sites, extract a proper `LLMResponse`, refactor sites one-by-one with tests at each step |
| Schema drift (2) — providers return different shapes | MEDIUM | Define the Pydantic model, regenerate both providers' schemas/prompts from it, add validation at adapter exit, replay last 100 prod classifications to surface where they would now fail |
| Session-state-vs-config (3) — provider toggle doesn't take effect | LOW | Wire the function param + factory; add a regression test that switches mid-session |
| Default-provider drift (4) — old path bit-rotted | MEDIUM | Run the parameterized test suite against both; fix whatever broke; add to CI gate |
| Mocks lie (5) — production fails what tests pass | MEDIUM | Capture real fixtures from stage; replay the failing prod request against the test harness; add as a regression fixture |
| Env-var leakage (6) — tests order-dependent | LOW | Migrate to `Settings` object + `monkeypatch.setenv`; grep-and-eradicate `os.environ` writes outside tests' explicit setup |
| Behavior drift (7) — providers disagree on quality | HIGH | Per-provider prompt tuning; benchmark harness; may require dropping one provider for specific call site |
| Schema versioning (8) — V2 introduced without migration | HIGH | Add `_schema_version` to all records; write migration; deprecate V1 with timeline |
| Log shape inconsistency (9) — can't compare providers | LOW | Add the normalized log adapter; backfill is impossible (logs are append-only) but forward-looking fix is cheap |
| Cache staleness (10) — stale config | LOW | Add "Reload config" button; document the issue in USER_GUIDE |
| Duplicate `_call_azure_openai` (11) | LOW | Grep, delete, re-route both call sites through the abstraction |
| Heuristic fallback (12) — silent degradation | LOW | Add UI indicator; add metric for fallback rate |
| `.env.example` drift (13) | LOW | Add `validate_config()` to startup; bump comment-versioned example file |
| Timeout mismatch (14) | LOW | Tune per-adapter; add latency to smoke-test assertions |
| Wrong environment (15) — stage vs prod | MEDIUM | Add startup URL log; verify with smoke; rotate API keys if data leakage is possible |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls. Phase names below are placeholders; the roadmap creator picks final names — what matters is the ordering.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 (Interface drift) | Build the seam (abstraction layer) — BEFORE Anthropic adapter | Grep: zero references to provider-specific response shapes outside adapter files |
| 2 (Schema drift) | Define `ClassificationResult` schema — before strict-tools wiring | Schema snapshot test; Pydantic validation on both adapters' outputs |
| 3 (Session-state-vs-config) | Add sidebar provider selector | Manual test: switch provider mid-session, confirm next call uses new provider |
| 4 (Default-provider drift) | Establish test harness — before either adapter has logic | Parameterized fixture: both providers exercised by every LLM-touching test |
| 5 (Mocks lie) | Establish test harness | At least one fixture per provider captured from live stage; adapter unit test asserts outgoing request shape |
| 6 (Env-var leakage) | Build the seam — migrate config to `Settings` object | Grep: `os.environ[` / `os.getenv(` only in `config.py` / `settings.py` and entry points |
| 7 (Behavior drift) | Integrate each adapter with each call site | A/B benchmark: 20-query suite run against both, output diff reviewed |
| 8 (Schema versioning) | Define `ClassificationResult` schema | Schema name includes version (`V1`); enum source of truth is a Python class |
| 9 (Logging inconsistency) | Build the seam — add normalized log record | A single log query produces latency / token counts per provider |
| 10 (Cache staleness) | Add sidebar provider selector | "Reload config" button works; cache key includes model + base_url + key fingerprint |
| 11 (Duplicate `_call_azure_openai`) | Integrate adapters with call sites — start with grep-then-migrate | Grep for `_call_azure_openai` returns zero hits outside the legacy stub |
| 12 (Heuristic fallback policy) | Integrate Anthropic adapter with `classify_intent` | Documented policy in code comment; UI indicator visible when fallback fires |
| 13 (`.env.example` drift) | Add env vars (early in the milestone) | Startup `validate_config()` fails fast on missing/placeholder values |
| 14 (Timeout/retry mismatch) | Integrate each adapter | Smoke test measures latency; per-adapter defaults verified |
| 15 (Stage vs prod) | Add env vars + smoke test | Startup log shows resolved base URL; smoke test runs against the configured URL |
| 16 (Doc drift) | Final phase (docs) | README and USER_GUIDE updated in the same PR |
| 17 (Streamlit cache invalidation) | Add sidebar provider selector | Audit existing `@st.cache_*` decorators; add `provider` to argument list where needed |
| 18 (Error message UX) | Integrate Anthropic adapter | `LLMError` typed exception; Streamlit shows `message`, logs `details` |

**Phase ordering implication:** The seam (abstraction + `Settings` + normalized logging + test harness) MUST come before the Anthropic adapter integration. Retrofitting it after is 2–3x the cost. PROJECT.md's "provider abstraction layer over per-call `if` branches" key decision aligns with this.

---

## Sources

- **mgti-anthropic-integration skill** (`~/.claude/skills/mgti-anthropic-integration/SKILL.md`) — 12 baseline pitfalls validated against kbroles Quicks 008–012 (2026-05-11/12). HIGH confidence.
- **kbroles project Quicks 008–012** (2026-05-11/12) — original validation source for baseline pitfalls. HIGH confidence (referenced via skill).
- **snow_query codebase** (`.planning/codebase/ARCHITECTURE.md`, `src/query_router.py`, `src/sql_generator.py`, `config.py`, `app.py`) — current LLM call sites, session-state patterns, duplicated `_call_azure_openai`. HIGH confidence.
- **snow_query PROJECT.md** — milestone scope, key decisions, three call sites enumerated. HIGH confidence.
- **Streamlit caching documentation** (`@st.cache_resource`, `@st.cache_data` semantics) — MEDIUM confidence; behavior depends on Streamlit version (≥1.40 per project STACK).
- **General multi-provider LLM patterns** (LangChain-style abstractions, Pydantic-based schema sources of truth) — MEDIUM confidence based on common ecosystem patterns; not project-specific.

---

*Pitfalls research for: multi-provider LLM refactor (Anthropic via MGTI proxy + Azure OpenAI in a Streamlit/Python app)*
*Researched: 2026-05-19*
