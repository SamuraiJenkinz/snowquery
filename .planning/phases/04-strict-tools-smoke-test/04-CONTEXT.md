# Phase 4: Strict-Tools + Smoke Test - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Two coupled deliverables:

1. **Anthropic strict-tools mode for intent classification**:
   - `INTENT_TOOL: ToolSchema` derived programmatically from `ClassificationResultV1` (TOOL-02 — single source of truth) — `chart_requested`/`chart_type` stay OUT of the LLM schema (TOOL-03)
   - `AnthropicMGTIClient.classify_with_tool()` replaces the Phase 3 `NotImplementedError` stub: sends `tools=[INTENT_TOOL]` + `tool_choice={"type":"tool","name":...,"disable_parallel_tool_use":True}`; on HTTP 200 extracts the `tool_use` block input; validates via `jsonschema.validate` against `tool.input_schema`; returns `ToolCall`
   - `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch transparently falls back to text-mode + JSON parsing (already-existing env var in `.env.example`; `self._tools_supported` already loaded in Phase 3 `__init__`)
   - `classify_intent` in `src/query_router.py` merges heuristic-populated `chart_requested`/`chart_type` AFTER receiving the LLM result (TOOL-04 — LLM cannot overwrite heuristic)

2. **`scripts/smoke_llm.py` live-credential gate**:
   - `python scripts/smoke_llm.py --provider both` exits zero against the staging gateway
   - Per-provider checks: `complete()` benign prompt + `classify_with_tool()` benign query; Anthropic adds `GET /coreapi/llm/anthropic/v1/` service-info diagnostic (per SC #5)
   - Pass/fail printed per check with captured response shape
   - Operator-run gate before Phase 5 unblocks UI exposure

LOCKED FROM ROADMAP (not re-discussed):
- Schema derivation from `ClassificationResultV1` is single source of truth
- `chart_requested`/`chart_type` are heuristic-populated, NOT in LLM schema
- `tool_choice` uses `disable_parallel_tool_use=True`
- Default provider stays `azure_openai`; no UI changes in Phase 4

OUT OF SCOPE FOR PHASE 4:
- Sidebar UI toggle (Phase 5)
- README / USER_GUIDE updates (Phase 5)
- CI integration of the smoke gate (operator-run only)
- Streaming responses, prompt-caching usage fields, direct Anthropic SDK migration

</domain>

<decisions>
## Implementation Decisions

NOTE: The user delegated decision-making for all four discussed areas. Decisions below are anchored in established Phase 1-3 patterns (see [[03-CONTEXT]], [[02-CONTEXT]], and STATE.md decision log) and are LOCKED for the planner.

### Fallback strategy (ANTHROPIC_TOOLS_SUPPORTED escape hatch)

- **Env-flag-only fallback, NO runtime auto-fallback.** `classify_with_tool` checks `self._tools_supported` (already loaded in Phase 3 `__init__`) at entry. `False` → call internal `_classify_via_text_mode(messages, tool, tool_name=tool_name)` helper which builds a system prompt embedding `tool.input_schema` as JSON-schema guidance, calls `self.complete()`, parses content with `json.loads` (handling ```json markdown fences identically to query_router.py:144-148), validates the parsed dict against `tool.input_schema` via `jsonschema.validate`, returns `ToolCall`. `True` → strict-tools path.
- **Rejected alternative**: Runtime auto-fallback (try tools-mode → on tool-rejection error, retry in text-mode) adds latency, masks observability, and turns one log event into two. STATE.md flags the proxy's tool support as "undocumented" — operators need a LOUD signal (`LLMError` propagated as `QueryError`), not a quiet downgrade. If the proxy regresses on tools, the operator flips `ANTHROPIC_TOOLS_SUPPORTED=false`, restarts, sees text-mode at boot.
- **Operator visibility**: Add `tools_supported: bool` field to the existing `llm_provider_loaded` startup log event in `AnthropicMGTIClient.__init__`. Dashboards/grep see which mode is active without parsing later `llm_call` events.
- **Text-mode helper is INTERNAL** to `AnthropicMGTIClient` — does NOT import from `src/llm/azure_openai.py`. Azure already owns its own `classify_with_tool` text-mode path per [[02-PLAN-01-azure-adapter-implementation]] decision (ADP-02 prompt-based JSON parsing). Duplication is intentional, symmetric with Phase 2/3 `_log_llm_call` precedent.
- **Schema validation runs in BOTH paths** (strict-tools and text-mode fallback). The escape hatch must produce a validated `ToolCall` identical to the strict-tools `ToolCall`; downstream `classify_intent` cannot tell which path produced the result.

