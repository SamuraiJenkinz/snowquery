# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** Phase 5 — Sidebar UI Toggle + Documentation (Plans 05-01, 05-02, 05-03, 05-04 complete; 05-05 acceptance gate next and final)

## Current Position

Phase: 5 of 5 (Sidebar UI Toggle + Documentation) — IN PROGRESS
Plan: 4 of 4 in Phase 5 (05-01, 05-02, 05-03, 05-04 all complete; 05-05 acceptance gate is the only remaining plan)
Status: Plan 05-03 (per-message provenance caption) complete. app.py gains `_render_provenance_caption(provider, model)` at module scope with explicit positional args + docstring-locked "MUST NOT read st.session_state" invariant; extended import line `from src.llm import get_llm, load_settings, missing_vars`; capture block in `process_query` (lines 897–906) that resolves `_client = get_llm()` → `_provider = getattr(_client, "provider_name", session_state fallback)` → `_model = getattr(_client, "_model", "unknown")` BEFORE the happy-path return; happy-path return dict gains `"provider"` + `"model"` keys; `render_chat_history` renders caption ABOVE `st.markdown(content)` dual-guarded by `role == "assistant" AND message.get("provider")`; on-submit `st.chat_message("assistant")` block renders caption ABOVE `st.markdown(response["content"])` guarded by `response.get("provider")`; `st.session_state.messages.append({...})` persists `provider` + `model` keys per assistant message. Early-return error paths intentionally unchanged — caption guard handles their absence. AST check verified helper body is session_state-free. Ordering check (cap_idx < md_idx) holds at both render sites. Strict app.py-only scope — no edits to src/, scripts/, tests/, README.md, USER_GUIDE.md, .env.example. Full 69-test suite still green.
Last activity: 2026-05-22 — Completed 05-PLAN-03-per-message-provenance-caption.md

Progress: [█████████░] 95% (19/20 plans complete — Phase 5 acceptance gate is the final remaining plan)

## Performance Metrics

**Velocity:**
- Total plans completed: 19 (through 05-04 — Phase 5 acceptance gate (05-05) is the only remaining plan)
- Average duration: ~4.3 min
- Total execution time: ~82 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Abstraction Seam | 3 | 11 min | ~4 min |
| 2. Azure Extraction | 4 | ~16 min | ~4 min |
| 3. Anthropic Adapter | 4 (of 4) | ~16 min | ~4 min |
| 4. Strict-Tools + Smoke | 4 (of 4) | ~22 min | ~5.5 min |
| 5. Sidebar UI Toggle | 4 (of 4) | ~32 min | ~8 min |

**Recent Trend:**
- Last 5 plans: 04-04 (4 min), 05-01 (~15 min), 05-02 (~3 min), 05-04 (~10 min), 05-03 (~4 min)
- Trend: 05-03 was app.py-only — two atomic commits (helper+capture; render+persist), no test rewires, both tasks landed first try with the 69-test suite still green. Zero merge-conflict risk: 05-03 ran after 05-02 + 05-04 (proper Wave 3 ordering per plan decision §16).

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

Decisions from 04-03 (smoke-script):
- load_dotenv() on module line 49, before src.llm imports on lines 52-54 — RESEARCH.md Pitfall 5 guard; load order is load-bearing for adapter __init__ env reading
- sys.stdout.reconfigure(encoding='utf-8') added — Rule 1 bug fix for Windows CP1252 crash on → arrow character; silently skipped on non-reconfigurable streams
- Synthetic shape strings for complete() checks — adapters return str not raw dict; Anthropic={id,type,role,content,model,stop_reason,usage}, Azure={id,object,choices,usage}
- Azure classify_with_tool signature confirmed identical to Anthropic (messages, tool, *, tool_name, **kwargs) — no adapter alignment needed; both adapters callable via same smoke script pattern

Decisions from 04-01 (INTENT_TOOL + classify_intent migration):
- INTENT_TOOL derived from ClassificationResultV1 via typing.get_type_hints() — NOT fields().type (which returns strings under `from __future__ import annotations`); this is the critical RESEARCH.md Pitfall 1 guard
- version: str stays plain string (no Literal["v1"]/const/enum) per locked decision §2 — future v2 updates dataclass + derivation helper together
- additionalProperties: false on derived schema — LLM cannot inject chart_requested/chart_type even by accident
- result["intent"] used directly in return dict (not .get("intent","structured")) — schema required+enum guarantees presence; defaulting silently masks contract violation
- test_phase2_parity.py updated (Rule 1 deviation): 3 tests tested old complete() call path in classify_intent; updated to mock classify_with_tool and ToolCall directly; all 39 tests green

