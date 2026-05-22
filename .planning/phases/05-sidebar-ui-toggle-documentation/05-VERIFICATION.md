---
phase: 05-sidebar-ui-toggle-documentation
verified: 2026-05-22T02:27:52Z
status: human_needed
score: 5/5 must-haves automated-verified (live smoke run deferred to operator per SMK-05)
human_verification:
  - test: Operator re-run of smoke_llm.py after Phase 5 .env / UI work
    expected: >-
      python scripts/smoke_llm.py --provider both --verbose exits 0; both Azure
      and Anthropic providers PASS on service-info, complete, and
      classify_with_tool checks against staging gateway; transcript pasted into
      the Phase 5 verification PR
    why_human: >-
      Phase 5 USER_GUIDE step 3 of First-Time Anthropic Setup Checklist
      directs operators to run scripts/smoke_llm.py before opening the UI;
      CONTEXT.md Smoke-script-credential section designates this OPERATOR-RUN ONLY
      (re-affirmed from Phase 4 RESEARCH Pitfall 7). Live staging credentials
      are not available to CI or the dev environment. SMK-05 preauthorizes
      deferral for PR review; the artifact and structural checks all pass.
---

# Phase 5: Sidebar UI Toggle + Documentation - Verification Report

**Phase Goal:** Expose provider selection in the Streamlit sidebar (Azure OpenAI default),
surface model + provider on every assistant message, warn on missing credentials, and document
the feature in README and USER_GUIDE.

**Verified:** 2026-05-22T02:27:52Z
**Status:** human_needed
**Re-verification:** No - initial verification

---

## Goal Achievement

### Observable Truths


| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Sidebar selectbox labeled LLM provider with locked options renders, persists selection in session_state, displays active model beneath | VERIFIED | app.py:606-611 selectbox label LLM provider with options list(_PROVIDER_OPTIONS.keys()); app.py:365-368 _PROVIDER_OPTIONS dict has exact keys Azure OpenAI / Anthropic Claude (MGTI); app.py:592-600 session_state init from LLM_PROVIDER_DEFAULT with clamp; app.py:617-624 load_settings() + st.caption MODEL read-only model display |
| 2 | get_llm() factory uses @st.cache_resource keyed on (provider, base_url, model, api_key_fingerprint); provider switch re-resolves on next query | VERIFIED | src/llm/__init__.py:133-165 _get_llm_cached(provider, base_url, model, api_key_fingerprint) decorated with @_cache_resource; src/llm/__init__.py:95-111 _fingerprint() uses SHA-256[:8] never raw key; src/llm/__init__.py:194-212 get_llm() computes 4-tuple BEFORE cache call; tests test_sc2_get_llm_cached_called_with_full_tuple + test_sc2_switching_provider_calls_with_different_tuple PASS |
| 3 | Missing-env warning renders in sidebar via st.warning and disables st.chat_input until resolved or switched | VERIFIED | app.py:629 missing_vars(provider) call; app.py:633-637 st.warning with bold provider name + backtick-formatted missing var names; app.py:638 sets st.session_state[_llm_provider_blocked]=True; app.py:999-1001 st.chat_input(_placeholder, disabled=_blocked) reads the flag; placeholder swaps to QUERY DISABLED - see sidebar warning |
| 4 | Every assistant message in st.session_state.messages carries provider+model keys; render reads from stored dict not session_state so history survives provider switches | VERIFIED | app.py:903-907 process_query reads getattr(_client, provider_name, ...) and getattr(_client, _model, ...); app.py:916-917 return dict carries provider/model; app.py:1047-1048 messages.append persists them; app.py:732-735 render_chat_history reads message[provider]/message.get(model) (not session_state); app.py:1021-1024 fresh-response caption uses response dict; tests test_sc4_render_history_caption_reads_from_stored_dict_not_session_state + test_sc4_render_provenance_caption_does_not_read_session_state PASS |
| 5 | README.md and USER_GUIDE.md document provider selection, MGTI-only constraint, smoke_llm.py usage, and warning resolution | VERIFIED (DOCS) / HUMAN-NEEDED (live smoke re-run) | README.md:88-111 LLM Provider Selection section + Smoke Test (operator-run) section; README.md:86 MGTI + Hubble reference; USER_GUIDE.md:297-369 full LLM Provider Selection section covering Overview / MGTI constraint / How to Switch / Per-Message Caption / Warning resolution table / First-Time Setup / Mid-Session Switching; tests test_sc5_readme_contains_required_topics + test_sc5_user_guide_contains_locked_ui_strings_and_required_topics PASS; live smoke re-run deferred per SMK-05 |

