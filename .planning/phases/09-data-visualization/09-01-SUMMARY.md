---
phase: 09-data-visualization
plan: "01"
subsystem: ui
tags: [altair, altair-theme, chart, loro-piana, vibrant-palette, snowgrep-v2.2]

# Dependency graph
requires:
  - phase: 08-screen-restyle
    provides: assistant-card DOM bay where charts render; Phase 6 CSS single-source pattern
provides:
  - src/ui/altair_theme.py — loro_piana Altair theme module with VIBRANT_PALETTE constant
  - @alt.theme.register decorator registering + activating 'loro_piana' at import time
  - Canonical VIBRANT_PALETTE list (5 colors, order-stable) as single source of truth
affects:
  - 09-02 (CSS — may reference VIBRANT_PALETTE for editorial table CSS rationale)
  - 09-03 (chart_generator.py — imports VIBRANT_PALETTE, deletes CHART_COLORS)
  - 09-04 (app.py integration — adds side-effect import of altair_theme)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Side-effect import pattern: module registration at import time, no enable() call"
    - "Altair 6 @alt.theme.register decorator API (NOT deprecated alt.themes.*)"
    - "Single palette source: VIBRANT_PALETTE in altair_theme.py; all chart modules import from here"

key-files:
  created:
    - src/ui/altair_theme.py
  modified: []

key-decisions:
  - "Used @alt.theme.register('loro_piana', enable=True) — Altair 6 new API; avoids AltairDeprecationWarning from old alt.themes.* namespace"
  - "background: transparent — chart inherits assistant-card white, future-proof against card color changes"
  - "VIBRANT_PALETTE order locked: crimson first (VIBRANT_PALETTE[0] = line-chart color)"

patterns-established:
  - "Pattern: Altair theme registration via @alt.theme.register decorator at module scope; enable=True means registration + activation in one decorator call"
  - "Pattern: range.category in theme config auto-applies palette to all nominal Color encodings without per-chart scale= override"

# Metrics
duration: 4min
completed: 2026-05-23
---

# Phase 9 Plan 01: Altair `loro_piana` Theme Module Summary

**Altair 6 loro_piana theme registered at import time via @alt.theme.register — cashmere chrome (EB Garamond/Inter/warm-beige) + 5-color VIBRANT_PALETTE baked into every chart spec**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-23T21:57:41Z
- **Completed:** 2026-05-23T22:01:13Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments

- `src/ui/altair_theme.py` created with `@alt.theme.register("loro_piana", enable=True)` decorator — registers and activates theme in one step at import time
- Cashmere chrome locked: EB Garamond title (20px / weight 300 / charcoal #2C2420), Inter axis labels (#6B5E52 warm-gray), warm-beige gridlines (#E8E0D8), no axis box (domainWidth 0 / tickWidth 0), transparent view stroke
- `VIBRANT_PALETTE` constant exported as single source of truth for chart data colors; Plan 03 (chart_generator.py) and Plan 04 (app.py) import from here
- All 5 verification checks pass: correct exports, `alt.theme.active == "loro_piana"`, theme config in chart spec JSON, zero DeprecationWarning, 22/22 Phase 5 UI tests green

## Task Commits

1. **Task 9-1-01: Create src/ui/altair_theme.py** - `f36c8c5` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `src/ui/altair_theme.py` — Altair 6 loro_piana theme module; exports `VIBRANT_PALETTE` and `loro_piana_theme`

## Decisions Made

- **Altair 6 decorator API**: `@alt.theme.register("loro_piana", enable=True)` — the `enable=True` kwarg means no separate `.enable()` call is needed. The deprecated `alt.themes.*` API was explicitly avoided per 09-RESEARCH.md Pitfall 1.
- **`background: "transparent"`**: Chart inherits the assistant-card background rather than setting a hard color. If the card color changes in a future phase, charts adapt automatically.
- **`VIBRANT_PALETTE[0]` is crimson `#C0392B`**: This ordering is load-bearing — Plan 03's line-chart uses `color=VIBRANT_PALETTE[0]` for the single-series mark color. Order must not change.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `src/ui/altair_theme.py` is ready for Plan 03 to import `VIBRANT_PALETTE` and delete `CHART_COLORS` from `chart_generator.py`
- Theme will activate automatically once Plan 04 adds the side-effect import to `app.py`
- No blockers for Plans 02, 03, or 04

---
*Phase: 09-data-visualization*
*Completed: 2026-05-23*
