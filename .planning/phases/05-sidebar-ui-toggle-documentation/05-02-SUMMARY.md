---
phase: 05-sidebar-ui-toggle-documentation
plan: 02
subsystem: ui
tags: [streamlit, sidebar, selectbox, chat_input, llm-toggle, brutalist]

# Dependency graph
requires:
  - phase: 05-sidebar-ui-toggle-documentation
    provides: "Plan 05-01 — missing_vars() non-raising helper, load_settings, provider_name abstract property, 4-arg cache key on _get_llm_cached"
provides:
  - "app.py module-level _PROVIDER_OPTIONS / _PROVIDER_LABELS / _PROVIDER_KEYS (single source of truth for UI labels ↔ _REGISTRY keys)"
  - "render_sidebar() '### LLM PROVIDER' block between EMBEDDINGS and CONFIG with selectbox + active-model caption + inline missing-creds warning"
  - "st.session_state['llm_provider'] initialization with .strip() + clamp-to-known defense against typos in LLM_PROVIDER_DEFAULT"
  - "st.session_state['_llm_provider_blocked'] decoupling flag (sidebar writes, main-content reads — no parameter ripple)"
  - "render_main_content() st.chat_input(disabled=_blocked) wiring + placeholder swap to 'QUERY DISABLED — see sidebar warning'"
  - "main() docstring locking the load-bearing render_sidebar()-before-render_main_content() order"
