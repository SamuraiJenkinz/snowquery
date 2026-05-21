# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** Phase 4 — Strict-Tools + Smoke Test (Phase 3 complete)

## Current Position

Phase: 4 of 5 (Strict-Tools + Smoke Test) — In Progress
Plan: 2 of ~4 in Phase 4 (04-02 complete)
Status: classify_with_tool fully implemented (strict-tools + text-mode fallback + _post_messages helper); 39/39 tests green. Plan 04-03 (Azure parity) and 04-04 (acceptance gate) unblocked.
Last activity: 2026-05-21 — Completed 04-PLAN-02-classify-with-tool-strict-tools-and-fallback.md

Progress: [████████░░] 78% (13/16 plans estimated)

## Performance Metrics

**Velocity:**
- Total plans completed: 11 (through 03-04 — Phase 3 fully complete)
- Average duration: ~3 min
- Total execution time: ~32 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Abstraction Seam | 3 | 11 min | ~4 min |
| 2. Azure Extraction | 4 | ~16 min | ~4 min |
| 3. Anthropic Adapter | 4 (of 4) | ~16 min | ~4 min |

**Recent Trend:**
- Last 5 plans: 03-02 (2 min), 03-03 (8 min), 03-04 (3 min), 04-01 (~3 min), 04-02 (7 min)
- Trend: consistent 2-8 min/plan; 04-02 (classify_with_tool implementation + _post_messages extraction) shipped in 7 min

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 1: Provider abstraction layer (`abc.ABC` + two adapters) over per-call `if` branches — interface drift is the dominant pitfall to prevent
- Phase 2: Parity-first refactor — Azure extraction must produce byte-identical output to today before Anthropic is introduced
- Phase 3: Anthropic adapter speaks native MGTI shape, no OpenAI-translation middleware
- Phase 4: Strict-tools mode for `classify_intent` only — `chart_requested`/`chart_type` stay out of the LLM schema (heuristic-populated)
- Phase 5: Default provider stays `azure_openai` so upgrade is byte-identical for existing deployments

Decisions from 01-01 (package skeleton):
- Flat error hierarchy (no retryable grouping) — add in Phase 5 if retry logic lands
- `complete()` takes `messages: list[dict]` (Azure-native shape) — Anthropic adapter extracts system internally
- `ClassificationResultV1` excludes `chart_requested`/`chart_type` — heuristic-only fields (TOOL-03)
- `ToolCall.raw_response` uses `field(repr=False)` — debug payload never leaks into repr/logs

Decisions from 01-02 (config + factory + stubs):
- Factory does NOT call validate_config() itself — explicit call at app.py startup (Phase 5)
- Cache key is provider string only — no api_key fingerprint until Phase 5 needs mid-session reload
- Adapter __init__ is no-op in Phase 1 (no raise) so factory cache can store instance
- st.session_state wrapped in try/except Exception (not hasattr) per RESEARCH.md verified pattern

Decisions from 01-03 (smoke verification):
- pytest 9.0.2 already installed — no requirements.txt change needed (dev-only)
- tests/ directory created without __init__.py (pytest discovers by collection)
- Acceptance gate pattern established: one pytest module per phase proves each numbered success criterion
- Cache-clear autouse fixture required for module-level singletons in get_llm

Decisions from 02-01 (azure adapter implementation):
- No .strip() in adapter — call sites strip; double-strip is idempotent but breaks byte-identity parity (Pitfall 1 guard locked)
- LLMConfigError embeds provider-specific remediation text at raise time so _compat.py uses str(e) for QueryError.message — Phase-3-clean (OQ-1 resolved)
- classify_with_tool uses prompt-based JSON parsing (ADP-02) — Azure stays on prompt+parse; provider-side strict-tools reserved for Anthropic in Phase 4
- _log_llm_call() is module-level in azure_openai.py; Phase 3 copies it verbatim to anthropic_mgti.py (intentional duplication — no premature extraction)

Decisions from 02-02 (error-translation seam):
- LLMConfigError branch passes str(e) through to QueryError.message — provider embeds remediation text at raise time; compat layer stays provider-agnostic (Phase-3-clean, no "Azure"/"Anthropic" text here)
- LLMAuthError branch hardcodes Azure remediation text for byte-identical Phase 2 parity — KNOWN Phase 3 debt: revisit when Anthropic adapter lands to dispatch on e.provider
- src/llm/_compat.py NOT re-exported from src/llm/__init__.py — call sites import directly from src.llm._compat (leading underscore = package-internal signal)
- Catch-all except LLMError is final branch — future subclasses (LLMGuardrailError etc.) never leak past the seam; Phase 3 can add dedicated branch above catch-all or rely on it

