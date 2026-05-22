---
phase: 05-sidebar-ui-toggle-documentation
plan: 03
subsystem: ui
tags: [streamlit, chat_message, caption, provenance, llm-toggle, session_state, brutalist]

# Dependency graph
requires:
  - phase: 05-sidebar-ui-toggle-documentation
    provides: "Plan 05-01 — LLMClient.provider_name @abstractmethod + concrete returns ('azure_openai' / 'anthropic_mgti'); get_llm()/_get_llm_cached on @st.cache_resource"
  - phase: 05-sidebar-ui-toggle-documentation
    provides: "Plan 05-02 — module-level _PROVIDER_LABELS dict + the single `from src.llm import load_settings, missing_vars` line that Plan 05-03 extends with get_llm; st.session_state['llm_provider'] init pattern"
provides:
  - "_render_provenance_caption(provider: str, model: str | None) -> None at app.py module scope — explicit-args helper that NEVER reads st.session_state (Pitfall 11 regression vector locked by docstring)"
  - "process_query happy-path return dict now carries 'provider' and 'model' keys captured via get_llm() + getattr(_client, 'provider_name', ...) / getattr(_client, '_model', 'unknown') at write time"
  - "render_chat_history() renders the caption ABOVE st.markdown(content), dual-guarded by role == 'assistant' AND message.get('provider')"
  - "On-submit st.chat_message('assistant') block renders the caption ABOVE st.markdown(response['content']), guarded by response.get('provider')"
  - "st.session_state.messages.append() now persists 'provider' and 'model' keys into each assistant-message dict — historical messages survive provider switch unchanged"
  - "Extended single module-level import line: `from src.llm import get_llm, load_settings, missing_vars` (Option B from plan decision §14 — no inline imports inside process_query)"