affects: [05-03-per-message-caption, 05-04-documentation, 05-05-acceptance-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Session-state init with clamp-to-known: getenv → .strip() → membership check → logger.warning + fallback"
    - "Sidebar-writes-flag / main-content-reads-flag decoupling via st.session_state (no function-signature changes; load-bearing order documented in main() docstring)"
    - "load_settings() in sidebar render (NOT get_llm()) — pure I/O for active-model display, no adapter construction or startup-log side effect"
    - "Module-level UI option dict + reverse-label dict + key-tuple alongside MODE_OPTIONS — co-located UI mapping constants"

key-files:
  created: []
  modified:
    - "app.py (single file, +86 lines net): module-level _PROVIDER_OPTIONS/_PROVIDER_LABELS/_PROVIDER_KEYS at line 364–370 (after MODE_OPTIONS); render_sidebar LLM PROVIDER block at lines 560–617 (between EMBEDDINGS divider and CONFIG); st.chat_input rewired at lines 947–953; main() docstring at lines 997–1009"

key-decisions:
  - "Locked UI strings preserved verbatim from ROADMAP SC #1 and CONTEXT.md: selectbox label 'LLM provider' (lowercase 'provider', single space); options ['Azure OpenAI', 'Anthropic Claude (MGTI)']; internal keys 'azure_openai' / 'anthropic_mgti' matching _REGISTRY"
  - "Position locked: between EMBEDDINGS and CONFIG. AFTER the EMBEDDINGS-closing st.divider() (was line 547, now 558) and BEFORE st.markdown('### CONFIG'). One new st.divider() added by the LLM PROVIDER block as its closing separator"
  - "_PROVIDER_OPTIONS insertion order is load-bearing (Azure first → default selectbox index points at it). _PROVIDER_KEYS derived as tuple(values()) is a tuple at definition time — order-frozen, no .index() ValueError risk"
  - "Session-state init with .strip() + clamp-to-_PROVIDER_KEYS + logger.warning on unknown — defends against typos and trailing whitespace in LLM_PROVIDER_DEFAULT (RESEARCH.md Pitfall 2). Selectbox index=_PROVIDER_KEYS.index(...) is ValueError-safe by construction"
  - "Active-model caption uses load_settings() NOT get_llm() — sidebar render must not side-effect adapter construction or startup-log emission on every rerun (decision §11). Azure model derived via _extract_model_from_endpoint imported from src.llm.azure_openai (leading underscore intentional; same pattern Plan 05-01 established)"
  - "Anthropic 'NOT CONFIGURED' fallback: when provider unconfigured (missing returns non-empty), _active_model may be empty string — caption renders 'NOT CONFIGURED' literal. Read-only display only; never crashes the render"
  - "missing_vars() called every rerun — NOT @st.cache_data wrapped (would defeat the credential-addition-then-refresh detection, RESEARCH.md Pitfall 10). os.getenv is O(1) so cost is negligible"
  - "Warning template names each missing var with backticks + lists BOTH recovery paths (add to .env + restart OR switch back to Azure OpenAI). icon=':material/warning:' is Streamlit Material-icon syntax (verified working at 1.40+)"
  - "st.session_state['_llm_provider_blocked'] decouples sidebar-render from main-content-render through session_state alone — no parameter ripple, no function-signature changes; main() docstring documents the load-bearing order"
  - "render_main_content modified ONLY at the chat_input call (lines 947–953) — all other render_main_content logic, history rendering, message dict append, process_query call, etc. are UNTOUCHED. Plan 05-03 owns per-message caption work"
  - "Single 'from src.llm import' line (line 20): 'from src.llm import load_settings, missing_vars'. Plan 05-03 will EXTEND this same line to add get_llm (per its decision §14, Option B). Do NOT split into a second from src.llm import line"
  - "Selectbox key= intentionally omitted — index=... + manual write-back chosen for consistency with existing MODE selectbox pattern (decision §5)"

patterns-established:
  - "Clamp-to-known session-state init: getenv → .strip() → check membership in tuple → logger.warning + fallback to first/safe option. Reusable for any future env-driven selectbox"
  - "Sidebar-flag / main-content-reads-flag decoupling: render_sidebar writes a session_state boolean → render_main_content reads via st.session_state.get(KEY, False) at the relevant widget call. No function-signature changes; main() docstring documents the load-bearing order. Future widgets that depend on sidebar state should mimic this pattern"
  - "Load-only sidebar render: sidebar reads provider/model metadata via load_settings(), NEVER via get_llm() — avoids cache resolution, startup log emission, and adapter construction on every rerun"

# Metrics
duration: ~3 min
completed: 2026-05-22
---

# Phase 5 Plan 02: Sidebar Selectbox + Warning Summary

**LLM PROVIDER sidebar block (selectbox + active-model caption + inline missing-creds warning) wired to st.chat_input(disabled=) through a session-state decoupling flag — all in app.py with zero src/ or test changes**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-22T01:51:09Z
- **Completed:** 2026-05-22T01:54:17Z
- **Tasks:** 2
- **Files modified:** 1 (app.py only)

## Accomplishments

- Added module-level `_PROVIDER_OPTIONS` / `_PROVIDER_LABELS` / `_PROVIDER_KEYS` constants near `MODE_OPTIONS` (line 364–370) — single source of truth for UI labels ↔ `_REGISTRY` keys
- Added `from src.llm import load_settings, missing_vars` (line 20) — single import line ready for Plan 05-03 to extend with `get_llm`
- Added new `### LLM PROVIDER` block in `render_sidebar()` between EMBEDDINGS and CONFIG (lines 560–617) with selectbox (locked label `"LLM provider"`, locked options `["Azure OpenAI", "Anthropic Claude (MGTI)"]`), `st.session_state["llm_provider"]` clamp-to-known init from `LLM_PROVIDER_DEFAULT`, `st.caption(f"MODEL: \`{...}\`")`, inline `st.warning` naming each missing var, and `_llm_provider_blocked` flag write
- Modified `st.chat_input` call (lines 947–953) to honor `_llm_provider_blocked` via `disabled=_blocked` + placeholder swap to `"QUERY DISABLED — see sidebar warning"`
- Added load-bearing-order docstring to `main()` (lines 997–1009) locking render_sidebar-before-render_main_content
- Full 69-test suite remains GREEN — zero regression at any boundary

## Task Commits

Each task was committed atomically:

1. **Task 2.1: Add module-level provider option dicts + imports + LLM PROVIDER sidebar block** — `4323e66` (feat)
2. **Task 2.2: Wire chat_input disabled flag + load-bearing main() docstring** — `fc114ea` (feat)

**Plan metadata:** [pending — committed after this summary lands]

## Files Created/Modified

### Only file touched in this plan

- `app.py` (+86 lines net, single file):
  - Line 20: new `from src.llm import load_settings, missing_vars`
  - Lines 364–370: `_PROVIDER_OPTIONS` (`"Azure OpenAI" → "azure_openai"`, `"Anthropic Claude (MGTI)" → "anthropic_mgti"`), `_PROVIDER_LABELS` reverse map, `_PROVIDER_KEYS` tuple
  - Lines 560–617: `### LLM PROVIDER` sidebar block — `st.markdown` header, session-state clamp-to-known init from `LLM_PROVIDER_DEFAULT`, `st.selectbox`, `st.caption` model line, missing-vars `st.warning`, `_llm_provider_blocked` True/False set, closing `st.divider()`
  - Lines 947–953: `st.chat_input` rewired with `(_placeholder, disabled=_blocked)` + load-bearing comment
  - Lines 997–1009: `main()` docstring locking `render_sidebar()`-before-`render_main_content()` order

### Untouched (verified via git diff)

- `src/llm/__init__.py`, `src/llm/config.py`, `src/llm/base.py`, `src/llm/azure_openai.py`, `src/llm/anthropic_mgti.py` — all UNCHANGED (Plan 05-01 deliverables consumed as-is)
- `tests/` — all UNCHANGED (Plan 05-05 acceptance gate is the future test landing)
- `README.md`, `USER_GUIDE.md`, `.env.example` — all UNCHANGED (Plan 05-04 docs territory)

## Exact UI strings now present in app.py

| Element | String |
|---------|--------|
| Sidebar header | `### LLM PROVIDER` |
| Selectbox label | `"LLM provider"` |
| Option 1 | `"Azure OpenAI"` |
| Option 2 | `"Anthropic Claude (MGTI)"` |
| Internal key 1 | `"azure_openai"` |
| Internal key 2 | `"anthropic_mgti"` |
| Model caption template | `f"MODEL: \`{_active_model or 'NOT CONFIGURED'}\`"` |
| Warning template line 1 | `f"**{_human_name}** is not configured. Missing env vars: {_missing_str}."` |
| Warning template line 2 | `f"Add them to your \`.env\` and restart the app, or switch back to Azure OpenAI above."` |
| Warning icon | `:material/warning:` |
| Chat placeholder (unblocked) | `"ENTER QUERY..."` |
| Chat placeholder (blocked) | `"QUERY DISABLED — see sidebar warning"` |

## Module-level `from src.llm import ...` line (as written for Plan 05-03)

```python
from src.llm import load_settings, missing_vars
```

**Plan 05-03 will EXTEND this same line to add `get_llm`** (per Plan 05-03 decision §14, Option B). Do NOT create a second `from src.llm import ...` line.

## Decisions Made

All locked decisions §1–§16 from the plan executed verbatim. Most load-bearing:

- **Decision §2 — Position: between EMBEDDINGS and CONFIG.** Inserted AFTER existing `st.divider()` (previously line 547) and BEFORE `st.markdown("### CONFIG")` (previously line 550). LLM PROVIDER block ends with its own `st.divider()` — clean separator from CONFIG. Existing EMBEDDINGS-vs-LLM-PROVIDER divider stays in place.
- **Decision §4 — Clamp-to-known defense.** `getenv("LLM_PROVIDER_DEFAULT", "azure_openai").strip()` → membership check against `_PROVIDER_KEYS` → `logger.warning` + fallback to `"azure_openai"` on mismatch. Guards against typos like `"Anthropic_MGTI"` (wrong case), `"anthropic"` (close but wrong), empty string, or trailing whitespace — all clamp to `"azure_openai"` so the selectbox index never raises `ValueError`.
- **Decision §6 — Active-model via load_settings().** Sidebar render uses `load_settings()` (pure I/O) NOT `get_llm()` (would trigger `@st.cache_resource` resolution + startup log on every rerun). Azure model extraction via `_extract_model_from_endpoint` imported from `src.llm.azure_openai` (leading underscore intentional — Phase 5 reaches across package internals; Plan 05-01 established this pattern).
- **Decision §9 — chat_input pattern.** `_blocked = st.session_state.get("_llm_provider_blocked", False)` (defaults to False if key absent — defensive against first-render-before-sidebar-ran edge case which CAN'T happen under current `main()` order but is cheap insurance). `_placeholder` swap mandatory per RESEARCH Pitfall 3 — greyed textarea without explanation would confuse users.
- **Decision §13 — Single `from src.llm import` line.** Locked to `from src.llm import load_settings, missing_vars` at line 20. Plan 05-03 will extend it to add `get_llm`. Do NOT split into multiple `from src.llm import` lines.

## Deviations from Plan

**None — plan executed exactly as written.**

- Both tasks landed on the first attempt with no debug iteration
- The two atomic commits (`4323e66`, `fc114ea`) correspond exactly to Task 2.1 and Task 2.2 as specified
- Full 69-test suite remained green after each task (8.57s after Task 2.2; 34.26s after Task 2.1 likely due to first-run cold cache — well within normal range)
- All locked UI strings present verbatim per the post-task grep verification

## Issues Encountered

**One transient tooling issue (not a plan deviation):**

- Initial `python -c "import ast; ast.parse(open('app.py').read())"` failed under Windows Python's default cp1252 codec because the new edit contains UTF-8 em-dash characters (`—` in inline comments). Fixed inline by using `open('app.py', encoding='utf-8')`. No file change needed; `app.py` itself is valid UTF-8 (matches the surrounding codebase which already uses `—` in CSS comments and elsewhere). Documenting here for any future verify-step that runs on a non-UTF-8-locale shell.

## User Setup Required

None — Plan 05-02 is pure UI wiring inside `app.py`. No new env vars, no new dependencies, no documentation updates (Plan 05-04 territory).

## Next Phase Readiness

### Unblocked

- **Plan 05-03 (per-message caption):** Will EXTEND the line-20 `from src.llm import` to add `get_llm`, and read `_PROVIDER_LABELS` for the caption-label dict. The sidebar already writes `st.session_state["llm_provider"]` correctly on every rerun, so any future caption code that reads it as a fallback is on solid ground.
- **Plan 05-04 (documentation):** README + USER_GUIDE updates can now reference the exact UI strings (locked in this plan): "LLM provider", "Azure OpenAI", "Anthropic Claude (MGTI)", `### LLM PROVIDER` sidebar header, the warning template, the "QUERY DISABLED" placeholder.
- **Plan 05-05 (acceptance gate):** Sidebar behavior is now testable via `unittest.mock.patch('streamlit.selectbox', ...)`, `patch('streamlit.warning', ...)`, and `patch('streamlit.chat_input', ...)` — the render functions take no DI arguments; tests patch the `streamlit` module directly per decision §14.

### Verified untouched (no scope creep)

- `src/llm/__init__.py`, `src/llm/config.py`, `src/llm/base.py`, `src/llm/azure_openai.py`, `src/llm/anthropic_mgti.py` — all UNCHANGED
- `tests/` (4 phase test files) — all UNCHANGED; full 69-test suite still green
- `README.md`, `USER_GUIDE.md`, `.env.example` — all UNCHANGED (Plan 05-04 territory)
- All other functions in `app.py` (`render_main_content` outside the chat_input lines, `render_chat_history`, `process_query`, `init_session_state`, every other block in `render_sidebar`) — all UNCHANGED

### Concerns / Blockers

- The operator-run smoke gate against stage gateway (`python scripts/smoke_llm.py --provider both --verbose`) remains pending. Plan 05-02 does NOT depend on it — this plan only adds UI wiring; the underlying adapters are unchanged and were already exercised by the 69-test acceptance suite. Plan 05-04 (documentation) is the natural place to reference the smoke ritual as the final acceptance step before any production deploy.
- Manual UI verification (operator running Streamlit and clicking through the sidebar) is the responsibility of the Phase 5 verification PR review — Plan 05-05 (acceptance gate) covers it programmatically via `streamlit` mocks.

---
*Phase: 05-sidebar-ui-toggle-documentation*
*Completed: 2026-05-22*