**Score:** 5/5 truths automated-verified; SC #5 live smoke re-run is operator-deferred (preauthorized)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app.py | _PROVIDER_OPTIONS dict + _render_provenance_caption helper + sidebar LLM PROVIDER block + chat_input disabled wiring + process_query provider/model capture + history rendering with caption | VERIFIED | 1073 lines; _PROVIDER_OPTIONS at line 365-368 (locked keys/values); _PROVIDER_LABELS reverse map at line 369; _render_provenance_caption helper at lines 373-395 (with explicit invariant: must NOT read session_state); LLM PROVIDER sidebar section at lines 586-642; missing_vars import at line 20; chat_input disabled wiring at lines 999-1001; process_query provider/model capture at lines 897-918; render_chat_history caption at lines 732-735; fresh-response caption at lines 1021-1024; messages.append with provider/model at lines 1047-1048; no stubs |
| src/llm/__init__.py | Factory + @st.cache_resource on _get_llm_cached + 4-tuple cache key + _fingerprint helper + no-Streamlit fallback | VERIFIED | 240 lines; _cache_resource try/except fallback at lines 72-85; _fingerprint at lines 95-111 (SHA-256[:8]); _resolve_provider at lines 114-130 (kwarg > session > env > default); _get_llm_cached at lines 133-165 decorated with @_cache_resource; get_llm() at lines 168-212 computes 4-tuple BEFORE cache call; LLMConfigError on unknown provider; no stubs |
| src/llm/config.py | missing_vars() non-raising helper + LLMSettings dataclass with provider config | VERIFIED | 162 lines; missing_vars at lines 136-161 (returns list, never raises, unknown provider returns []); _REQUIRED_VARS dict at lines 53-63; LLMSettings dataclass at lines 23-48 with api_key fields excluded from repr (OBS-03); validate_config raises with FULL missing list at lines 112-133; no stubs |
| src/llm/base.py | LLMClient ABC with provider_name property | VERIFIED | provider_name abstract property at lines 86-99 with docstring naming Phase 5 UI caption contract; canonical strings match _REGISTRY keys |
| src/llm/azure_openai.py + anthropic_mgti.py | provider_name property returns canonical key | VERIFIED | azure_openai.py:101-102 returns azure_openai; anthropic_mgti.py:193-194 returns anthropic_mgti; test_provider_name_concrete_returns_canonical_strings PASSES |
| README.md | LLM Provider Selection section + smoke_llm.py operator-run docs + MGTI/Hubble references + USER_GUIDE.md cross-link | VERIFIED | 117 lines; line 22 mentions selectable per session; lines 78-86 env-var table with all Anthropic vars + MGTI/Hubble line; lines 88-95 LLM Provider Selection section with USER_GUIDE cross-link; lines 96-111 Smoke Test (operator-run) with exit codes; line 116 data-privacy update |
| USER_GUIDE.md | Full LLM Provider Selection section covering switch UX, caption meaning, warning resolution, first-time setup, mid-session behavior | VERIFIED | 455 lines; line 19 TOC entry; lines 297-369 LLM Provider Selection with 6 subsections (Overview / MGTI Constraint / How to Switch / Caption Meaning / Warning Resolution table / First-Time Setup / Mid-Session); line 454 v2.1 changelog |
| tests/test_phase5_ui.py | Acceptance gate covering SC 1-5 + provider_name + helpers | VERIFIED | 22 tests all passing: SC1 (4), SC2 (4), SC3 (4), SC4 (4), provider_name (2), SC5 docs (2), helpers (2) |
| scripts/smoke_llm.py | Operator-run live-credential gate (referenced by USER_GUIDE first-time setup checklist) | VERIFIED (ARTIFACT) | 470 lines; py_compile succeeds; live execution operator-run only per SMK-05 |


