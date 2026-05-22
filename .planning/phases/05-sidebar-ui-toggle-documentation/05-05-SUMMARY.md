---
phase: 05-sidebar-ui-toggle-documentation
plan: 05
subsystem: tests
tags: [pytest, acceptance-gate, streamlit-mocks, ast, docs-content-check, phase-5-signoff]

# Dependency graph
requires:
  - phase: 05-sidebar-ui-toggle-documentation/01
    provides: "_fingerprint, _get_llm_cached cache (4-arg tuple), missing_vars helper, provider_name abstract property"
  - phase: 05-sidebar-ui-toggle-documentation/02
    provides: "_PROVIDER_OPTIONS dict, render_sidebar LLM PROVIDER block (selectbox + warning), _llm_provider_blocked decoupling, chat_input disable wiring"
  - phase: 05-sidebar-ui-toggle-documentation/03
    provides: "_render_provenance_caption(provider, model) module-scope helper, process_query write-time capture, render_chat_history caption render, session_state.messages provider/model persistence"
  - phase: 05-sidebar-ui-toggle-documentation/04
    provides: "README.md + USER_GUIDE.md updates (7 locked UI strings, 4 required topics, MGTI/Hubble pointer, smoke_llm.py reference, warning-resolution table)"
provides:
  - "tests/test_phase5_ui.py — self-contained Phase 5 acceptance gate (22 tests, all 5 ROADMAP SCs proven + 5 RESEARCH.md pitfall regression guards)"
  - "Combined Phase 1+2+3+4+5 result: 91 passed in 8.13s, zero live HTTP/LLM/Streamlit"
  - "Phase 5 sign-off readiness: all 5 ROADMAP success criteria proven by named test functions; manual operator-run smoke gate remains the only live surface"
affects: []  # Final plan of Phase 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Streamlit mock surface helper (_build_streamlit_mock_surface) as single source of truth for ALL render_* tests — context managers (sidebar, expander, chat_message, spinner) pre-built with __enter__/__exit__ BEFORE patch.multiple is entered"
    - "Columns side_effect closure that returns the right number of context-manager mocks per call (handles st.columns(2), st.columns(3), st.columns([3,1]))"
    - "AST-based invariant check (test_sc4_render_provenance_caption_does_not_read_session_state): parse helper source, drop docstring node, assert executable body free of session_state references — Pitfall 11 lock with docstring-safe regex"
    - "Wraps-spy pattern for cache-key tuple assertions: patch.object(llm_pkg, '_get_llm_cached', wraps=real_cached) captures call args without breaking the real cache resolution"
    - "Docs-content grep test pattern (test_sc5_*): assert exact UI strings + required topics in README/USER_GUIDE — locks docs against drift (RESEARCH.md Pitfall 13)"

key-files:
  created:
    - "tests/test_phase5_ui.py (744 lines, 22 tests)"
    - ".planning/phases/05-sidebar-ui-toggle-documentation/05-05-SUMMARY.md (this file)"
  modified: []  # No production code touched

