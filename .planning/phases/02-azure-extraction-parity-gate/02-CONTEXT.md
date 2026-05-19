# Phase 2: Azure Extraction + Parity Gate - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract the two duplicated `_call_azure_openai` definitions (`src/query_router.py:105` and `src/sql_generator.py:86`) into a single `AzureOpenAIClient` adapter behind the Phase 1 seam, route the three call sites (intent classification at `query_router.py:180`, SQL generation at `sql_generator.py:194`, executive summary at `query_router.py:542`) through `LLMClient` via dependency injection, and prove byte-identical output against a pre-refactor baseline before any subsequent phase introduces a non-Azure provider.

**Hard constraints carried from ROADMAP.md success criteria:**
- `_call_azure_openai` is gone from both `src/query_router.py` and `src/sql_generator.py` — grep returns zero hits
- All three call sites consume `LLMClient` via dependency injection (not module-level import of a global)
- Five representative queries spanning structured / semantic / hybrid intents and the executive-summary path produce byte-identical output to the pre-refactor capture — this is the gate, not a goal
- User-visible error contract is preserved: Azure timeout / 5xx → `QueryError` (NOT `LLMError`) at the call-site boundary; the existing remediation text (e.g. "Set the AZURE_OPENAI_API_KEY environment variable.") still reaches the user
- One structured log event per `complete()` call carrying provider, model, latency_ms, outcome, and (when available) prompt + completion token counts
- **No Anthropic code in this phase** — Phase 3 introduces `AnthropicMGTIClient`; Phase 2 only proves the seam is real and the parity story holds

This phase is the parity gate that unlocks Phase 3. If parity fails, Phase 3 is blocked.

