---
phase: 10-polish-edge-states
plan: "03"
subsystem: ui
tags: [app.py, integration, edge-states, loading-indicators, error-cards, empty-state, streamlit, css-only]

# Dependency graph
requires:
  - phase: 10-01
    provides: POL-01..04 CSS classes in src/ui/css.py (.lp-empty-card, .lp-loading/@keyframes lp-pulse, .lp-error-card, stAlert* overrides)
  - phase: 10-02
    provides: _render_empty_card() and _render_error_html() pure-Python string builders in src/ui/results.py
  - phase: 09-data-visualization
    provides: _render_editorial_table, _render_empty_state, _render_chart_unavailable — existing import line to extend
  - phase: 05-v2.1-ui
    provides: v2.1 invariants locked in tests/test_phase5_ui.py (22 tests; _render_provenance_caption session_state guard; locked UI strings)
provides:
  - "POL-01 satisfied: _render_empty_card() rendered at app.py:749-753 when data_loaded is False — replaces bare return"
  - "POL-02 satisfied: .lp-loading indicators at 3 callsites (CSV load app.py:126, embeddings build app.py:447, query analyze app.py:811)"
  - "POL-03 satisfied: _render_error_html() at 4 in-process_query sites (app.py:608/616/631/718) + outer try/except (app.py:812) — brutalist [ERR] strings gone"
  - "POL-04 satisfied: zero call-site edits — CSS-only coverage via Plan 01 overrides on all 6 st.success/st.error sites"
  - "Full Phase 10 POL-01..04 visual surface closed — nothing brutalist leaks through"
  - "Visual refinements during checkpoint: sidebar action button editorial style, markdown-injection table cell fix, ghost-query button style, Clear History key"
affects:
  - "11-docs: Phase 10 integration complete; all four POL surfaces documented for TST-01/02/03 acceptance gate"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "st.empty() local handle pattern for loading indicators: create before work, .empty() after — NOT session_state (single-rerun scope)"
    - "Per-key Streamlit button CSS override via [class*='st-key-{key}'] selector for buttons with unsafe_allow_html siblings"
    - "Defense-in-depth error handling: inner except Exception inside process_query + outer except (QueryError, LLMError) at call site"
    - "Markdown-injection-inside-td cell fix: .lp-editorial-table tbody td h1..h6/strong/b/p inherit from td to override injected heading styles"

key-files:
  created: []
  modified:
    - app.py

key-decisions:
  - "POL-04 required zero call-site edits — confirmed by inspecting all 6 st.success/st.error callsites; CSS-only from Plan 01 sufficient"
  - "CONTEXT.md line 37 lock honored: per-batch {message} copy suppressed in progress_callback; BUILDING EMBEDDINGS… locked phrase rendered twice (preamble + callback)"
  - "st.empty() local handles used for all 3 loading sites — no session_state writes for loading state (RESEARCH.md #4 confirmed single-rerun scope)"
  - "Markdown-injection-inside-td: Streamlit's st.markdown in table cells injects heading/strong tags that override td font styles; fix via descendant selector inheritance"
  - "Per-key [class*='st-key-_ghost_'] targeting: Streamlit ghost-query buttons share a prefix pattern; wildcard attribute selector covers all without explicit per-button keys"

patterns-established:
  - "Phase 10 error safety net pattern: inner catch-all in process_query + outer (QueryError, LLMError) at chat_message site = defense in depth"
  - "Editorial button style via .st-key-{key}: EB Garamond italic, white text, cashmere bg — reuse for any future sidebar/panel action button needing override"
  - "Ghost/example-query button consistency: match sidebar action button style for visual coherence in empty-state surfaces"

# Metrics
duration: ~2h (including checkpoint and visual refinement iterations)
completed: 2026-05-23
---

# Phase 10 Plan 03: Polish Edge States — app.py Integration Summary

**app.py wired with all four POL surfaces via 10 edit locations: POL-01 empty card, POL-02 three .lp-loading indicators, POL-03 six _render_error_html() callsites, POL-04 CSS-only (zero edits); checkpoint visual refinements polished sidebar buttons, table cell typography, ghost queries, and Clear History**

## Performance

- **Duration:** ~2h (Tasks 1-2 automated; Task 3 human verification checkpoint with visual refinement iterations)
- **Started:** 2026-05-23 (continuation from checkpoint)
- **Completed:** 2026-05-23
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 1 (app.py); CSS refinements in src/ui/css.py (checkpoint deviations)

## Accomplishments