key-decisions:
  - "Test module is SELF-CONTAINED — no conftest.py, no pytest.ini, no new fixture files. Matches Phase 1/2/3/4 acceptance-gate pattern (decision §1 of plan)"
  - "_build_streamlit_mock_surface() defined at module top as helper; called by 12 render_*-exercising tests (DRY). Context managers (sidebar/expander/chat_message/spinner) built with working __enter__/__exit__ via inline _make_cm() factory — supersedes the earlier draft's broken `MagicMock().__enter__.return_value` pattern (Blocker 3 closed)"
  - "Columns mock uses side_effect with closure instead of fixed return_value — production code calls st.columns([3,1]) AND st.columns(2) AND st.columns(3) at different sites; a single 3-tuple return_value would either over-supply (silent ignore) or under-supply (unpack error). Closure inspects the spec arg and returns matching tuple"
  - "expander/chat_message/spinner moved from single-CM-return_value to side_effect-returning-fresh-CMs — render_chat_history loops over messages and calls st.chat_message(role) once per message; same CM reuse can break the second iteration's __exit__"
  - "Test cohort: 22 tests (one over target of ~21). SC #1: 4, SC #2: 4, SC #3: 4, SC #4: 4, Pitfall 8 / provider_name: 2, SC #5: 2, helper sanity: 2 = 22"
  - "SC #3 covers BOTH blocked AND unblocked chat_input branches (Warning 5 fix). The unblocked test asserts placeholder == 'ENTER QUERY...' exactly (Warning 7 fix locks default UI string against silent drift). Without the unblocked test, a regression that always sets disabled=True would still pass the blocked-only assertion"
  - "SC #4 helper-static-source invariant uses AST parsing + docstring-drop instead of raw substring grep. The helper's docstring intentionally mentions session_state (to document the invariant); naive `'session_state' not in src` would false-positive on that documentation. The AST walk parses the function, removes the docstring node, then unparses the executable body for the assertion — invariant is checked AT THE BODY LEVEL where it matters (Pitfall 11 lock — robust to docstring evolution)"
  - "SC #5 README test explicitly asserts 'MGTI' token presence (Warning 6 closed) — not just inferred via 'Hubble' alone. The MGTI constraint is the load-bearing piece of context; documenting Hubble without MGTI would leave a reader confused about whether plain api.anthropic.com works"
  - "Autouse _clear_streamlit_session_state fixture added beyond the prior-phase pattern — Streamlit session_state persists across pytest test invocations within the same process. The two SC1 tests that seed `llm_provider` and the SC3+SC4 tests that read it from history MUST not leak state into each other (Pitfall 12 hardening). try/except wrappers cover the no-Streamlit-context fallback"
  - "Tests seed `data_loaded=False`, `embeddings_ready=False`, `schema=None` in EVERY render_sidebar-exercising test — render_sidebar's EMBEDDINGS/CONFIG sections read these via attribute access (st.session_state.schema, etc.) which raises if unset. The autouse session-state-clear means each test starts from a blank session_state and must re-seed"
  - "Tests for render_main_content seed `data_loaded=True` + populated `schema` + `embeddings_ready=True` because render_main_content's status-bar block reads schema['row_count'] — must pass before the chat_input call"
  - "Zero live HTTP / LLM / Streamlit / network — verified by grep for `subprocess|requests\\.(get|post|put|delete)|urllib|httpx` returning empty"
  - "patches against `streamlit` module directly (patch.multiple('streamlit', **surface)) — the render functions take no DI args; this is the cleanest seam (decision §13 of plan, locked from RESEARCH.md)"

patterns-established:
  - "Acceptance-gate-per-phase pattern now consistent across all 5 phases: one self-contained pytest module per phase, autouse fixtures isolate per-test state (cache/env/session_state), inline mock builders not fixture files, exactly maps each ROADMAP SC to a named test function"
  - "Mock-surface DRY helper pattern: when N>3 tests need the same wide patch.multiple surface, extract a builder that returns a dict; tests override only the 1-2 primitives they assert on. Avoids the maintenance cost of N copies of a 20-line patch block"
  - "AST-based invariant testing: when a regression vector is 'maintainer accidentally adds a forbidden call (session_state read, raw key in cache key, etc.) to a function', parse the function source via ast/inspect, drop the docstring, then string-check the executable body. More robust than raw grep (docstring-safe) and cheaper than runtime instrumentation"

# Metrics
duration: ~6 min
completed: 2026-05-22
---

# Phase 5 Plan 05: Acceptance Gate Summary

**Phase 5 acceptance gate — 22 tests prove all 5 ROADMAP success criteria + 5 RESEARCH.md pitfall regression guards (1, 6, 8, 11, 13); combined Phase 1+2+3+4+5 suite is 91 passed in 8.13s with zero live HTTP/LLM/Streamlit. Phase 5 (the milestone) signs off here.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-22T02:13:32Z
- **Completed:** 2026-05-22T02:19:52Z
- **Tasks:** 1
- **Files modified:** 1 (tests/test_phase5_ui.py — new file)

## Accomplishments