Decisions from 02-03 (call-site migration):
- Call-site DI pattern locked in: client = get_llm() inline at top of function; no function-parameter ripple; no module-level singleton
- .strip() kept at call site (adapter returns raw content — double-strip is idempotent but breaks byte-identity parity guarantee; Pitfall 1 guard confirmed)
- max_tokens=500 at classify_intent+generate_executive_summary; max_tokens=1000 at generate_sql — load-bearing difference preserved across extraction
- generate_executive_summary broad except Exception: return None intentionally NOT changed (Pitfall 4 — QueryError swallowed here silently; non-fatal exec summary path unchanged)
- grep -rn _call_azure_openai src/query_router.py src/sql_generator.py → zero hits (ABS-06 complete; comments in locked src/llm/ files are documentary, not code)

Decisions from 02-04 (acceptance gate):
- Test module is self-contained — no conftest.py or pytest.ini added; matches Phase 1 gate pattern
- Level A patching (requests.post) for adapter-direct parity tests; Level B (factory cache injection) for error-translation tests — separation of concerns
- CS3 (generate_executive_summary) tested to silently return None on LLM error — INTENTIONAL invariant (RESEARCH.md Pitfall 4), not a bug; Phase 3 must not add `except QueryError: raise` to CS3
- chromadb installed (was already in requirements.txt but not in test env); Rule 3 blocker

Decisions from 03-01 (env + startup log):
- Startup log lives in adapter __init__ (not in factory __init__.py) — each adapter owns its own observability contract; factory cache handles "once per process" idempotence at the consumer boundary, not the producer
- Distinct event tag llm_provider_loaded vs llm_call — two different lifecycle events deserve two different tags; field-name namespaces also kept disjoint (provider/base_url vs llm_provider/llm_model) so dashboards can filter cleanly
- Log fires UNCONDITIONALLY (even when base_url is empty) — operator wants the signal "I tried to load <provider> and got base_url=''", not a silent skip
- ANTHROPIC_MODEL placeholder is a concrete eu.anthropic.claude-sonnet-4-5-20250929-v1:0 (not a generic stub) so cp .env.example .env produces a config that constructs without LLMConfigError; SC #2's prefix check passes against the template
- .env.example default LLM_PROVIDER_DEFAULT=azure_openai locked from Phase 5 — Phase 3 does NOT flip the default; existing deployments remain byte-identical until an operator opts in
- Plan 03 contract: mirror this __init__ logger.info block verbatim in AnthropicMGTIClient.__init__ with provider="anthropic_mgti" and base_url=self._base_url to satisfy SC #5 fully

Decisions from 03-02 (compat provider dispatch):
- Phase 2 KNOWN DEBT (LLMAuthError hardcoded Azure remediation) RESOLVED — _compat.py now dispatches on e.provider in 4 branches (LLMAuthError, LLMTimeoutError, LLMTransientError, catch-all LLMError); LLMConfigError branch UNCHANGED (Phase 2 OQ-1 lock holds)
- getattr(e, "provider", None) used (not e.provider) — defensive against any third-party LLMError subclass that bypasses our __init__; three extra characters, zero behavior cost
- Azure path is unconditional fallback in every dispatched branch — covers provider=None, provider="azure_openai", AND any future adapter not yet wired into dispatch; Phase 2 acceptance gate (which injects provider="azure_openai") still passes byte-identically
- Dispatch extended beyond originally-debted LLMAuthError to also cover LLMTimeoutError, LLMTransientError, catch-all LLMError (per orchestrator OQ-2) — prevents wrong-product-label UX bug where Anthropic timeout would surface as "Azure OpenAI API call failed"; 12 additional lines, no Phase 2 test asserts non-Azure text so safe to land
- Anthropic-named QueryError wording locked: "Anthropic API key not configured or not authorised" (auth) / "Anthropic API call failed" (timeout/transient/catch-all) — Plan 04 acceptance gate will grep-assert these strings
- Module docstring updated from "Phase 3 may revisit this branch" to "Phase 3 dispatches on e.provider — see if-branches below"; debt note in code is now closed
- No helper extraction — the file's value is being a single, readable translation table; repetition is the point