---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Sidebar selectbox value | session_state[llm_provider] | st.session_state[llm_provider] = _PROVIDER_OPTIONS[selected_label] at app.py:612 | WIRED | Selection persisted on every rerun; index resolved from current session_state at line 609 |
| session_state[llm_provider] | get_llm() resolution | _resolve_provider reads st.session_state.get(llm_provider) at src/llm/__init__.py:123-129 | WIRED | try/except guard keeps non-Streamlit paths safe; explicit kwarg still takes priority |
| get_llm() | @_cache_resource cache | _get_llm_cached(resolved, base_url, model, fingerprint) at src/llm/__init__.py:212 | WIRED | 4-tuple key includes provider+base_url+model+api_key_fingerprint per ROADMAP SC #2; switching provider re-resolves on next get_llm() call |
| Sidebar missing_vars check | chat_input disabled state | st.session_state[_llm_provider_blocked] set at app.py:638/640; read at app.py:999-1001 | WIRED | render_sidebar() runs BEFORE render_main_content() per main() at app.py:1067-1069 (load-bearing order documented); placeholder text swaps when blocked |
| process_query | provider/model capture | _client = get_llm() at app.py:903; getattr fallbacks at lines 904-907 | WIRED | Reuses cached adapter (no extra HTTP); defensive getattr keeps the path crash-free if a future adapter omits provider_name/_model |
| Messages list | history caption rendering | message[provider] / message.get(model) at app.py:732-735 - NOT session_state | WIRED | Explicit invariant locked in _render_provenance_caption docstring at app.py:386-389; test_sc4_render_provenance_caption_does_not_read_session_state enforces |
| README LLM Provider Selection section | USER_GUIDE.md anchor | Markdown link to USER_GUIDE.md#llm-provider-selection at README.md:94 | WIRED | Anchor matches USER_GUIDE.md:19 TOC entry and lines 297 heading |

---

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| UI-01 Sidebar selectbox with locked label and options | SATISFIED | app.py:607-611 selectbox label LLM provider; app.py:365-368 _PROVIDER_OPTIONS dict matches exact required strings |
| UI-02 Selection persists in session_state initialized from LLM_PROVIDER_DEFAULT | SATISFIED | app.py:592-600 session_state[llm_provider] init from env with clamp to azure_openai on typo |
| UI-03 Active model name displayed read-only beneath via st.caption | SATISFIED | app.py:617-624 load_settings() + provider-specific model extraction + st.caption MODEL |
| UI-04 Cache re-resolution on switch (4-tuple key) | SATISFIED | src/llm/__init__.py:133-212 4-tuple (provider, base_url, model, api_key_fingerprint) cache key; fingerprint via SHA-256[:8] never raw key |
| UI-05 Missing-env warning rendered in sidebar | SATISFIED | app.py:629-637 missing_vars + st.warning with named missing vars + provider name |
| UI-06 Query submission disabled until warning resolves | SATISFIED | app.py:638/640 _llm_provider_blocked flag; app.py:999-1001 chat_input(disabled=_blocked) + placeholder swap |
| UI-07 Per-message provenance caption from stored dict | SATISFIED | app.py:732-735 history; app.py:1021-1024 fresh; both read from explicit args, never session_state - invariant locked by docstring + test |
| DOC-01 README documents LLM provider selection | SATISFIED | README.md:88-95 LLM Provider Selection section with cross-link to USER_GUIDE |
| DOC-02 USER_GUIDE walks through switching, captions, warnings | SATISFIED | USER_GUIDE.md:297-369 six-subsection walkthrough including switching UX, caption format examples, warning resolution table |
| DOC-03 MGTI-only constraint documented | SATISFIED | README.md:86 + USER_GUIDE.md:308-312 with explicit DOES NOT connect to api.anthropic.com assertion + Hubble onboarding link |
| DOC-04 smoke_llm.py usage and warning resolution documented | SATISFIED | README.md:96-111 Smoke Test (operator-run) with all three invocations + exit codes; USER_GUIDE.md:333-348 warning resolution table; USER_GUIDE.md:356-360 first-time setup checklist step 3 |


---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No stubs, TODOs, FIXMEs, empty handlers, or placeholder returns in any Phase 5 artifact |

Grep across Phase 5 modified files (app.py, src/llm/__init__.py, src/llm/config.py, src/llm/base.py,
src/llm/azure_openai.py, src/llm/anthropic_mgti.py, tests/test_phase5_ui.py, README.md, USER_GUIDE.md)
shows zero matches for stub patterns. The only placeholder hits in app.py are legitimate uses of
the Streamlit st.text_input(placeholder=...) and st.chat_input(placeholder) API parameters
(lines 467, 1000, 1001) - NOT placeholder content stubs.