- Wired all four POL requirements into app.py — Phase 10 visual surface is closed; nothing brutalist leaks through
- Replaced 4 brutalist `[ERR] {msg}` string interpolations and added outer try/except safety net for QueryError + LLMError
- Swapped 3 st.spinner callsites for .lp-loading editorial indicators (LOADING DATA…, BUILDING EMBEDDINGS…, ANALYZING…)
- Human verification "approved" after full browser walkthrough of POL-01..04 + sidebar + ghost queries + table cells
- Side mission: ANTHROPIC_DIRECT_MODE flag added to LLM adapter (sk-ant key path) + fixture fix restoring 91/91 tests

## Task Commits

Each planned task committed atomically:

1. **Task 1: Extend imports + wire POL-01 empty card + POL-03 error renderers** — `ffa554f` (feat)
2. **Task 2: POL-02 — Swap spinners for .lp-loading indicators** — `774c3d1` (feat)
3. **Task 3: Human verification checkpoint** — approved (no commit; gate resolved by user)

**Visual refinements during checkpoint (Phase-10-scope deviations):**
- `eeb2321` — fix(10-03): sidebar action button + caption editorial typography (REPLACE/APPEND/LOCK UPLOAD/REBUILD/UPDATE + DROP CSV HERE)
- `273147e` — fix(10-03): editorial table inner typography + sidebar button readability + Clear History editorial style
- `f211ed0` — fix(10-03): ghost-query buttons match REBUILD/UPDATE (white text + EB Garamond italic)

**Out-of-scope side mission (LLM concerns, not POL-* deliverables):**
- `3bdbdfe` — feat(llm): ANTHROPIC_DIRECT_MODE flag for direct sk-ant key in anthropic_mgti adapter
- `8f2e360` — test(llm): add ANTHROPIC_DIRECT_MODE to strip-env fixtures (restores 91/91 tests)

**Plan metadata:** (docs commit follows this summary)

## Files Created/Modified

- `app.py` — 10 planned edit locations + Clear History key addition:
  - **Imports** (line ~25-31): `from src.utils import` extended with `QueryError`; `from src.ui.results import` extended with `_render_empty_card`, `_render_error_html`; new `from src.llm.errors import LLMError`
  - **POL-01** (line ~749-753): `st.markdown(_render_empty_card(), unsafe_allow_html=True)` before `return` when `data_loaded` is False
  - **POL-03 Site A** (line ~608): `"[ERR] NO DATA LOADED — UPLOAD CSV FIRST"` → `_render_error_html("NO DATA LOADED — UPLOAD CSV FIRST")`
  - **POL-03 Site B** (line ~616): `"[ERR] NO EMBEDDINGS — BUILD VIA SIDEBAR"` → `_render_error_html("NO EMBEDDINGS — BUILD VIA SIDEBAR")`
  - **POL-03 Site C** (line ~631): `f"[ERR] {result['error']}"` → `_render_error_html(result["error"])`
  - **POL-03 Site D** (line ~718): `f"[ERR] {str(e)}"` → `_render_error_html(str(e))`
  - **POL-03 outer try/except** (line ~812): new `except (QueryError, LLMError)` + `except Exception` wrapper around `process_query` call
  - **POL-02 Site 1** (line ~126): `with st.spinner(f"{mode_text} CSV DATA...")` → `st.empty()` + `_loading.markdown('... LOADING DATA… ...')` + `_loading.empty()`
  - **POL-02 Site 2** (line ~447): `status_text.text(message.upper())` in embeddings callback → `st.empty()` preamble + `status_text.markdown('... BUILDING EMBEDDINGS… ...')`; `{message}` suppressed per CONTEXT.md line 37 lock
  - **POL-02 Site 3** (line ~811): `with st.spinner("PROCESSING...")` → `_loading = st.empty()` + `_loading.markdown('... ANALYZING… ...')` + `_loading.empty()` (try/except from Task 1 preserved)
  - **Checkpoint deviation**: `key="clear_history"` added to Clear History button + `.st-key-clear_history` CSS rule
- `src/ui/css.py` — Extended during checkpoint:
  - Sidebar action button + caption editorial style (EB Garamond italic 13px, cashmere bg, white text on `p`/`div`/`span` inside buttons)
  - `.lp-editorial-table tbody td h1..h6/strong/b/p` inherit from td (markdown-injection fix)
  - `.st-key-clear_history` editorial style matching sidebar action buttons
  - `[class*="st-key-_ghost_"]` selectors for ghost-query buttons (EB Garamond italic 14px, white text on cashmere)

## Decisions Made

- **POL-04 required zero call-site edits**: All 6 `st.success`/`st.error` callsites at app.py:133, 138, 146, 194, 455, 461 are covered purely by the Plan 01 CSS overrides. Confirmed by inspection — no `st.success`/`st.error` site needed a Python change.

- **CONTEXT.md line 37 lock honored — per-batch {message} suppressed**: The `progress_callback(progress, message)` signature is preserved for `build_embeddings` backward compatibility, but `message` is intentionally ignored in the `.lp-loading` render. Both the preamble `_loading_label` and the per-callback `status_text` render the same locked phrase "BUILDING EMBEDDINGS…". Cycling live per-batch text through the small-caps gold style would be a visual regression.