Decisions from 05-02 (sidebar selectbox + warning):
- Locked UI strings preserved verbatim from ROADMAP SC #1: selectbox label 'LLM provider' (lowercase 'provider', single space); options ['Azure OpenAI', 'Anthropic Claude (MGTI)']; internal keys 'azure_openai' / 'anthropic_mgti' matching _REGISTRY — single source of truth lock between UI label and factory dispatch
- Position locked: between EMBEDDINGS and CONFIG. The LLM PROVIDER block ends with its own st.divider() (closing separator). Existing EMBEDDINGS-vs-LLM-PROVIDER divider preserved
- Module-level _PROVIDER_OPTIONS / _PROVIDER_LABELS / _PROVIDER_KEYS at app.py:364–370 (after MODE_OPTIONS) — co-located UI mapping constants. _PROVIDER_OPTIONS insertion order is load-bearing (Azure first → default selectbox index points at it); _PROVIDER_KEYS derived as tuple(values()) at definition time
- Session-state init with .strip() + clamp-to-_PROVIDER_KEYS + logger.warning on unknown — defends against typos ("Anthropic_MGTI", "anthropic"), empty string, trailing whitespace. Selectbox index=_PROVIDER_KEYS.index(...) is ValueError-safe by construction
- Active-model caption via load_settings() NOT get_llm() — sidebar render must not side-effect adapter construction or @st.cache_resource resolution or startup-log emission on every rerun (decision §11)
- Azure model derived via _extract_model_from_endpoint imported from src.llm.azure_openai (leading underscore intentional; Phase 5 reaches across package internals — same pattern Plan 05-01 established for cache-key derivation). Anthropic model read directly from settings.anthropic_model
- 'NOT CONFIGURED' caption fallback: when _active_model is empty string, caption renders 'NOT CONFIGURED' literal — read-only display, never crashes the render
- missing_vars() called every rerun — NOT @st.cache_data wrapped (would defeat credential-addition-then-refresh detection, RESEARCH.md Pitfall 10). os.getenv is O(1) so cost is negligible
- Warning template names each missing var with backticks + lists BOTH recovery paths (add to .env + restart OR switch back to Azure OpenAI). icon=':material/warning:' is Streamlit Material-icon syntax (verified working at 1.40+)
- st.session_state['_llm_provider_blocked'] decouples sidebar render from main-content render through session_state alone — no parameter ripple, no function-signature changes; main() docstring documents the load-bearing render_sidebar-before-render_main_content order (RESEARCH.md Pitfall 5)
- st.chat_input modified ONLY at the placeholder + disabled= keyword args (lines 947–953). _blocked = st.session_state.get("_llm_provider_blocked", False) — defaults safely if key absent; placeholder swaps to 'QUERY DISABLED — see sidebar warning' when blocked (RESEARCH.md Pitfall 3 guard)
- render_main_content otherwise UNTOUCHED — history rendering, message dict append, process_query call, etc. all preserved; Plan 05-03 owns per-message caption work
- Single 'from src.llm import' line at app.py:20 = 'from src.llm import load_settings, missing_vars'. Plan 05-03 will EXTEND this same line to add get_llm (per Plan 05-03 decision §14, Option B). Do NOT split into multiple from src.llm import lines
- Selectbox key= intentionally omitted — index=... + manual write-back chosen for consistency with existing MODE selectbox pattern (decision §5)
- No deletions of existing widgets — pure additive; DATA INGEST, DATA STATUS, EMBEDDINGS, CONFIG, MODE selectbox, all main-content widgets UNCHANGED. Only app.py modified — no src/, no tests/, no docs