---

### Human Verification Required

#### 1. Operator Re-Run of Smoke Script After Phase 5 .env / UI Work

**Test:** From a dev environment with valid .env containing ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY,
ANTHROPIC_MODEL, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_KEY set to staging values, run:

    python scripts/smoke_llm.py --provider both --verbose

**Expected:**

    [PASS] anthropic_mgti   / service-info         - 200 in <N>ms  shape={...}
    [PASS] anthropic_mgti   / complete              - 200 in <N>ms  model=eu.anthropic.claude-*  shape={...}
    [PASS] anthropic_mgti   / classify_with_tool    - 200 in <N>ms  intent=structured|semantic|hybrid  shape={...}
    [PASS] azure_openai     / complete              - 200 in <N>ms  shape={...}
    [PASS] azure_openai     / classify_with_tool    - 200 in <N>ms  intent=structured|semantic|hybrid  shape={...}
    Summary: 5 passed, 0 failed, 0 skipped - exit 0

Exit code: 0

**Why human:** Live staging credentials are not available in CI. The smoke script is designated
OPERATOR-RUN ONLY in scripts/smoke_llm.py and 04-CONTEXT.md / 05-CONTEXT.md Smoke-script-credential
section. Phase 5 USER_GUIDE.md first-time Anthropic setup checklist (USER_GUIDE.md:356-360)
directs operators to re-run this script before opening the UI with new credentials. SMK-05
preauthorizes deferral of the live execution to PR review.

**Action required:** Paste the full terminal transcript into the Phase 5 verification PR before
merging.

---

### Gaps Summary

No gaps found. All five automated success criteria pass structural, substantive, and wiring
verification against the actual codebase:

- SC #1 (selectbox): exact locked label and option strings present in app.py:606-611; session_state
  persists with defensive clamp at lines 592-600; read-only model caption at lines 617-624.
- SC #2 (cache re-resolution): @_cache_resource on _get_llm_cached with 4-tuple key in
  src/llm/__init__.py; _fingerprint() uses SHA-256[:8] never raw key; switching provider
  produces a different cache-key tuple (verified by test_sc2_switching_provider_calls_with_different_tuple).
- SC #3 (missing-env warning + disabled submission): missing_vars() at src/llm/config.py:136-161;
  sidebar wiring at app.py:629-640 sets _llm_provider_blocked flag; chat_input reads it at
  app.py:999-1001; main() order is load-bearing and documented.
- SC #4 (per-message provenance): process_query captures provider/model via cached adapter
  (no extra HTTP); messages.append persists them; render reads from stored dict NOT session_state
  (invariant locked by _render_provenance_caption docstring at app.py:386-389 and enforced by
  test_sc4_render_provenance_caption_does_not_read_session_state).
- SC #5 (docs): README.md LLM Provider Selection section + Smoke Test (operator-run) section;
  USER_GUIDE.md LLM Provider Selection section with 6 subsections (Overview / MGTI / How to Switch /
  Caption Meaning / Warning Resolution / First-Time Setup / Mid-Session); locked UI strings
  present; MGTI constraint explicit; smoke_llm.py invocations documented with exit codes; warning
  resolution table maps every required env var to a fix.

The single human-needed item (live smoke run) is an expected operator-run gate per phase design.

---

### Test Suite Evidence

    pytest tests/ -q
    91 passed, 1 warning in 8.02s

    pytest tests/test_phase5_ui.py -v
    22 passed, 1 warning in 8.03s

Phase 5 tests by SC mapping:

- SC #1 (selectbox + locked strings + session_state): test_sc1_* - 4 tests
- SC #2 (cache 4-tuple + fingerprint + switching): test_sc2_* - 4 tests
- SC #3 (missing_vars + warning + chat_input disabled): test_sc3_* - 4 tests
- SC #4 (provenance caption reads stored dict not session_state): test_sc4_* - 4 tests
- provider_name property contract: test_provider_name_* - 2 tests
- SC #5 (README + USER_GUIDE topics + locked UI strings): test_sc5_* - 2 tests
- Helpers (missing_vars non-raising; _PROVIDER_OPTIONS == _REGISTRY): test_helper_* - 2 tests

Combined suite (Phases 1-5): 91 passed.

---

_Verified: 2026-05-22T02:27:52Z_
_Verifier: Claude (gsd-verifier)_
