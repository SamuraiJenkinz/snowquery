---
phase: 10-polish-edge-states
plan: "02"
subsystem: ui
tags: [html-renderers, xss-safety, edge-states, pure-python, results-layer]

# Dependency graph
requires:
  - phase: 09-data-visualization
    provides: pure-Python HTML string-builder pattern in src/ui/results.py (3 functions, __all__, html.escape contract)
provides:
  - "_render_empty_card() — POL-01 spec-locked empty-state card HTML (no CSV loaded, no parameters)"
  - "_render_error_html(msg, label='ERROR') — POL-03 unified error card HTML with XSS-safe html.escape() on both msg and label"
  - "__all__ extended from 3 to 5 entries"
  - "Module docstring updated to 'Five pure-Python string builders'"
affects:
  - "10-03 (app.py integration): must import _render_empty_card and _render_error_html from src.ui.results"
  - "11-docs: __all__ now 5 entries; both new functions in public API"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-Python string-builder pattern extended: new functions follow same shape as Phase 9 (return str, no Streamlit import, html.escape for user-supplied data)"
    - "XSS-safety contract extended: both msg and label in _render_error_html escaped via html.escape()"
    - "Spec-locked verbatim strings: _render_empty_card heading/subtitle must not be altered (REQUIREMENTS.md POL-01)"

key-files:
  created: []
  modified:
    - src/ui/results.py

key-decisions:
  - "NAMING: _render_empty_card (NOT _render_empty_state — that name already taken by Phase 9 0-row fallback at line 222)"
  - "Both new functions coexist with Phase 9 _render_empty_state — distinct CSS classes (lp-empty-card vs lp-et-empty), distinct labels (no label vs NO RESULTS)"
  - "_render_error_html label parameter also XSS-escaped — not just msg — matching the module's documented contract for all user-supplied data"
  - "No new imports added — html stdlib already imported at line 29; no Streamlit import added (call site pattern preserved)"

patterns-established:
  - "Phase 10 edge-state renderers: same pure-string-builder shape as Phase 9 (return str; st.markdown at call site in Plan 03)"
  - "__all__ multi-line form (5 entries): more readable than single-line for >3 exports"

# Metrics
duration: 10min
completed: 2026-05-23
---

# Phase 10 Plan 02: Polish Edge States — Empty Card + Error HTML Renderers Summary

**Two XSS-safe pure-Python HTML renderers added to src/ui/results.py: spec-locked POL-01 empty card and POL-03 unified error card with html.escape() on both msg and label**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-24T00:49:00Z
- **Completed:** 2026-05-24T00:59:02Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `_render_empty_card()` — POL-01 spec-locked card shown when no CSV is loaded; heading "No data loaded" and subtitle "Upload incidents.csv from the sidebar to begin." are verbatim-locked per REQUIREMENTS.md
- Added `_render_error_html(msg, label='ERROR')` — POL-03 unified error card for QueryError and LLMError; both `msg` and `label` HTML-escaped via `html.escape()` before interpolation
- Extended `__all__` from 3 to 5 entries (multi-line form for readability)
- Updated module docstring from "Three pure-Python string builders" to "Five pure-Python string builders"
- Phase 9 `_render_empty_state` is byte-identical to pre-edit state — no collision confirmed by assertion test

## Task Commits

1. **Task 1: Add _render_empty_card and _render_error_html to src/ui/results.py** - `0562cb6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/ui/results.py` — Added 2 new functions, extended `__all__` (3→5), updated docstring; grew from 276 to 360 lines

## Decisions Made

- **CRITICAL NAMING**: `_render_empty_card` (not `_render_empty_state` — already taken). Both coexist: `_render_empty_state` has `.lp-et-empty` class and `NO RESULTS` label; `_render_empty_card` has `.lp-empty-card` class and `No data loaded` heading.
- **`label` parameter also XSS-escaped**: The plan spec said "msg and label are both HTML-escaped via html.escape()" — both are escaped in `_render_error_html`, matching the module's XSS-safety contract for all user-supplied content.
- **No new imports**: `html` stdlib was already at line 29; `pandas` already imported; no Streamlit import added. Module stays dependency-free per the pure-string-builder contract.

## XSS-Safety Verification Results

All four XSS contract assertions passed:

1. `_render_error_html('<script>alert(1)</script>')` — `<script>` absent, `&lt;script&gt;` present
2. `_render_error_html('msg', label='<b>bad</b>')` — `<b>` absent, `&lt;b&gt;` present
3. Default label renders as `>ERROR<` in output — no escaping needed for literal default
4. `_render_empty_card()` — no interpolation, all strings spec-locked literals; no escaping needed

## Coexistence Verification (Phase 9 Naming Guard)

```
_render_empty_state()  → class="lp-et-empty"  label="NO RESULTS"  (Phase 9, 0-row query fallback)
_render_empty_card()   → class="lp-empty-card" heading="No data loaded" (Phase 10, no-CSV surface)
```

Assertion `'lp-empty-card' not in _render_empty_state()` passes — zero collision confirmed.

## `__all__` Extension (3 → 5)

Before:
```python
__all__ = ["_render_editorial_table", "_render_empty_state", "_render_chart_unavailable"]
```

After:
```python
__all__ = [
    "_render_editorial_table",
    "_render_empty_state",
    "_render_chart_unavailable",
    "_render_empty_card",
    "_render_error_html",
]
```

## Deviations from Plan

None — plan executed exactly as written. Three coordinated edits (docstring, two functions, `__all__`) applied in order. No imports added. No existing functions modified.

## Issues Encountered

`pytest tests/test_phase5_ui.py` invoked with bare `pytest` yields `ModuleNotFoundError: No module named 'src'` (pre-existing environment issue — `src` is not on `sys.path` without the project root). Running as `python -m pytest tests/test_phase5_ui.py` passes 22/22. This is a pre-existing CI configuration note, not caused by this plan's changes.

## Hand-off Note for Plan 03 (app.py Integration)

Plan 03 must extend the import line at `app.py` line 31 (or wherever `src.ui.results` is imported) to include the two new symbols:

```python
from src.ui.results import (
    _render_editorial_table,
    _render_empty_state,
    _render_chart_unavailable,
    _render_empty_card,      # POL-01: shown when data_loaded is False
    _render_error_html,      # POL-03: replaces brutalist [ERR] strings
)
```

Call sites in `app.py::process_query` and the main panel branch:
- `_render_empty_card()` → render when `st.session_state.data_loaded is False`; wrap in `st.markdown(html, unsafe_allow_html=True)`
- `_render_error_html(str(e))` → replace `[ERR] {e}` string patterns in error branches; wrap in `st.markdown(html, unsafe_allow_html=True)`

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both new renderers are importable, callable, and verified
- Phase 9 `_render_empty_state` is untouched — no regression
- 22/22 Phase 5 UI tests green
- Plan 03 (app.py call-site wiring for POL-01 + POL-03) is unblocked
- Plan 01 (src/ui/css.py POL-01 + POL-03 CSS classes) may run in parallel — this plan touches only src/ui/results.py

---
*Phase: 10-polish-edge-states*
*Completed: 2026-05-23*