affects: [05-05-acceptance-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Write-time provenance capture: read client.provider_name + client._model from the cached adapter instance INSIDE the producing function (process_query), persist into the message dict, render from the stored dict — never recompute from current session_state at render time"
    - "Explicit-args render helper with docstring-locked invariant: helper takes (provider, model) positional args; docstring forbids reading st.session_state; AST check verifies body is session_state-free (Pitfall 11 regression vector)"
    - "Defensive getattr with double-fallback: getattr(client, 'provider_name', st.session_state.get('llm_provider', 'unknown')) — uses Plan 05-01's abstract property when present, sidebar-written session-state value as first fallback, 'unknown' literal as last resort"
    - "Dual-guard at history render site: role == 'assistant' AND message.get('provider') — first guard excludes user messages permanently; second guard skips early-return error paths (NO DATA LOADED, NO EMBEDDINGS) that intentionally don't carry provenance"

key-files:
  created: []
  modified:
    - "app.py — only file touched. Line 20: import line extended to `from src.llm import get_llm, load_settings, missing_vars`. Lines 373–395: new `_render_provenance_caption` helper inserted immediately after `_PROVIDER_KEYS`. Lines 728–735: caption render block in `render_chat_history`. Lines 897–906: capture block in `process_query` before happy-path return; return dict gains `provider` + `model` keys (915–917). Lines 1016–1024: caption render block in on-submit `st.chat_message('assistant')` block. Lines 1046–1048: `st.session_state.messages.append({...})` extended with `provider` + `model` keys."

key-decisions:
  - "Decision §1 — Capture inside `process_query` AFTER `route_query` (so we only capture on success) and BEFORE the final return (so the value reflects the adapter that produced the response, future-proof against retry wrappers)"
  - "Decision §2/§3 — Re-call `get_llm()` inside `process_query` for `_client`/`_provider`/`_model` (cache hit via `@st.cache_resource` — zero HTTP, zero extra startup log). Defensive `getattr` with double-fallback: client attr → session_state.get('llm_provider', 'unknown') → literal 'unknown'. `_model` fallback is literal `'unknown'` (no session-state fallback because session_state doesn't store the resolved model)"
  - "Decision §4 — Early-return dicts (NO DATA LOADED, NO EMBEDDINGS, `route_query` error) DO NOT carry provider/model. The dual-guard on the caption render skips them silently. No false-positive 'via **Azure OpenAI**' captions on errors that didn't involve the LLM"
  - "Decision §5 — Helper reuses Plan 05-02's `_PROVIDER_LABELS` module-level dict (single source of truth — no duplicate). Unknown provider key degrades gracefully to the raw string (no crash; legible for future provider additions)"
  - "Decision §6 — Caption format LOCKED verbatim from RESEARCH Recommendation 3: `f\"via **{human_name}** · `{model}`\"`. When `model` is falsy, drops to `f\"via **{human_name}**\"`. Use of interpunct `·` (U+00B7) is intentional — visually distinct separator without being aggressive like the existing project's em-dash"
  - "Decision §7 — Helper API is `_render_provenance_caption(provider, model)` with EXPLICIT positional args. Docstring locks the invariant: 'CRITICAL INVARIANT: This helper MUST NOT read st.session_state'. AST-based verify check confirms helper body is session_state-free (run during plan verification)"
  - "Decision §8 — Caption position: FIRST inside `with st.chat_message('assistant'):` context manager, BEFORE `st.markdown(content)`. Verified by python regex window-check: in both render sites, the helper-call substring index is less than the `st.markdown(` substring index"
  - "Decision §9 — Dual guard. History loop guards on `role == 'assistant' AND message.get('provider')` (BOTH conditions required — user messages permanently excluded; early-return errors silently skipped). On-submit live render guards on `response.get('provider')` alone (the `with st.chat_message('assistant'):` block establishes role context structurally — no `role` field on `response`)"
  - "Decision §10/§11 — Two new keys appended to the dict end (trailing comma added to `chart_feedback` for Black-style). `.get(...)` access (vs subscript) preserves SC #3 contract: if process_query returned an early-error dict without provider/model, the append still succeeds with `None` values; the caption guard then skips render"
  - "Decision §14 / Option B — EXTEND the Plan-05-02 single module-level import line: `from src.llm import get_llm, load_settings, missing_vars` (alphabetized). NO inline `from src.llm import get_llm` inside any function body. Verified by grep: `grep -cE '^from src\\.llm import' app.py` = 1 and `grep -nE '    from src\\.llm import get_llm' app.py` = empty"
  - "Decision §16 — Wave 3 placement justified: Plan 05-03 hard-depends on both Plan 05-01's `provider_name` abstract property AND Plan 05-02's `_PROVIDER_LABELS` dict + the `from src.llm import ...` line that's being extended. Three-wave ordering (Wave 1 = Plan 01, Wave 2 = Plans 02+04, Wave 3 = Plan 03, Wave 4 = Plan 05) cleanly serializes the file-shared edits to app.py between 02 and 03"

patterns-established:
  - "Write-time provenance capture pattern (reusable for any per-message metadata): read the producing-side identifier INSIDE the function that builds the response, persist into the message dict, render from the stored dict at history-render time. Render code MUST NOT recompute from current session_state — that would silently mutate historical messages on session-state change"
  - "Explicit-args render helper with docstring-locked invariant: when a regression vector is 'someone simplifies the helper to read session_state', encode the warning in the docstring AND add an AST-based test (Plan 05-05 territory) that asserts the helper body contains no `session_state` reference"
  - "Defensive `getattr` with double-fallback for cross-adapter consistency: when reading a 'should always be there' attribute on an instance that came from a factory + ABC, use `getattr(client, 'provider_name', sensible_fallback)` not direct attribute access. Plan 05-01's abstract property guarantees the attr exists today, but a future adapter forgetting to override + the abstract enforcement skipping (e.g. mock subclass in tests) would crash render — defensive fallback degrades to 'unknown' (or session_state value) gracefully"
  - "Dual-guard exclusion at render-time: when a render site MUST exclude certain message variants (user messages here; future: system messages, info-only messages), use a combined `role == 'X' AND message.get('required_key')` guard. The role check is the structural exclusion (user vs assistant); the dict-key check is the data-driven exclusion (error paths without metadata). Each guard alone is insufficient — both must hold"
  - "Append-with-`.get(...)`-fallback for new optional keys: when a future-extended message dict gains new keys, write them via `response.get('new_key')` (not `response['new_key']`) so early-error paths that don't set those keys don't crash the append. The render guard handles `None` values gracefully"

# Metrics
duration: ~4 min
completed: 2026-05-22
---

# Phase 5 Plan 03: Per-Message Provenance Caption Summary

**Per-assistant-message provenance caption (`via **<Provider>** · \`<model>\``) captured at write time from `client.provider_name` + `client._model`, persisted into `st.session_state.messages`, and rendered above content in both history loop and on-submit block — historical messages survive a mid-session provider switch because data is captured-then-stored, not recomputed-from-session_state**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-22T02:01:55Z
- **Completed:** 2026-05-22T02:06:09Z
- **Tasks:** 2
- **Files modified:** 1 (app.py only)

## Accomplishments

- Extended single module-level import line: `from src.llm import get_llm, load_settings, missing_vars` (Option B from decision §14 — no inline imports anywhere in app.py)
- Added `_render_provenance_caption(provider, model)` at app.py module scope (lines 373–395) with explicit positional args + docstring-locked invariant (`MUST NOT read st.session_state`). Helper uses `_PROVIDER_LABELS.get(provider, provider)` for human-name lookup (degrades gracefully on unknown key) and `st.caption(f"via **{human_name}** · \`{model}\`")` (or drops the model half when falsy)
- Capture block in `process_query` (lines 897–906): `_client = get_llm()` → `_provider = getattr(_client, "provider_name", st.session_state.get("llm_provider", "unknown"))` → `_model = getattr(_client, "_model", "unknown")` — happens AFTER `route_query` succeeds and BEFORE the final return; defensive `getattr` keeps the path crash-free if a future adapter forgets to override `provider_name` or set `_model`
- Happy-path return dict gains two new keys: `"provider": _provider, "model": _model` (early-return error paths intentionally unchanged — caption guard handles their absence)
- `render_chat_history` (lines 728–735): caption rendered FIRST inside `with st.chat_message(message["role"]):` context, BEFORE `st.markdown(content)`. Dual-guarded by `role == "assistant" AND message.get("provider")`
- On-submit `with st.chat_message("assistant"):` block (lines 1016–1024): caption rendered AFTER spinner finishes and BEFORE `st.markdown(response["content"])`, guarded by `response.get("provider")`
- `st.session_state.messages.append({...})` (lines 1046–1048): two new keys `"provider": response.get("provider")` + `"model": response.get("model")` (trailing comma added to `chart_feedback` for Black-style cleanliness)
- Full 69-test suite remains GREEN — zero regression at adapter, factory, or render boundary

## Task Commits

Each task was committed atomically:

1. **Task 3.1: Extend src.llm import + add _render_provenance_caption helper + capture provider/model in process_query** — `8c4a12d` (feat)
2. **Task 3.2: Wire caption into render_chat_history + on-submit assistant render + persist provider/model in messages dict** — `a5e3480` (feat)

**Plan metadata:** [pending — committed after this summary lands]

## Files Created/Modified

### Only file touched in this plan

- `app.py` (+63 lines net, single file):
  - **Line 20:** import line extended — `from src.llm import get_llm, load_settings, missing_vars`
  - **Lines 373–395:** new `_render_provenance_caption(provider, model)` helper at module scope, inserted IMMEDIATELY after `_PROVIDER_KEYS` (line 370). 23 lines including docstring. Two-branch body: with model → `via **<Name>** · `<model>`` ; without → `via **<Name>**`
  - **Lines 728–735:** caption render block at top of `with st.chat_message(message["role"]):` in `render_chat_history` — 7 lines including Phase-5 comment
  - **Lines 897–906:** capture block at end of `process_query` happy path — 9 lines including Phase-5 comment; before the final return statement
  - **Lines 915–917:** return dict extended with two new keys (`"provider": _provider`, `"model": _model`)
  - **Lines 1016–1024:** caption render block in on-submit `with st.chat_message("assistant"):` — 8 lines including Phase-5 comment; between spinner-exit and `st.markdown(response["content"])`
  - **Lines 1046–1048:** `st.session_state.messages.append` dict extended with two new keys (`"provider": response.get("provider")`, `"model": response.get("model")`); trailing comma added to `chart_feedback` for Black-style

### Untouched (verified via git diff)

- `src/llm/__init__.py`, `src/llm/config.py`, `src/llm/base.py`, `src/llm/azure_openai.py`, `src/llm/anthropic_mgti.py` — all UNCHANGED (Plan 05-01 deliverables consumed as-is)
- `tests/` — all UNCHANGED (Plan 05-05 acceptance gate is the future test landing)
- `README.md`, `USER_GUIDE.md`, `.env.example` — all UNCHANGED (Plan 05-04 docs territory; will reference the caption format in its own work)
- All other functions in `app.py` (`render_sidebar` LLM PROVIDER block from Plan 05-02, `init_session_state`, `display_results`, `render_main_content` outside the on-submit lines, `main()`) — all UNCHANGED

## Exact UI strings now present in app.py (Plan 05-04 docs may quote these)

| Element | String |
|---------|--------|
| Caption template (with model) | `f"via **{human_name}** · \`{model}\`"` |
| Caption template (no model) | `f"via **{human_name}**"` |
| Example: Azure caption | `via **Azure OpenAI** · `gpt-4o`` |
| Example: Anthropic caption | `via **Anthropic Claude (MGTI)** · `eu.anthropic.claude-sonnet-4-5-20250929-v1:0`` |

The interpunct `·` is U+00B7 (MIDDLE DOT). Provider human-name comes from `_PROVIDER_LABELS.get(provider, provider)` — falls back to the raw provider key on lookup miss.

## Decisions Made

All locked decisions §1–§16 from the plan executed verbatim. Most load-bearing:

- **Decision §1 — Capture location** is after `route_query` success and before the final return. This means the captured provider/model reflects the adapter that actually produced this specific response. If a future refactor adds retry-with-fallback logic, the captured value will track whichever provider's response landed in the dict — exactly what the UI needs to display.
- **Decision §3 — Defensive `getattr` with double-fallback.** `getattr(_client, "provider_name", st.session_state.get("llm_provider", "unknown"))` ensures three layers of fallback: the adapter's abstract property (today), the sidebar-written session-state value (rare miss case), and the literal string `'unknown'` (last resort, never crashes). Plan 05-01's abstract enforcement guarantees `provider_name` exists on every concrete adapter, but defensive coding is cheap and futureproofs against test mocks or unforeseen subclasses.
- **Decision §5 — Reuse `_PROVIDER_LABELS` from Plan 05-02.** Single source of truth at module scope; no duplicate dict; future additions to the dict (a hypothetical third provider) immediately propagate to both the sidebar selectbox option list AND the per-message caption.
- **Decision §7 — Explicit-args helper with docstring-locked invariant.** The helper signature is `_render_provenance_caption(provider: str, model: str | None)`. Docstring contains the phrase `"CRITICAL INVARIANT: This helper MUST NOT read st.session_state"`. AST-based verification at plan-execution time confirmed the helper body is `session_state`-free. Plan 05-05's acceptance gate will add a programmatic regression test for this invariant.
- **Decision §9 — Dual-guard at the history-render site.** `role == "assistant" AND message.get("provider")`. The role check excludes user messages permanently (they don't carry provenance). The dict-key check skips assistant messages from early-return error paths (NO DATA LOADED, NO EMBEDDINGS, route_query error) that intentionally don't carry provenance. Each guard alone is insufficient; both together produce the correct behavior.
- **Decision §14 / Option B — Extend the Plan-05-02 import line, not a second import.** Locked the single canonical `from src.llm import get_llm, load_settings, missing_vars` line at app.py:20. Verified by grep: exactly one `from src.llm import` line in app.py; zero inline `from src.llm import get_llm` inside any function body. This matches app.py's prevailing import style and keeps Plan 05-05's static-analysis-based tests simple.

## Deviations from Plan

**None — plan executed exactly as written.**

- Both tasks landed on the first attempt with no debug iteration
- The two atomic commits (`8c4a12d`, `a5e3480`) correspond exactly to Task 3.1 and Task 3.2 as specified
- Full 69-test suite remained green after each task (7.76s after Task 3.1; 7.83s after Task 3.2 — well within the established Phase 1–4 baseline)
- All plan-level verification checks passed: single module-level import line; helper defined once + called twice (3 total occurrences); `_provider`/`_model` capture + return-dict keys present; append dict has both new keys; AST check confirms helper body session_state-free; ordering check (cap_idx < md_idx) holds in both render sites

## Issues Encountered

**One minor observation (not a plan deviation):**

- The plan's verify regex `grep -cE 'st\.chat_message\("assistant"\)' app.py` expected `2` matches, but the live grep returns `1`. This is because `render_chat_history` uses the dynamic form `st.chat_message(message["role"])` (variable, not the literal string `"assistant"`) — a pre-existing app.py pattern dating from before Phase 5. The literal `st.chat_message("assistant")` exists only at the on-submit render site (line 1012). This is not a regression introduced by Plan 05-03; both render sites are correctly updated with the caption block. To verify the dual-render expectation programmatically, we used the python regex window-check (counting `cap_idx < md_idx` ordering at BOTH `st.chat_message("assistant"):` and `st.chat_message(message["role"]):` sites), which confirmed correct ordering at both sites. Plan 05-05's acceptance gate may want to use the AST-walker approach (find `ast.With` nodes whose context manager is `st.chat_message(...)`) rather than literal-string grep, since the assistant-render site at line 727 uses the dynamic role argument by design.

## User Setup Required

None — Plan 05-03 is pure UI metadata capture + render inside `app.py`. No new env vars, no new dependencies, no documentation updates (Plan 05-04 docs territory).

## Next Phase Readiness

### Unblocked

- **Plan 05-05 (acceptance gate):** Phase 5's most important SC #4 test ("history survives provider switch") is now fully exercisable. The test should patch `get_llm()` to return a controllable mock with `provider_name = "azure_openai"` + `_model = "gpt-4o"`, run a query so `process_query` appends a message with that provenance, then re-patch `get_llm()` to return `provider_name = "anthropic_mgti"` + `_model = "eu.anthropic.claude-..."`, call `render_chat_history()`, and assert the FIRST message's caption still reads `via **Azure OpenAI** · `gpt-4o``. The dual-guard regression test should call `_render_provenance_caption` directly with no current-session-state setup; if anyone refactors the helper to read session_state, the test crashes with `KeyError` or returns the wrong human-name. AST-based test for the helper-body-session_state-free invariant should also land (Plan 05-05 territory).

- **Plan 05-04 (documentation):** The README + USER_GUIDE updates can now reference the exact caption format strings: `via **<Provider>** · `<model>`` (with interpunct U+00B7). USER_GUIDE's `## LLM Provider Selection` section's "Caption Meaning" subheading should quote both example formats from the table above.

### Verified untouched (no scope creep)

- `src/llm/__init__.py`, `src/llm/config.py`, `src/llm/base.py`, `src/llm/azure_openai.py`, `src/llm/anthropic_mgti.py` — all UNCHANGED
- `tests/` (4 phase test files) — all UNCHANGED; full 69-test suite still green
- `README.md`, `USER_GUIDE.md`, `.env.example` — all UNCHANGED (Plan 05-04 territory)
- All other functions in `app.py` outside the 6 narrow edit windows (single import line + helper insertion + history-render guard + capture block + return-dict extension + on-submit caption block + append-dict extension) — all UNCHANGED

### Concerns / Blockers

- The operator-run smoke gate against stage gateway (`python scripts/smoke_llm.py --provider both --verbose`) remains pending. Plan 05-03 does NOT depend on it — this plan only adds UI metadata capture + render; the underlying adapters are unchanged and were already exercised by the 69-test acceptance suite. Plan 05-04 (documentation) now references the smoke ritual as the final acceptance step before any production deploy (per Plan 05-04 SUMMARY).
- Manual UI verification (operator running Streamlit and visually inspecting captions after a provider switch) is the responsibility of the Phase 5 verification PR review — Plan 05-05 (acceptance gate) covers it programmatically via `streamlit` mocks, but a visual smoke test against the real Streamlit render is still recommended.

---
*Phase: 05-sidebar-ui-toggle-documentation*
*Completed: 2026-05-22*