Decisions from 03-03 (Anthropic adapter implementation):
- Init-time vs HTTP-time validation split: non-empty bad-prefix model raises at __init__ (catches typos before factory cache fills); missing env (api_key/base_url/model) raises at first complete() with provider-specific remediation text (preserves Phase 1 no-op factory pattern)
- startswith('eu.anthropic.claude-opus-4-7') used for sampling-param omission match — NOT a regex; CONTEXT.md "matching opus-4-7*" is satisfied by startswith which covers opus-4-7-20251201-v1:0 and any future opus-4-7 variant
- _log_llm_call COPIED VERBATIM from src/llm/azure_openai.py — intentional duplication per Phase 2 decision 02-01; no premature extraction. If both adapters ever unify, helper moves to src/llm/_log.py
- response.ok-based HTTP-error dispatch (NOT raise_for_status) — MGTI error envelope {error: {title, detail, status}} parsed BEFORE raising typed error so title/detail embed in LLMError message (RESEARCH.md Pitfall 1)
- correlation_id = str(uuid.uuid4()) generated BEFORE the try block — guarantees finally's _log_llm_call has it even if requests.post raises immediately (e.g. DNS failure firing RequestException before response is created) — Pitfall 5
- system key OMITTED entirely from request body when no system messages present (NOT sent as empty string) — Anthropic Messages API distinguishes absent from empty
- max_tokens stop_reason returns text WITH outcome='truncated' (does NOT raise) — caller chose max_tokens, truncation is a known outcome, not a failure
- Guardrail check BEFORE content-emptiness check in HTTP 200 dispatcher — the single biggest source of latent bugs per RESEARCH.md Pitfall 4; locked order documented as inline numbered comment block
- Field-name normalization at log boundary: Anthropic's usage.input_tokens/output_tokens → extra['llm_prompt_tokens']/extra['llm_completion_tokens'] (matches Azure's prompt_tokens/completion_tokens semantics) so dashboards aggregate across providers without per-provider field maps
- X-Correlation-Id echo verification deferred to OPERATOR (manual script at tests/manual/observe_correlation_echo.py) — observation step, not runtime dependency; STATE.md blocker resolved-by-observation (OQ-3); no adapter code path depends on a particular echo outcome
- __repr__ override returns 'AnthropicMGTIClient()' — OBS-03 regression guard symmetric with Azure; API key cannot leak via repr/Streamlit session inspection
- classify_with_tool stub body BYTE-IDENTICAL to Phase 1 — Phase 4 territory; raise NotImplementedError("AnthropicMGTIClient.classify_with_tool is implemented in Phase 4")