- Wrote `tests/test_phase5_ui.py` (22 tests, 744 lines) as a self-contained pytest module — NO conftest.py, NO pytest.ini, NO new fixture files (matches Phase 1/2/3/4 gate pattern)
- Defined `_build_streamlit_mock_surface()` helper at module scope as the single source of truth for Streamlit mocks across 12 render_*-exercising tests (Blocker 3 closure — supersedes the earlier draft's broken inline patch.multiple pattern)
- Autouse fixtures (`_clear_factory_cache`, `_strip_llm_env`, `_clear_streamlit_session_state`) isolate per-test state for cache / env / session_state respectively — Phase 5 hardening over the prior-phase pattern
- All 5 Phase 5 ROADMAP success criteria proven by named test functions; all 5 RESEARCH.md pitfall regression guards (1, 6, 8, 11, 13) have dedicated tests
- Phase 5 acceptance gate alone: 22 passed in 8.05s
- Combined Phase 1+2+3+4+5 result: **91 passed in 8.13s**, zero live HTTP/LLM/Streamlit, zero subprocess/network calls

## Task Commits

Each task was committed atomically:

1. **Task 5.1: Write tests/test_phase5_ui.py — full acceptance gate (22 tests)** — `010bc78` (test)

**Plan metadata:** [pending — committed after this summary lands]

## Files Created/Modified

### Only file touched in this plan (production)

- `tests/test_phase5_ui.py` (NEW, 744 lines, 22 tests)

### Documentation artifact

- `.planning/phases/05-sidebar-ui-toggle-documentation/05-05-SUMMARY.md` (this file)

### Verified untouched (no scope creep)

- `src/` — all UNCHANGED (Phase 5 source-code work landed in 05-01, 05-02, 05-03)
- `app.py` — UNCHANGED (Phase 5 UI work landed in 05-02 and 05-03)
- `scripts/` — UNCHANGED (smoke script landed in Phase 4)
- `README.md`, `USER_GUIDE.md`, `.env.example`, `ROADMAP.md`, `REQUIREMENTS.md` — all UNCHANGED (docs landed in 05-04)
- Other test files (`test_llm_seam.py`, `test_phase2_parity.py`, `test_phase3_adapter.py`, `test_phase4_strict_tools.py`) — all UNCHANGED; prior 69-test suite remains green

## SC → Test Function Mapping

| ROADMAP SC | Proving Test Function(s) | Count |
|---|---|---|
| **SC #1** — sidebar selectbox `LLM provider` label + 2 options + session_state init from `LLM_PROVIDER_DEFAULT` + active-model caption | `test_sc1_provider_options_dict_has_exact_locked_keys_and_values`, `test_sc1_render_sidebar_calls_selectbox_with_locked_label_and_options`, `test_sc1_session_state_initialized_from_env_default`, `test_sc1_session_state_clamps_unknown_env_to_azure` | 4 |
| **SC #2** — switching providers mid-session re-resolves `@_cache_resource` because cache key includes (provider, base_url, model, api_key_fingerprint) | `test_sc2_fingerprint_one_way_and_does_not_leak_key`, `test_sc2_get_llm_cached_called_with_full_tuple`, `test_sc2_switching_provider_calls_with_different_tuple`, `test_sc2_module_level_cache_dict_is_deleted` | 4 |
| **SC #3** — missing-env provider → inline sidebar warning + query disabled | `test_sc3_missing_vars_returns_required_list_for_anthropic`, `test_sc3_sidebar_renders_warning_with_missing_vars_named`, `test_sc3_chat_input_disabled_when_blocked_flag_true`, `test_sc3_chat_input_enabled_when_not_blocked` | 4 |
| **SC #4** — every assistant message displays caption showing provider + model that produced it (history-survives-switch) | `test_sc4_render_history_caption_reads_from_stored_dict_not_session_state` (LOAD-BEARING), `test_sc4_render_history_no_caption_for_user_messages`, `test_sc4_render_history_no_caption_when_provider_key_missing`, `test_sc4_render_provenance_caption_does_not_read_session_state` | 4 |
| **SC #5** — README + USER_GUIDE explain provider selection, MGTI-only constraint, smoke_llm.py, warning resolution | `test_sc5_readme_contains_required_topics`, `test_sc5_user_guide_contains_locked_ui_strings_and_required_topics` | 2 |

**Pitfall 8 + abstract-property coverage (Plan 05-01 backstop):**
| Test | Locks |
|---|---|
| `test_provider_name_is_abstract_on_llmclient_abc` | provider_name is in LLMClient.__abstractmethods__ |
| `test_provider_name_concrete_returns_canonical_strings` | Both adapters return exact _REGISTRY keys |

**Helper sanity (additive):**
| Test | Locks |
|---|---|
| `test_helper_missing_vars_is_non_raising` | missing_vars returns list, never raises (Pitfall 7) |
| `test_helper_provider_options_keys_match_registry` | _PROVIDER_OPTIONS.values() ↔ _REGISTRY.keys() single source of truth |

## Pitfall → Regression-Guard Test Mapping

| Pitfall (from 05-RESEARCH.md) | Regression-Guard Test |
|---|---|
| **Pitfall 1** — fingerprint must not leak any substring of raw key; empty key returns `""` | `test_sc2_fingerprint_one_way_and_does_not_leak_key` |
| **Pitfall 6** — single cache layer only; Phase 1 module-level `_cache` dict must be deleted | `test_sc2_module_level_cache_dict_is_deleted` |
| **Pitfall 8** — provider_name as abstract property (not class attribute) — adapters must override deliberately | `test_provider_name_is_abstract_on_llmclient_abc`, `test_provider_name_concrete_returns_canonical_strings` |
| **Pitfall 11** — `_render_provenance_caption` MUST NOT read st.session_state; historical messages must keep their original provenance after switch | `test_sc4_render_history_caption_reads_from_stored_dict_not_session_state` (LOAD-BEARING), `test_sc4_render_history_no_caption_for_user_messages`, `test_sc4_render_history_no_caption_when_provider_key_missing`, `test_sc4_render_provenance_caption_does_not_read_session_state` (AST-based) |
| **Pitfall 13** — docs-drift guard: README/USER_GUIDE must quote the exact UI strings, naming each required topic | `test_sc5_readme_contains_required_topics`, `test_sc5_user_guide_contains_locked_ui_strings_and_required_topics` |

## Closure Confirmations (from plan must-haves)

- **Blocker 3 closure:** `_build_streamlit_mock_surface()` is the single source of truth for Streamlit mocks — called by 12 tests (grep `_build_streamlit_mock_surface\(\)` returns 12). The broken `MagicMock().__enter__.return_value` pattern is ABSENT from the file (grep returns 0 hits).
- **Warning 5 closure:** SC #3 covers BOTH chat_input branches — `test_sc3_chat_input_disabled_when_blocked_flag_true` AND `test_sc3_chat_input_enabled_when_not_blocked`. A regression that always sets `disabled=True` would now fail the unblocked test.
- **Warning 6 closure:** README test asserts `"MGTI" in text` explicitly (not just inferred from Hubble). The MGTI constraint is named in its own assertion.
- **Warning 7 closure:** SC #3 unblocked test asserts `placeholder == "ENTER QUERY..."` exactly — default UI string locked against silent drift.
- **Self-containment:** zero `conftest.py`, zero `pytest.ini`, zero fixture files added — matches Phase 1/2/3/4 gate pattern.
- **Zero live surface:** no subprocess, no requests, no urllib, no httpx — verified by grep.
- **Test count target hit:** 22 tests delivered (target ~21 ± tolerance). All SCs covered ≥2 tests; SCs 1-4 covered with 4 tests each.

## Decisions Made

All locked decisions §1–§19 from the plan executed verbatim. The most load-bearing implementation choices:

- **Decision §2 — _build_streamlit_mock_surface helper.** Refined during execution to add `_make_cm()` inline factory and `side_effect` closures for `columns`/`expander`/`chat_message`/`spinner`. The static `return_value` pattern in the plan draft proved insufficient because `render_chat_history` loops messages (each `with st.chat_message(role):` needs its own fresh CM) and `render_main_content` calls `st.columns(...)` at multiple sites with different specs. The helper is functionally identical to the plan's intent; the implementation adds the dynamic-shape support the production code needs.
- **Decision §11 (SC #4 helper-invariant test) — AST + docstring-drop refinement.** The plan's `"session_state" not in inspect.getsource(...)` would false-positive against the helper's docstring (which intentionally mentions `session_state` to document the invariant — Plan 05-03 decision §7). Refined to parse the source with `ast`, drop the docstring expression node, unparse the body, then string-check. Same invariant proved at the executable level; documentation is now free to evolve without breaking the test.
- **Decision §6 — session_state seeding.** Every test that calls `render_sidebar()`/`render_main_content()`/`render_chat_history()` seeds `upload_authenticated`, `data_loaded`, `embeddings_ready`, `schema` (and messages where relevant) before the call. The autouse `_clear_streamlit_session_state` fixture means each test starts blank and must re-seed; no leakage between tests.
- **Decision §15 — test count.** 22 tests delivered (one above the ~21 target). SC counts match plan exactly: SC1=4, SC2=4, SC3=4, SC4=4, Pitfall 8 / provider_name=2, SC5=2, helper sanity=2.

## Deviations from Plan

**Three minor refinements during execution — all documented above:**

1. **[Rule 3 — Blocker] _build_streamlit_mock_surface evolution.** The plan's draft pattern of returning single context-manager mocks (sidebar_cm/expander_cm/chat_message_cm/spinner_cm) didn't survive against `render_chat_history`'s per-message loop or `render_main_content`'s multi-call `st.columns(...)` pattern. Refined inline to use `_make_cm()` inline factory + `side_effect` closures. Helper still meets all the plan's stated invariants (single source of truth, pre-built context managers, DRY across tests). Closure semantics also correctly handle `st.columns(2)`, `st.columns([3,1])`, and `st.columns(3)` simultaneously.

2. **[Rule 1 — Bug fix] SC #4 invariant test docstring false-positive.** Plan's draft `"session_state" not in inspect.getsource(...)` would have ALWAYS failed against the current `_render_provenance_caption` (whose docstring deliberately documents the invariant — see Plan 05-03 decision §7). Refined to drop the docstring node before checking. The invariant is still strictly enforced at the body level — if a future maintainer adds a real `st.session_state.get(...)` call to the helper body, the AST check will catch it.

3. **[Rule 3 — Blocker] Session-state seeding for embed/data sections.** The render_sidebar EMBEDDINGS section (line 519+) reads `st.session_state.data_loaded`, `st.session_state.embeddings_ready`, `st.session_state.schema` via attribute access — raises if unset. Every render_sidebar test now seeds these (plus `upload_authenticated`) before the render call.

None of these are scope changes — they're plan-level patterns refined against the real production code surface. The 5 ROADMAP SCs are still proven by exactly the test functions the plan named, with the exact assertion semantics the plan specified.

## Issues Encountered

**One initial test-execution iteration with 5 failures:**

- 3 failures (SC1 init/clamp + SC3 sidebar warning) — root cause: missing `schema` / `data_loaded` / `embeddings_ready` seeds in `st.session_state`. Fixed by extending the seed lines in each affected test.
- 2 failures (SC3 chat_input blocked + unblocked) — root cause: `columns`/`expander`/`chat_message`/`spinner` mocks didn't behave as context managers because they were single MagicMock instances (not configured with `__enter__`/`__exit__`). Fixed by refactoring the helper to use `side_effect`-returning-fresh-CM-mocks pattern (deviation 1 above).

Second test run after both fixes: **22/22 passed in 8.05s**. Combined suite: **91/91 passed in 8.13s**.

## User Setup Required

None. The acceptance gate is a pure-mock pytest module; it adds zero live dependencies and zero env requirements. CI / local pytest run is sufficient.

## Phase 5 Sign-Off

**All 5 ROADMAP success criteria proven; sidebar selectbox + missing-creds warning + per-message provenance caption + factory-cache invariants + README/USER_GUIDE documentation shipped. The multi-provider Streamlit toggle is live; operators select Azure OpenAI (default) or Anthropic Claude (MGTI) per session; historical messages keep their original provenance after switches. Phase 5 closes the snow_query multi-provider LLM integration milestone.**

### Verifier Outcome

4 of 5 SCs are fully automated and green in CI / pytest. SC #5 (docs content) is also fully automated (grep-style assertions over README.md + USER_GUIDE.md).

The only remaining live surface is the operator-run smoke gate against the stage MGTI Apigee gateway (`python scripts/smoke_llm.py --provider both --verbose`) — this is the same operator-run gate that's been pending since Phase 4. Documented prominently in BOTH:
- README.md `### Smoke Test (operator-run)` subsection
- USER_GUIDE.md `### First-Time Anthropic Setup Checklist` step 3

### Pending Operator Action

Run `python scripts/smoke_llm.py --provider both --verbose` against the stage gateway with valid MGTI credentials; paste the transcript into the Phase 5 verification PR. This is the final acceptance ritual before any production deploy.

### Combined Phase 1+2+3+4+5 Suite

```
91 passed in 8.13s
```

- Phase 1 (seam): 6 tests
- Phase 2 (Azure parity): 12 tests
- Phase 3 (Anthropic adapter): 21 tests
- Phase 4 (strict-tools + smoke): 30 tests
- Phase 5 (UI + docs + factory-cache + per-message caption): 22 tests
- **Total: 91 tests, zero live HTTP, zero live LLM, zero live Streamlit, zero subprocess**

## Next Phase Readiness

### Unblocked

- **Phase 6 (if planned):** Phase 5 wave is complete; the multi-provider LLM substrate is stable. Future phases (e.g. retry/fallback logic, observability dashboards, additional providers) inherit a clean abstraction seam, single-cache layer, and per-message provenance contract.
- **Production deployment:** Phase 5 sign-off is contingent ONLY on the operator-run smoke gate. Once that returns Exit: 0 against stage, the multi-provider Streamlit toggle is shippable.

### Concerns / Blockers

- Operator-run smoke gate (`scripts/smoke_llm.py --provider both --verbose`) — pending operator availability of stage MGTI credentials. Same outstanding item from Phase 4 close-out; not introduced by Phase 5.
- Manual UI verification (operator running Streamlit and clicking through the sidebar) — covered programmatically by this acceptance gate, but a 30-second sanity click-through is the standard PR-review ritual and is the responsibility of the Phase 5 verification reviewer.

---
*Phase: 05-sidebar-ui-toggle-documentation*
*Plan: 05 (acceptance gate)*
*Phase 5 milestone: SIGNED OFF*
*Completed: 2026-05-22*