Decisions from 05-03 (per-message provenance caption):
- Capture location LOCKED inside process_query AFTER route_query success and BEFORE the happy-path return — guarantees the captured (provider, model) reflects the adapter that actually produced THIS response, future-proof against retry/fallback wrappers
- Re-call get_llm() inside process_query for _client/_provider/_model — cache hit via @st.cache_resource (Plan 05-01's 4-arg tuple key), zero extra HTTP, zero extra startup log
- Defensive getattr with double-fallback: getattr(_client, "provider_name", st.session_state.get("llm_provider", "unknown")) → three-layer fallback (abstract property → sidebar-written session_state → literal 'unknown'). _model fallback is literal 'unknown' (no session_state fallback because resolved model is adapter-private)
- Early-return error paths (NO DATA LOADED, NO EMBEDDINGS, route_query error) DO NOT carry provider/model — intentional. The dual-guard on the caption render skips them silently (no false-positive 'via **Azure OpenAI**' captions on errors that didn't involve the LLM)
- Helper API LOCKED: _render_provenance_caption(provider: str, model: str | None) -> None at app.py module scope with EXPLICIT positional args + docstring containing the verbatim string 'CRITICAL INVARIANT: This helper MUST NOT read st.session_state' — Plan 05-05 will add an AST-based regression test for this invariant (helper body must be session_state-free)
- Caption format LOCKED verbatim from RESEARCH Recommendation 3: f"via **{human_name}** · `{model}`" (interpunct · is U+00B7). When model is falsy, drops to f"via **{human_name}**" (helper handles both branches)
- Provider human-name via _PROVIDER_LABELS.get(provider, provider) — reuses Plan 05-02's module-level dict (single source of truth). Unknown provider key degrades gracefully to the raw string (no crash; legible for future provider additions)
- Render position: FIRST inside `with st.chat_message(...):` context manager, BEFORE st.markdown(content). Verified by python regex window-check: cap_idx < md_idx at BOTH render sites
- Dual-guard at history render site: `role == "assistant" AND message.get("provider")` — BOTH conditions required. Role check excludes user messages permanently; dict-key check skips early-return error paths (NO DATA LOADED etc.) that intentionally don't carry provenance
- On-submit live render guards on `response.get("provider")` alone — the `with st.chat_message("assistant"):` block establishes role context structurally (no `role` field on the response dict)
- Append-with-`.get(...)`-fallback: two new keys `"provider": response.get("provider"), "model": response.get("model")` at the END of the assistant message dict (trailing comma added to chart_feedback for Black-style cleanliness). `.get` access (vs subscript) preserves SC #3 contract — if process_query returned an early-error dict without provider/model, append still succeeds with None values; caption guard skips render
- Single from-src-llm import line LOCKED: `from src.llm import get_llm, load_settings, missing_vars` at app.py:20 (Option B from plan decision §14 — extended the Plan-05-02 line in-place; alphabetized: get_llm, load_settings, missing_vars). NO inline `from src.llm import get_llm` inside any function body. Verified: `grep -cE '^from src\.llm import' app.py` = 1
- Wave 3 placement justified by hard-dependency on both Plan 05-01 (provider_name abstract property) AND Plan 05-02 (_PROVIDER_LABELS dict + the import line being extended). Three-wave ordering (Wave 1 = 05-01, Wave 2 = 05-02 + 05-04, Wave 3 = 05-03, Wave 4 = 05-05) cleanly serializes the file-shared edits to app.py between 05-02 and 05-03

Decisions from 05-04 (README + USER_GUIDE):
- README/USER_GUIDE split LOCKED per RESEARCH.md Rec 4: README owns setup audience (env vars, smoke-test how/when, MGTI/Hubble pointer); USER_GUIDE owns use audience (in-app switching, captions, warnings, first-time checklist). One cross-link from README to USER_GUIDE — zero content duplication.
- 7 exact UI strings quoted verbatim in both docs (RESEARCH.md Pitfall 13 docs-drift guard): selectbox label `LLM provider`, options `Azure OpenAI` + `Anthropic Claude (MGTI)`, sidebar header `LLM PROVIDER`, blocked-input placeholder `QUERY DISABLED — see sidebar warning`, caption format `via **<Provider>** · \`<model>\``, Hubble URL, smoke_llm.py script path.
- USER_GUIDE section-header style `## LLM Provider Selection` (NO numeric prefix) matches the existing file convention where all 12 other `## SectionName` headers lack numeric prefixes — the plan's verify-check `^## [0-9]+\. ...` was style-stricter than the file. TOC's numbered list (1.–11.) remains authoritative section ordering. Plan 05-05 acceptance gate should grep `^## LLM Provider Selection`, NOT `^## 9\. LLM Provider Selection`.
- Anthropic optional-vars consolidated into ONE table row (ANTHROPIC_VERSION / MAX_TOKENS / TEMPERATURE / TIMEOUT_S / TOOLS_SUPPORTED) pointing at .env.example — avoids 5-row bloat while keeping the variable names searchable.
- Warning-Resolution table contains 5 rows (3 Anthropic + 2 Azure) matching src/llm/config.py:_REQUIRED_VARS exactly — the table is the documented mirror of _REQUIRED_VARS, so any future required-var change must update both. Recovery paths (2 of them: `.env`+restart, or switch back) listed inline after the table.
- Version stamp bumped from `December 2024 (v2.0 - Added password protection & chart visualization)` to `May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)` — preserves existing parenthetical-versioning convention; date uses today's planning context.
- Strict docs-only scope: ZERO edits to .env.example, src/, scripts/, tests/, app.py, ROADMAP.md, REQUIREMENTS.md — verified by `git diff --stat HEAD -- src/ scripts/ tests/ app.py .env.example` returning empty.
- No screenshots embedded in either doc — both docs preserve their image-free convention (RESEARCH.md Rec 4 explicit decision); zero matches for image-embed regex confirmed.

Decisions from 05-01 (factory cache + helpers):
- Single cache layer LOCKED: Phase 1 module-level _cache: dict DELETED; @_cache_resource on _get_llm_cached is the only cache (RESEARCH.md Pitfall 6); Phase 1 anticipated this at __init__.py:59-60 comment
- Cache key tuple order LOCKED: (provider, base_url, model, api_key_fingerprint) — all positional, all hashable strings; switching ANY of these four re-resolves the adapter
- _fingerprint(api_key) empty key returns '' (NOT hashlib.sha256(b"").hexdigest()[:8]) — unconfigured-provider cache slot must be distinct from any real key's slot
- _fingerprint uses hashlib.sha256(key.encode("utf-8")).hexdigest()[:8] — 32 bits of entropy is sufficient for cache-invalidation purposes; NEVER substring of raw key; NEVER raw key in cache-key tuple (RESEARCH.md Pitfall 1)
- Streamlit decorator with try/except fallback at module scope: try import streamlit; except → def _cache_resource(func=None, **kwargs): pass-through. Tests defend missing .clear() via getattr(_get_llm_cached, "clear", None) + callable(...)
- missing_vars() as SEPARATE function (not validate_config(raise_on_missing=False)) — Open Question 3 resolved by Researcher recommendation: distinct API for distinct purpose (UI runtime vs startup-time guard)
- missing_vars unknown provider returns [] (not raises) — sidebar selectbox enum validates upstream; UI must not raise (Pitfall 7); validate_config keeps its raise-on-unknown contract
- provider_name as @property @abc.abstractmethod on LLMClient (NOT class attribute) — forces every future adapter to deliberately implement it; concrete returns ('azure_openai' / 'anthropic_mgti') match _REGISTRY keys AND startup-log provider= strings — single source of truth lock
- test_phase2_parity.py:354 WRITE rewired via patch.object(llm_pkg, "_get_llm_cached", return_value=fake) — Option A from plan decision §7; chosen over Option B (mock at different seam, too invasive) and Option C (debug-only _set_cached_for_testing() helper, violates Pitfall 6 single-cache lock)
- _install_raising_client renamed to _make_raising_client (builder, not installer) — sets fake.provider_name = 'azure_openai' for MagicMock(spec=AzureOpenAIClient) + Task 1.1 abstract-property compatibility
- _extract_model_from_endpoint imported from src.llm.azure_openai (NOT reimplemented) — leading underscore intentional; Phase 5 reaches across package internals per decision §5
- test_abc_contract_enforced updated to expect frozenset({"complete", "classify_with_tool", "provider_name"}) — inline Complete/MissingOne test subclasses got provider_name overrides

Decisions from 04-04 (acceptance gate):
- Test module self-contained — no conftest.py, no pytest.ini, no new tests/fixtures/ files (matches Phase 1/2/3 acceptance-gate pattern; four phases consistent now)
- Inline mock-response builders used INSTEAD of fixture files — RESEARCH.md "Mock Response Builder Pattern" applied (same as Phase 3 gate)
- _RecordCapturer mirrors test_phase3_adapter.py:412-420 VERBATIM — locked decision §3; subclass logging.Handler, override emit()
- COMPAT-DISPATCH covers LLMSchemaError + LLMGuardrailError — no _compat.py edits needed; catch-all `except LLMError` branch already dispatches by e.provider since Phase 3-02
- SC #4 test patches get_llm + classify_with_tool to inject chart_requested=True into ToolCall.input, then asserts classify_intent reads from heuristic locals (False) — strongest TOOL-04 regression guard without live HTTP
- Combined suite: 69 tests (39 prior + 30 Phase 4), all passing, 8.05s, zero live HTTP

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

### Phase 4 Sign-Off

Phase 4 (Strict-Tools + Smoke Test) is complete. All 5 ROADMAP success criteria proven by tests/test_phase4_strict_tools.py (30 tests, ~8s, zero live HTTP calls). classify_intent uses strict-tools when ANTHROPIC_TOOLS_SUPPORTED=true and JSON-parse text-mode fallback when false; INTENT_TOOL is derived programmatically from ClassificationResultV1 (single source of truth, chart fields excluded by design); heuristic-merge regression locked by SC #4 test; COMPAT-DISPATCH pair covers LLMSchemaError + LLMGuardrailError; smoke script exists and compiles cleanly. Combined suite: 69 tests (39 + 30), 0 failures, 8.05s.

Verifier outcome: 4/5 automated + 1 human_needed (SC #5 live-execution against stage gateway). User explicitly approved deferring the live smoke run to the Phase 4 verification PR review (operator-run, not CI — original phase contract per CONTEXT.md §Smoke script credential). VERIFICATION.md captures the operator checklist item. Phase 5 (Sidebar UI Toggle) is unblocked.

### Pending Todos

None.

### Blockers/Concerns

- Phase 5 Plans 05-01, 05-02, 05-03, 05-04: ALL COMPLETE; no smoke gate required for these (05-01 pure infrastructure, 05-02 pure additive UI in app.py, 05-03 pure additive UI metadata capture + render in app.py, 05-04 docs-only) — all four exercised by the unchanged 69-test acceptance suite.
- Plan 05-05 (acceptance gate) is the only remaining Phase 5 plan. UNBLOCKED on all upstream dependencies (provider_name property from 05-01, sidebar wire-up from 05-02, per-message caption + persistence from 05-03, docs from 05-04). Critical SC #4 test (history-survives-provider-switch) is now fully exercisable since 05-03 lands write-time capture + read-from-stored-dict render pattern. Plan 05-05 should also include an AST-based regression test asserting `_render_provenance_caption` body is session_state-free (Pitfall 11 lock).
- Operator-run smoke gate against stage gateway (`python scripts/smoke_llm.py --provider both --verbose`) still pending — NOW DOCUMENTED PROMINENTLY in BOTH README ("### Smoke Test (operator-run)") and USER_GUIDE (First-Time Anthropic Setup Checklist step 3) by Plan 05-04. Must land before any production deploy.
- Plan 05-05 acceptance gate: Plan 05-04 outputs are ready for SC #5 docs-content assertions. Critical: grep for `^## LLM Provider Selection` (NO numeric prefix) in USER_GUIDE.md — see 05-04 decisions block above for the style-resolution explanation.
- Plan 05-05 acceptance gate: Plan 05-03 outputs are ready for SC #4 caption + history-survives-switch assertions. For the dual-render-site check, prefer AST-walker (find `ast.With` nodes whose context manager is `st.chat_message(...)`) over literal-string grep — `render_chat_history` uses dynamic `st.chat_message(message["role"])` (pre-existing pattern, not a Plan 05-03 deviation).
- Manual UI verification (operator running Streamlit and clicking through the sidebar) is the responsibility of the Phase 5 verification PR review — Plan 05-05 (acceptance gate) covers it programmatically via streamlit mocks.
- Phase 4 MGTI usage block pass-through and X-Correlation-Id echo — RESOLVED-BY-OBSERVATION-STEP (tests/manual/observe_correlation_echo.py exists). Live observation still pending operator availability of a stage ANTHROPIC_API_KEY — to be combined with smoke gate run.

## Session Continuity

Last session: 2026-05-22T02:06:09Z
Stopped at: Plan 05-03 (per-message provenance caption) complete — 2/2 tasks committed atomically (8c4a12d feat: helper + capture; a5e3480 feat: render + persist), SUMMARY.md created, STATE.md updated; full 69-test suite green (7.83s). All 4 of 4 Phase 5 implementation plans now complete (05-01, 05-02, 05-03, 05-04). Plan 05-05 (acceptance gate) is the only remaining Phase 5 plan and is now unblocked on every upstream dependency.
Resume file: None