Decisions from 04-02 (classify_with_tool strict-tools + fallback):
- _post_messages extracted intra-module (NOT to src/llm/_log.py): owns HTTP + 4xx/5xx envelope; shared by complete() and classify_with_tool(); does NOT own timing or log emission
- Env-flag-only fallback: self._tools_supported False->_classify_via_text_mode; NO runtime auto-fallback (loud signal if proxy regresses on tools)
- max_tokens during tool_use raises LLMSchemaError (DIVERGES from complete()'s truncated-as-success); message mentions "raise ANTHROPIC_MAX_TOKENS"
- Guardrail check BEFORE missing-tool_use check — load-bearing order lock: guardrail -> max_tokens -> tool_use extraction -> input validation -> schema validation
- _emit_log: bool = True kwarg on complete(); text-mode wrapper passes _emit_log=False to suppress delegate's event; ONE event per classify_with_tool in both paths
- _classify_via_text_mode self-contained (no cross-adapter import); system-prompt mirrors azure_openai.py:254-264; fence-stripping mirrors query_router.py:144-148
- tools_supported added at END of llm_provider_loaded extra dict (order-of-definition lock)
- jsonschema upgraded from 4.25.1 -> 4.26.0 (requirements.txt pin >=4.26.0,<5 now satisfied)

Decisions from 04-01 (INTENT_TOOL + classify_intent migration):
- INTENT_TOOL derived from ClassificationResultV1 via typing.get_type_hints() — NOT fields().type (which returns strings under `from __future__ import annotations`); this is the critical RESEARCH.md Pitfall 1 guard
- version: str stays plain string (no Literal["v1"]/const/enum) per locked decision §2 — future v2 updates dataclass + derivation helper together
- additionalProperties: false on derived schema — LLM cannot inject chart_requested/chart_type even by accident
- result["intent"] used directly in return dict (not .get("intent","structured")) — schema required+enum guarantees presence; defaulting silently masks contract violation
- test_phase2_parity.py updated (Rule 1 deviation): 3 tests tested old complete() call path in classify_intent; updated to mock classify_with_tool and ToolCall directly; all 39 tests green

Decisions from 03-04 (acceptance gate):
- Test module self-contained — no conftest.py, no pytest.ini added; matches Phase 1/Phase 2 gate pattern across all three phases now
- Inline mock-response builders (_make_anthropic_response, _make_error_response) used INSTEAD of fixture files — Phase 3 has no parity baseline so the Phase 2 fixture-file pattern does not apply (CONTEXT.md decision); RESEARCH.md "Mock Response Builder Pattern" applied
- _RecordCapturer is a class-level helper (not a fixture) — adds handler in test body and removes in finally; no global logger mutation; the autouse fixture pattern from Phase 2 is preserved for env/cache isolation only
- anthropic_env and opus_env are SEPARATE non-overlapping fixtures (not parameterized) — opus path's response body uses a different model field AND triggers a different code branch in _build_request_body; separating keeps SC #2 test names self-documenting
- Empty-model no-raise verified TWICE in one test (test_init_no_raise_on_empty_model): __init__ constructs successfully AND complete() pre-flight raises LLMConfigError — both halves of the Phase 1 no-op pattern proved intact
- Guardrail/Schema-error PAIR (test_guardrail_intervened_raises_guardrail_error + test_empty_content_non_guardrail_raises_schema_error) is the load-bearing regression guard for RESEARCH.md Pitfall 4 — if adapter reorders the checks, only the latter passes; both must be green
- COMPAT-DISPATCH group (2 tests) deliberately exercises Plan 02's per-provider dispatch end-to-end with provider='anthropic_mgti' tag — locks against the "wrong product label in UI" regression class; pattern to replicate in Phase 4's gate (e.g. for LLMSchemaError(provider='anthropic_mgti') → tool-mode QueryError wording)

### Phase 1 Sign-Off

Phase 1 (Abstraction Seam) is complete. All 5 ROADMAP.md success criteria are proven by the acceptance gate at tests/test_llm_seam.py (6 tests, 0.42s, zero live HTTP calls). The seam is stable for Phase 2 to plug AzureOpenAIClient into.

### Phase 2 Sign-Off

Phase 2 (Azure Extraction + Parity Gate) is complete. All four ROADMAP success criteria proven by tests/test_phase2_parity.py (12 tests, ~8s, zero live HTTP calls). Azure adapter extraction verified byte-identical across 5 fixtures covering all 3 call sites. Combined suite: 18 tests, 0 failures. Phase 3 (Anthropic MGTI Adapter) is unblocked.

### Phase 3 Sign-Off

Phase 3 (Anthropic MGTI Adapter) is complete. All 5 ROADMAP success criteria proven by tests/test_phase3_adapter.py (21 tests, ~8s, zero live HTTP calls). Anthropic adapter is wired against the MGTI Apigee proxy with full typed-error mapping (401/403/429/5xx/Timeout/Guardrail/Schema), structured logging (llm_provider_loaded + llm_call), and per-provider QueryError dispatch through Plan 02's _compat layer. Adapter reachable via get_llm('anthropic_mgti'). classify_with_tool intentionally remains a NotImplementedError stub — Phase 4 territory. Combined suite: 39 tests, 0 failures. Phase 4 (Strict-Tools + Smoke Test) is unblocked.

### Pending Todos

None.

### Blockers/Concerns

- Phase 4: MGTI proxy strict-tools support is "works as of 2026-05-12 but undocumented" — `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch must be verified against staging before relying on tools in prod
- Phase 4: MGTI `usage` block pass-through and `X-Correlation-Id` echo — RESOLVED-BY-OBSERVATION-STEP (tests/manual/observe_correlation_echo.py exists). Live observation still pending operator availability of a stage ANTHROPIC_API_KEY — to be combined with Phase 4 smoke test per ROADMAP.md. No adapter code path depends on the outcome.

## Session Continuity

Last session: 2026-05-21T18:52:10Z
Stopped at: Completed 04-PLAN-02-classify-with-tool-strict-tools-and-fallback.md — classify_with_tool implemented (strict + text-mode); _post_messages extracted; 39/39 tests green; Plan 04-03 (Azure parity) unblocked
Resume file: None