### classify_with_tool error handling

- **Raise `LLMSchemaError` immediately on any structural failure; NO adapter-level retry; NO adapter-level fallback to text-mode.** Caller (`classify_intent`) keeps its existing heuristic-fallback pattern at `query_router.py:171-175` — `except QueryError: raise` and the broader `except Exception` already route to `_heuristic_classify`. Adapter doesn't grow retry logic; the existing site-level pattern is sufficient.
- **Specific error matrix** (each row maps to a typed-error raise in the adapter):
  | Condition | Typed error | Message shape |
  |---|---|---|
  | HTTP 4xx/5xx, `requests.Timeout`, connection errors | Reuse `complete()`'s typed errors via shared private `_post_messages()` helper (see "Code structure" below) | Same as Phase 3 |
  | HTTP 200, `stop_reason == "guardrail_intervened"` | `LLMGuardrailError` | "Anthropic guardrail intervened on this request." (matches Phase 3) |
  | HTTP 200, empty `content[]`, non-guardrail | `LLMSchemaError` | "Anthropic MGTI returned HTTP 200 with empty content (stop_reason=X)" (matches Phase 3) |
  | HTTP 200, content non-empty, no `tool_use` block found (or first matching block missing) | `LLMSchemaError` | "missing tool_use block in content (stop_reason=X, content_types=[...])" |
  | HTTP 200, tool_use block found but `name != tool_name` | `LLMSchemaError` | "wrong tool name returned: expected X, got Y" |
  | HTTP 200, tool_use block, `input` field missing or not a dict | `LLMSchemaError` | "malformed tool_use input: expected dict, got {type}" |
  | HTTP 200, tool_use block, `jsonschema.validate(input, tool.input_schema)` raises | `LLMSchemaError` | "tool_use input failed schema validation: {jsonschema_error_message}" |
  | HTTP 200, `stop_reason == "max_tokens"` during tool_use | `LLMSchemaError` | "max_tokens reached during tool_use — input likely truncated and unreliable; raise ANTHROPIC_MAX_TOKENS" |
  | HTTP 200, `stop_reason in (None, unknown)` | `LLMSchemaError` | "unknown stop_reason: {value}" |