- **st.empty() local handles, not session_state**: All three loading indicators use function-local `st.empty()` placeholders created and cleared within the same rerun. Per RESEARCH.md #4, these callsites complete within a single rerun — session_state storage would be unnecessary and would violate the v2.1 invariant against new session_state writes in renderer paths.

- **Defense-in-depth error handling**: The inner `except Exception as e` inside `process_query` (Site D) handles synchronous logic errors. The outer `except (QueryError, LLMError)` at the call site catches exceptions that escape (e.g., adapter-raised errors before process_query's inner block runs). Both layers coexist; both render via `_render_error_html()`.

- **Markdown-injection-inside-td is a Streamlit architectural constraint**: When `st.markdown(html, unsafe_allow_html=True)` content includes heading/strong/bold tags and those elements are placed inside an existing `<td>` (e.g., via an editorial table), Streamlit's markdown renderer injects its own heading styles that override the cell's `font-*` properties. Fix: add explicit descendant selectors `.lp-editorial-table tbody td h1, h2, h3, h4, h5, h6, strong, b, p { inherit from td }`. This is a permanent pattern for any future editorial table that may receive markdown-injected content.

- **Per-key `[class*='st-key-_ghost_']` selector pattern**: Ghost-query buttons in the empty-state surface share a `_ghost_` prefix in their Streamlit-generated key class names. A CSS wildcard attribute selector covers all ghost variants without enumerating keys. This extends the `.st-key-{key}` per-button override pattern established in Phase 8.

## v2.1 Invariant Verification

All v2.1 Phase 5 acceptance tests: **22/22 passed**

Locked strings verified present verbatim:
- `"LLM provider"` — sidebar selectbox label (1 match)
- `"Azure OpenAI"` — provider option string (1 match)
- `"Anthropic Claude (MGTI)"` — provider option string (1 match)
- `"QUERY DISABLED — see sidebar warning"` — em-dash preserved (1 match)
- `"Ask anything about your incidents…"` — chat input placeholder (1 match)

Full test suite: **91/91 passed** (includes 12 new LLM fixture tests from side mission)

## POL-04 Verification

POL-04 required **zero call-site edits**. The 6 st.success/st.error callsites in app.py are:

| Line | Call | Coverage |
|------|------|----------|
| ~133 | `st.success("[OK] APPENDED…")` | Plan 01 CSS `.stAlertContentSuccess` override |
| ~138 | `st.success("[OK] LOADED…")` | Plan 01 CSS `.stAlertContentSuccess` override |
| ~146 | `st.error(format_error_message(e))` | Plan 01 CSS `.stAlertContentError` override |
| ~194 | `st.success("[OK] EMBEDDED…")` | Plan 01 CSS `.stAlertContentSuccess` override |
| ~455 | `st.success(…)` | Plan 01 CSS `.stAlertContentSuccess` override |
| ~461 | `st.error(…)` | Plan 01 CSS `.stAlertContentError` override |

All styled via `[data-testid="stAlertContainer"]` and `[data-testid="stAlertContent*"]` — sage/terracotta borders, warm-beige background, small-caps label via `::before`.

## Human Verification

**Status: APPROVED** by user after browser walkthrough on 2026-05-23.

Surfaces verified:
- **POL-01**: Empty card renders on no-CSV-loaded state — "No data loaded" heading in EB Garamond, subtitle in Inter, hairline divider, warm-beige background, no icon
- **POL-02 LOADING DATA…**: Small-caps tracked muted-gold indicator during CSV upload (replaces old circle spinner)
- **POL-02 BUILDING EMBEDDINGS…**: Small-caps tracked muted-gold preamble above progress bar during embeddings build; per-batch text suppressed
- **POL-02 ANALYZING…**: Small-caps tracked indicator inside assistant card while LLM responds; disappears on response arrival
- **POL-03**: Unified error card with 3px terracotta left border, "ERROR" small-caps label, Inter charcoal body — replaces `[ERR]` brutalist prefix
- **POL-04**: `st.success` toasts render with sage 3px left border, "SUCCESS" label; `st.error` toasts with terracotta 3px left border, "ERROR" label — no browser-default green/red
- **Sidebar buttons**: REPLACE/APPEND/LOCK UPLOAD/REBUILD/UPDATE buttons in EB Garamond italic, white text, cashmere background
- **Ghost queries**: Example query buttons in chat empty state match sidebar action button style
- **Clear History**: Key added; `.st-key-clear_history` CSS rule — editorial style consistent with sidebar buttons
- **Editorial table cells**: Markdown-injected headings/strong inside `<td>` now inherit td font styles; no heading-size override artifacts
- **v2.1 regressions**: Sidebar Material Symbols icons intact; locked UI strings intact; Phase 8 sidebar always-visible intact

## Deviations from Plan

### Visual Refinements During Checkpoint (Phase-10-scope)

**1. [Rule 2 - Missing Critical] Sidebar action button + caption editorial typography**
- **Found during:** Task 3 visual verification (checkpoint)
- **Issue:** Sidebar buttons (REPLACE/APPEND/LOCK UPLOAD/REBUILD/UPDATE) rendered with fallback Inter font and non-white text — lacked the EB Garamond italic editorial style established for the design system
- **Fix:** Added per-button `.st-key-*` CSS rules for sidebar action buttons + `.lp-sidebar-caption` rule for DROP CSV HERE caption (EB Garamond italic 13px, cashmere bg, white text on inner `p`/`div`/`span`)
- **Files modified:** src/ui/css.py
- **Commit:** `eeb2321`

**2. [Rule 1 - Bug] Editorial table inner typography + sidebar button readability + Clear History style**
- **Found during:** Task 3 visual verification (checkpoint)
- **Issue 1:** Markdown-injected headings (`h1..h6`), `strong`, `b`, `p` inside `.lp-editorial-table tbody td` overrode the cell's `inherit` font-size/weight, causing heading-scale artifacts in table cells
- **Issue 2:** Sidebar button inner `p`/`div`/`span` had no explicit color override, allowing Streamlit's default dark text to bleed through on cashmere background
- **Issue 3:** Clear History button lacked a `key=` and CSS rule for editorial consistency
- **Fix:** Added `.lp-editorial-table tbody td h1..h6/strong/b/p { inherit }` descendant rule; added `color: var(--lp-neutral-0) !important` on inner elements; added `key="clear_history"` + `.st-key-clear_history` CSS rule
- **Files modified:** src/ui/css.py, app.py (key= addition)
- **Commit:** `273147e`

**3. [Rule 2 - Missing Critical] Ghost-query buttons match sidebar action button style**
- **Found during:** Task 3 visual verification (checkpoint)
- **Issue:** Ghost-query example buttons in the chat empty-state surface used a mismatched visual style — did not match the REBUILD/UPDATE sidebar action button aesthetic, breaking visual coherence on the empty-state surface
- **Fix:** Added `[class*="st-key-_ghost_"]` CSS selectors applying EB Garamond italic 14px, white text on cashmere to all ghost-prefix Streamlit button keys
- **Files modified:** src/ui/css.py
- **Commit:** `f211ed0`

---

**Total deviations:** 3 visual refinements (all Phase-10-scope; applied during checkpoint iteration)
**Impact on plan:** All three refinements directly serve the POL visual polish objective. No scope creep — all touch the same editorial surface (sidebar/panel buttons and editorial table) that Plan 03 wires. Zero functionality change.

### Out-of-Phase-10-scope Side Mission (Traceability Only)

These commits landed in the same branch during the checkpoint session but are LLM-layer concerns, not POL-* deliverables:

**`3bdbdfe` — feat(llm): ANTHROPIC_DIRECT_MODE flag for direct Anthropic API**
- Added `ANTHROPIC_DIRECT_MODE` env flag to `src/llm/anthropic_mgti.py` adapter; enables direct `sk-ant-*` key path for operator testing
- `.env` is gitignored; no credentials committed

**`8f2e360` — test(llm): add ANTHROPIC_DIRECT_MODE to strip-env fixtures**
- Added `ANTHROPIC_DIRECT_MODE` to `conftest.py` strip-env fixture list
- Restores full test suite to 91/91 after `.env` pollution was introduced by the side mission commit above

## Issues Encountered

None during planned task execution. Visual refinements discovered at checkpoint are documented in Deviations above. Side-mission commits are fully contained and did not affect any Phase 10 test coverage.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 10 is **COMPLETE**. All three plans executed:
- 10-01 COMPLETE: POL-01..04 CSS classes in src/ui/css.py
- 10-02 COMPLETE: _render_empty_card + _render_error_html in src/ui/results.py
- 10-03 COMPLETE: app.py wired; 10 edit locations; visual refinements applied; human verified

**Phase 11 (Documentation + Acceptance Gate) is unblocked.**

Phase 11 entry gates:
- TST-01: v2.1 locked UI strings and Phase 5 invariants → **22/22 Phase 5 tests green** (confirmed)
- TST-02: `#2C2420` chart_generator literal → Phase 9 deferred item; may enforce `LABEL_COLOR_CHARCOAL` import
- TST-03: Full regression suite → **91/91 tests green** (confirmed)

No blockers or concerns for Phase 11 start.

---
*Phase: 10-polish-edge-states*
*Completed: 2026-05-23*