**Already locked from Phase 1 (don't revisit):**
- `complete()` takes `messages: list[dict]` in Azure-native shape — the adapter does not translate
- `max_tokens` is a per-call kwarg on `complete()` (the only diff between the two duplicated definitions today is 500 vs 1000)
- Error taxonomy is flat under `LLMError`; `LLMAuthError`/`LLMTransientError`/`LLMTimeoutError` exist but are catchable by name at call-site boundary
- `get_llm()` is cached; cache key is provider string only (no fingerprint until Phase 5 needs it)
- `validate_config()` is explicit at app.py startup — Phase 2 does NOT call it from adapters

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (all four discussed areas)

User explicitly delegated these four areas to research + planner ("make decisions for these areas based on research and known documentation"). Researcher should investigate and propose; planner should bake the chosen shape into tasks. No further user input required unless a decision creates ambiguity downstream.

**1. Parity capture & verification mechanism**

- *The hard constraint:* five queries (structured / semantic / hybrid / executive-summary path; researcher picks the fifth) must produce byte-identical output before vs after extraction. "Byte-identical" is the literal contract — Azure responses are non-deterministic at `temperature=0.1`, so live A/B against the real endpoint will not pass this bar reliably.
- *Options researcher should weigh:*
  - **Recorded-replay** (e.g. `responses`, `vcrpy`, or hand-rolled JSON fixtures): capture real Azure responses for the five queries once, save as fixtures, mock the HTTP layer in the parity test, assert the new adapter routes the recorded response through the same downstream code path (JSON parsing, error handling, message-list shape) and produces the same final string the call site returned today.
  - **Frozen-response unit test**: stub `complete()` to return a fixed string and prove the call site's downstream parsing is unchanged. Simpler but doesn't exercise the adapter's HTTP shape.
  - **Hybrid**: recorded fixtures for the HTTP layer + frozen strings for the post-`complete()` parsing.
- *What "byte-identical" applies to:* the final string the call site returns to its caller — not Azure's raw response. The adapter is allowed to add structure (return a `CompletionResult` with `text`); the call site extracts `.text` and downstream parsing must match exactly.
- *Picking the five queries:* researcher must surface this from the existing app — look at any saved queries, USER_GUIDE examples, or test fixtures; otherwise propose five that span the four intent paths the router classifies (structured / semantic / hybrid / + executive-summary path which fires after results return).
- *Out of scope:* live regression testing against the real Azure endpoint in CI. Capture is one-time; replay is the gate.

**2. Error translation seam (LLMError → QueryError at the call-site boundary)**

- *Hard constraint:* Phase 2 success criterion #3 says timeout / 5xx surface to the user as `QueryError`, not `LLMError`. Today this happens inline at the bottom of each `_call_azure_openai` (`except requests.exceptions.RequestException: raise QueryError(...)`); after extraction the adapter raises typed `LLMError` subclasses, so *someone* upstream of the adapter must translate.
- *Preserve user-visible remediation text*: the current `QueryError("Azure OpenAI API key not configured", "Set the AZURE_OPENAI_API_KEY environment variable.")` and similar must still appear. The translation layer cannot collapse all `LLMError` subclasses into a single generic `QueryError("LLM failed")` — at minimum the remediation text on config-related failures must survive.
- *Options researcher should weigh:*
  - **Per-call-site try/except**: each of the three call sites wraps `client.complete(...)` in `try: ... except LLMError as e: raise QueryError(...) from e`. Boilerplate × 3, but explicit and grep-friendly.
  - **Shared helper / context manager**: `with _llm_to_query_error(): result = client.complete(...)` — single source of truth for the translation table, but adds an indirection.
  - **Decorator on each call-site function**: cleanest read at call site, hardest to grep when debugging.
- *Constraint that picks the winner:* the translation table is small (config → QueryError with remediation; auth → QueryError; timeout/5xx → QueryError; otherwise re-raise). Researcher should propose the option that makes the translation table appear exactly once in the codebase and lets each call site stay readable.
- *Test surface:* the parity test (decision 1) must cover error paths too — verify a stubbed `LLMAuthError` from the adapter still surfaces as the same `QueryError` text users see today.

**3. Structured log shape (one event per `complete()` call)**

- *Hard constraint from criterion #4:* one event per call, must contain provider name, model, latency_ms, outcome, token counts when available.
- *Open shape decisions:*
  - **Format:** JSON line on stdout? Python `logging` with `extra={...}` dict? A small dedicated structured-logging helper (`log_llm_call(...)`) that the adapter calls in a `finally:` block?
  - **Granularity:** single event after the call (simpler, current-style) vs start+end pair (better for distributed tracing but overkill here).
  - **`outcome` field values:** `"success" | "error"` plus an `error_type` field on errors? Or a richer enum (`success | timeout | auth_error | transient | unknown`)?
  - **Token counts when missing:** Azure usually returns `usage` but it can be absent on certain failures. Omit the field, set to `null`, or log `0`?
- *Researcher should investigate:*
  - Existing logging convention in `src/utils.py` (and what `logger.info` calls look like in the current codebase — extend that style, do not invent a parallel one)
  - Whether Streamlit's stdout capture in dev surfaces these logs visibly, or whether logs go to a file; the answer shapes whether JSON-line or formatted-text is more useful for the user during development
- *Planner instruction:* whatever shape is chosen, the same shape must be reusable by Phase 3 (`AnthropicMGTIClient` emits identical event structure) — otherwise we're back to per-provider divergence.

**4. Dependency injection pattern (how the three call sites consume `LLMClient`)**

- *Hard constraint from criterion #1:* call sites use the seam "via dependency injection." This explicitly rules out module-level globals being baked in at import time.
- *Phase 5 constraint that bounds this:* Phase 5 needs adapter re-resolution when the user switches provider in the sidebar mid-session. A pattern that captures the adapter once at module load breaks Phase 5. The factory's cache (`@lru_cache` or equivalent on `get_llm`) handles re-resolution when the provider key changes — so calling `get_llm()` inline at each call site is safe and Phase-5-compatible.
- *Options researcher should weigh:*
  - **Inline `client = get_llm()` at the top of each call-site function**: relies on factory cache, zero call-site signature change, tests monkeypatch `get_llm` or the underlying registry. Smallest diff against today.
  - **Function parameter `def generate_sql(..., llm: LLMClient | None = None)`**: cleaner for tests (pass a stub directly), but ripples through the three call-site signatures and any caller — verify no caller depends on positional args.
  - **Module-level lazy singleton (`_LLM: LLMClient | None = None; def _get(): ...`)**: rejected — duplicates factory cache and breaks Phase 5.
- *Constraint that picks the winner:* parity gate must pass with minimal diff to call-site internals. Researcher should propose the option that lets the parity test stub the adapter at exactly one point per call site (whether that's `get_llm` itself or a function param), and that doesn't force Phase 5 to re-architect injection.
- *Test override mechanism:* the parity test (decision 1) needs to swap in a recorded-fixture-replaying fake. Whatever DI pattern is chosen, the test must be able to substitute that fake without touching the adapter's HTTP code.

</decisions>

<specifics>
## Specific Ideas

- **The duplication baseline:** RESEARCH.md (Phase 1) already audited the two `_call_azure_openai` definitions and confirmed the only logic difference is `max_tokens` (500 in `query_router.py`, 1000 in `sql_generator.py`). Phase 1's `complete()` accepts `max_tokens` as a per-call kwarg precisely to make this extraction trivial — researcher should treat that as a load-bearing decision, not revisit it.
- **Three call sites are explicit:** `query_router.py:180` (classify_intent → max_tokens=500), `sql_generator.py:194` (generate_sql → max_tokens=1000), `query_router.py:542` (generate_executive_summary → max_tokens=500). Phase 2 plans should enumerate these exactly.
- **Phase 1 acceptance gate pattern is the model:** `tests/test_llm_seam.py` proves each numbered Phase 1 criterion with one pytest module. Phase 2 should ship the equivalent — one pytest module that proves each of the four Phase 2 success criteria, with the parity test being the headline.
- **Phase 3 alignment:** any shape decision (log format, error translation seam, DI pattern) should be one that Phase 3's `AnthropicMGTIClient` can adopt without modification. If a Phase 2 choice would force Phase 3 to invent a parallel pattern, pick a different choice. The `mgti-anthropic-integration` skill (in `~/.claude/skills`) documents the MGTI HTTP shape — researcher can cross-check that the chosen log/error/DI pattern stays Phase-3-clean.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-azure-extraction-parity-gate*
*Context gathered: 2026-05-19*