- **`max_tokens` for `classify_with_tool` is a SCHEMA ERROR, not a success-with-truncated outcome.** This is the ONE place where Phase 3's "truncation is a known outcome" decision (see [[03-CONTEXT]] §"stop_reason mapping") DOES NOT apply: a partial JSON tool_use input cannot pass schema validation. Locked here so the planner doesn't mistakenly copy the Phase 3 `complete()` semantics into `classify_with_tool()`.
- **Multiple `tool_use` blocks in `content`**: take the FIRST block whose `name == tool_name`. `disable_parallel_tool_use=True` should prevent multiples; defensive iteration handles the case if the proxy ignores the flag.
- **Code structure**: Extract a private `_post_messages(body: dict) -> dict` helper inside `AnthropicMGTIClient` that owns HTTP + envelope parsing + 4xx/5xx → typed-error mapping (identical to Phase 3's `complete()` lines 269-315). Both `complete()` and `classify_with_tool()` call this helper. JUSTIFICATION: Phase 3 explicitly deferred this with "If both adapters are ever unified, helper extracts to src/llm/\_log.py" — but the duplication here would be ~70 lines INTRA-MODULE (within one file), not cross-adapter. Intra-module helper extraction is established by `_build_request_body` (Phase 3). DO NOT extract to `src/llm/_log.py` — keep within `anthropic_mgti.py`.
- **`classify_with_tool` log event**: Add `llm_tool_mode: "strict" | "text_fallback"` field to the existing `llm_call` extra dict so the dashboard can distinguish strict-tool calls from fallback. All other fields (latency_ms, outcome, correlation_id, prompt_tokens, completion_tokens, stop_reason) match Phase 3 shape.

### Smoke script output & exit semantics

- **Output style**: Human-readable pretty by default. Per-check lines:
  ```
  [PASS] anthropic_mgti / service-info       → 200 in 312ms  shape={api_version, supported_models}
  [PASS] anthropic_mgti / complete           → 200 in 412ms  model=eu.anthropic.claude-sonnet-4-5-20250929-v1:0  shape={id, type, role, content, model, stop_reason, usage}
  [PASS] anthropic_mgti / classify_with_tool → 200 in 521ms  intent=structured  shape={id, type, role, content[tool_use], model, stop_reason, usage}
  [PASS] azure_openai  / complete            → 200 in 287ms  model=gpt-4o-mini   shape={id, object, choices, usage}
  [PASS] azure_openai  / classify_with_tool  → 200 in 311ms  intent=structured  shape={id, object, choices, usage}
  ```
- **Captured response shape = TOP-LEVEL KEYS ONLY**, never values. The smoke output may be pasted into an MR/Slack; values could echo incident-data fragments. Print `shape={key1, key2, ...}` from `sorted(response_json.keys())`. For `content[*]`, print block types (e.g. `content[tool_use]`).
- **--verbose flag**: Adds the full request body, full response body (raw JSON), and request headers — with `X-Api-Key` REDACTED to `***` and `Authorization` REDACTED to `***`. Default (non-verbose) mode never prints headers.
- **--json flag**: NOT added in Phase 4. Operators read this gate by eye before deploying; CI doesn't run it. Adding `--json` is premature; revisit only if CI integration lands in a future phase.
- **Exit codes**: `0` = all configured providers passed all checks. `1` = at least one CONFIGURED provider's check failed. NO sub-code differentiation — keeps `&&`-chaining trivial in operator scripts.
- **Failure mode = CONTINUE ON FAILURE.** Run ALL checks for ALL selected providers regardless of intermediate failures, aggregate at the end. Operators want "anthropic auth failed AND azure timed out" in one run, not "azure failed; never tried anthropic". Final summary block lists totals:
  ```
  Summary: 3 passed, 2 failed, 0 skipped — exit 1
  ```
- **Checks per provider**:
  - **anthropic_mgti**: (1) `GET {base_url}/` (service-info; SC #5 explicit) → expect 200; (2) `complete()` with benign system + user prompt "Reply with the single word OK." (deterministic, short, guardrail-safe); (3) `classify_with_tool()` with benign query "how many incidents are open" + the actual derived `INTENT_TOOL` schema.
  - **azure_openai**: (1) `complete()` with the same benign prompt; (2) `classify_with_tool()` with the same benign query against the Azure text-mode JSON-parse path.
- **Service-info validation depth**: Status code 200 is sufficient. Response shape captured to stdout (top-level keys) but NOT asserted — the MGTI service-info schema is undocumented and asserting fields would break on proxy upgrades. Catches the `/messages` URL bug (missing `/v1` returns 404; service-info is the canary).
- **Benign prompts MUST be guardrail-safe** — short, no PII, no system-command-like phrasing. "Reply with the single word OK." has been validated in prior MMC smoke scripts. Hardcoded in `scripts/smoke_llm.py`, not parameterized — operators should NOT pass arbitrary text and risk a guardrail flag.

### Smoke script credential & provider model

- **Credential source = `.env` via `load_dotenv()`** (matches `src/app.py` and `src/llm/config.py` pattern). NO new CLI flags for credentials. Operators set the env once, run the script. Reduces "wrong creds via CLI" surprises and matches the app's runtime behavior.
- **Required env vars per provider**:
  - Azure: `AZURE_OPENAI_ENDPOINT` AND `AZURE_OPENAI_API_KEY` — both must be non-empty
  - Anthropic: `ANTHROPIC_BASE_URL` AND `ANTHROPIC_API_KEY` AND `ANTHROPIC_MODEL` — all three must be non-empty
- **Missing-credential behavior = SKIP, not FAIL.** If a provider's required env vars are missing/empty, mark its checks as `[SKIP]` (with reason printed) and DO NOT count toward exit-code failure. Avoids "I haven't set up Anthropic yet, why is the gate red?".
  - Exception: if `--provider anthropic_mgti` is explicitly requested AND its env is missing, exit 1 with a clear "you asked for anthropic_mgti but ANTHROPIC_API_KEY is empty" message. Explicit selection should never silently skip.
  - `--provider both` (default) skips missing-env providers gracefully.
- **--provider flag values**: `azure_openai`, `anthropic_mgti`, `both` (default). Exact strings match `get_llm()`'s provider names. NO short aliases (`azure`, `anthropic`) — explicit beats clever, and the operator's mental model maps directly to the env var prefix.
- **Gate enforcement = OPERATOR-RUN, not CI.** Live credentials cannot live in CI without ops review; the smoke gate runs from an operator's terminal against the STAGING gateway before Phase 5 unblocks UI. The Phase 4 acceptance gate (pytest module) does NOT call the smoke script — it only verifies the script exists and is syntactically valid. The operator attaches smoke output (paste or screenshot) to the Phase 4 verification PR before Phase 5 work begins.
- **Pytest tests stay 100% mocked.** Mirrors Phase 1/2/3 acceptance-gate pattern (zero live HTTP from pytest). `tests/test_phase4_strict_tools.py` mocks `requests.post`/`requests.get` for every Anthropic and Azure check; the smoke script is the ONLY thing that touches the real network and runs from the operator's shell, not pytest.

### Verification strategy

- **Test module**: `tests/test_phase4_strict_tools.py` — acceptance gate covering all 5 Phase 4 success criteria. Self-contained (no `conftest.py`, matches Phase 1/2/3 pattern).
- **Verification surface**:
  - SC #1: Import `INTENT_TOOL`, assert its `input_schema['properties']` contains `version`/`intent`/`confidence`/`reasoning`/`detected_filters` AND does NOT contain `chart_requested`/`chart_type`. Assert single-source-of-truth: changing `ClassificationResultV1` field set changes `INTENT_TOOL.input_schema['properties']` (e.g. via a regeneration helper or a frozen-set comparison test).
  - SC #2: Strict-tools path — mock `requests.post` to return a valid `tool_use` response; assert request body contains `tools=[INTENT_TOOL_dict]` and `tool_choice={"type":"tool","name":"classify_intent","disable_parallel_tool_use":True}`; assert returned `ToolCall.input` validates against `tool.input_schema`. Pair-test: missing tool_use block → `LLMSchemaError`.
  - SC #3: Set `ANTHROPIC_TOOLS_SUPPORTED=false` in test env; mock `requests.post` to return a text-mode response with JSON content; assert `classify_with_tool()` returns a `ToolCall` whose `input` matches the parsed JSON; assert request body does NOT contain `tools` or `tool_choice` keys.
  - SC #4: Patch `classify_intent` to receive an LLM result with `chart_requested=True` injected into the LLM response payload; assert the final returned dict's `chart_requested` matches the HEURISTIC, not the LLM injection.
  - SC #5: File-existence check on `scripts/smoke_llm.py`; syntax check via `py_compile`. NO execution from pytest (operator-run gate). Optionally: import the script's `main()` and call with a mocked `requests` session to verify the check-orchestration logic.
- **Error-matrix tests**: Each row of the classify_with_tool error matrix above gets one pytest case (missing tool_use, wrong tool name, malformed input, schema-validate failure, max_tokens during tool_use, unknown stop_reason).
- **COMPAT-DISPATCH group**: Mirror Phase 3's pattern — verify `LLMSchemaError(provider="anthropic_mgti")` from `classify_with_tool` surfaces as the per-provider QueryError wording through `_compat.py`. Locks against the wrong-product-label regression class.
- **Combined target**: 39 (Phase 1+2+3) + ~25 Phase 4 tests = ~64 tests, all passing on `pytest -q`. Zero live HTTP.

### Claude's Discretion

User delegated all four areas; decisions above are locked. Remaining planner/executor flexibility:
- Exact Python mechanism for deriving `INTENT_TOOL` from `ClassificationResultV1` — `dataclasses.fields()` + per-field type hint mapping is the obvious approach; pydantic is NOT a dependency and should not be added solely for this. Hand-rolled `field_name → {"type": ...}` switch is acceptable.
- Exact JSON-schema type mapping (`str → "string"`, `float → "number"`, `dict → "object"`, etc.). Planner picks; the test in SC #1 verifies the result, not the implementation.
- Whether `_classify_via_text_mode` lives as a method on `AnthropicMGTIClient` or a module-level private function. Either is fine; method co-locates with state, module-level eases unit testing.
- `tools_supported` log-field placement within the `llm_provider_loaded` extra dict (alphabetical, order-of-definition, etc.).
- Exact filename of the text-mode injected system prompt template constant (e.g. `_TOOL_FALLBACK_SYSTEM_PROMPT_TEMPLATE`).
- Smoke script structure: single-file with inline check functions vs. small class. Single-file is simpler; planner picks.
- Plan breakdown: planner decides 3-vs-4 plan split. Suggested split: (1) `INTENT_TOOL` derivation + heuristic merge in `classify_intent`, (2) `classify_with_tool` strict-tools path + text-mode fallback + `_post_messages` helper extraction, (3) `scripts/smoke_llm.py`, (4) acceptance gate. Matches Phase 3's 4-plan rhythm.

</decisions>

<specifics>
## Specific Ideas

- **`INTENT_TOOL.name = "classify_intent"`** — the value passed in `tool_choice.name`. Mirrors the function name at the call site (`query_router.classify_intent`) so logs are self-documenting.
- **`INTENT_TOOL.description` should be a short prose hint**, NOT a copy of the docstring — Anthropic's tool-use guide notes that overly long descriptions reduce model accuracy. Two sentences max: "Classify a user query about ServiceNow incidents into structured / semantic / hybrid. Extract filters and confidence."
- **The heuristic merge in `classify_intent` must run AFTER the LLM result is received, not before** — `_detect_chart_request()` already runs first at `query_router.py:121`. The merge step is the final dict construction at `query_router.py:162-169`, where `chart_requested` and `chart_type` come from the heuristic-detected locals, NOT from the LLM `result`. This pattern is already correct in the current code; Phase 4 must NOT regress it by reading `chart_requested`/`chart_type` from the LLM `ToolCall.input`. SC #4's verification query is the regression guard.
- **Anthropic `tool_use` response shape**: content blocks have `{"type": "tool_use", "id": "toolu_...", "name": "classify_intent", "input": {...}}`. The `id` is opaque to us; we use `name` for the wrong-tool check and `input` for the schema validation.
- **`disable_parallel_tool_use: True`** is REQUIRED in `tool_choice` (per SC #2). The model can in theory return multiple tool_use blocks otherwise. Even with the flag, the adapter defensively iterates `content` to find the FIRST matching `name == tool_name`.
- **The text-mode fallback's injected system prompt** must explicitly forbid markdown fences in the response, since `json.loads` then doesn't need fence-stripping logic. If the LLM ignores the instruction, the adapter strips ```json fences (mirror query_router.py:144-148).
- **Smoke script's benign user prompt for `classify_with_tool`** = "how many incidents are open". This phrase exercises the structured-intent branch (most common, simplest), avoids semantic-search keywords that could surprise the model, and is plainly guardrail-safe.
- **Existing call site `classify_intent` does NOT yet call `classify_with_tool`** — it calls `complete()` with prompt-based JSON parsing. Phase 4's Plan must migrate it to `classify_with_tool` (TOOL-05 / TOOL-06) AND preserve the existing heuristic-fallback try/except shape at `query_router.py:171-175`.

</specifics>

<deferred>
## Deferred Ideas

- **CI integration of `scripts/smoke_llm.py`** — operator-run gate only in Phase 4. Adding to CI requires ops review of how live credentials are stored; possible future phase, not this milestone.
- **`--json` output flag on the smoke script** — only needed when CI consumes the output programmatically. Operator-eye consumption doesn't need it. Revisit if CI integration lands.
- **Automatic runtime tool-rejection detection** (auto-fallback from strict-tools to text-mode based on MGTI proxy returning a specific error) — explicitly rejected as silent-downgrade risk. If proxy regresses, operator flips `ANTHROPIC_TOOLS_SUPPORTED=false`. Revisit only if operator-toggle friction proves load-bearing.
- **Retry on `LLMSchemaError` from `classify_with_tool`** — heuristic fallback at the call site already handles this. Adapter-level retry adds complexity without proven value.
- **Schema versioning beyond `version: "v1"`** — `ClassificationResultV1` has `version` as a literal field. A future Phase could derive `v2` schema and dispatch on response `version` field. Out of scope; Phase 4 only ships v1.
- **Anthropic prompt-caching usage fields** (`cache_creation_input_tokens`, `cache_read_input_tokens`) — Phase 3 deferred; Phase 4 inherits the deferral. Revisit if Phase 5 prompt-caching work lands.
- **Multi-tool support** (more than `INTENT_TOOL`) — Phase 4 ships exactly one tool. Architecture supports multiple via `ToolSchema` indirection, but no other call site needs strict-tools today.
- **Migration of `classify_with_tool` for Azure OpenAI to use Azure's native function-calling** — Phase 2 locked Azure on prompt-based JSON parsing (ADP-02). No Phase 4 work changes this; Azure stays text-mode for `classify_with_tool` until a future phase justifies the migration.
- **The Anthropic spec PDF's `tools` examples that omit `disable_parallel_tool_use`** — known proxy-version issue per the MGTI skill. Phase 4 explicitly sends `disable_parallel_tool_use=True`; if a future proxy version makes this required-but-renamed, the adapter rev follows.

</deferred>

---

*Phase: 04-strict-tools-smoke-test*
*Context gathered: 2026-05-21*
