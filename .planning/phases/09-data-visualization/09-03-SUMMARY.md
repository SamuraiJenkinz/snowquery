---
phase: 09-data-visualization
plan: "03"
subsystem: ui
tags: [altair, charts, horizontal-bar, vibrant-palette, loro-piana, dvz-05]

# Dependency graph
requires:
  - phase: 09-01
    provides: VIBRANT_PALETTE constant and loro_piana Altair theme registration in src/ui/altair_theme.py
provides:
  - src/chart_generator.py restylied: horizontal bar charts with value labels, VIBRANT_PALETTE for pie+bar, crimson line
  - CHART_COLORS and configure_chart_theme() deleted — loro_piana theme handles all chrome
  - Bar branch returns alt.LayerChart (bars + text labels layer)
affects: [09-04, 10-polish, app.py integration site]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Horizontal bar: x=Quantitative (value), y=Nominal (category), sort='-x' for largest-at-top ordering"
    - "Layered chart: alt.layer(bars, labels) returns LayerChart; st.altair_chart() accepts it"
    - "Value label layer: mark_text align=left dx=4 baseline=middle with format=',' for thousand-separator"
    - "Theme consumption: no .configure_*() chain on generated charts — loro_piana handles chrome at theme level"
    - "Single source of truth: VIBRANT_PALETTE imported from src.ui.altair_theme, not redefined"

key-files:
  created: []
  modified:
    - src/chart_generator.py

key-decisions:
  - "Bar chart height scales dynamically: max(200, len(chart_df) * 32) — 32px per bar, 200px floor. Old fixed 400px would crowd many-bar horizontal layouts."
  - "Bar chart legend=None on color encoding: y-axis tick labels already name categories, legend would be redundant (per 09-CONTEXT.md Legend rules)."
  - "Line chart mark color is literal '#C0392B' (not VIBRANT_PALETTE[0] reference) — mark_line(color=...) is a mark property not a color encoding, so the theme range.category does not apply; literal is correct here."
  - "Pie chart retains explicit alt.Legend(title=...) — pie has no axis labels to identify segments, so legend is required (per 09-CONTEXT.md Legend rules)."

patterns-established:
  - "Horizontal bar pattern: flip x/y encodings from vertical, use sort='-x' on Y encoding (not '-y') for descending order by bar length."
  - "Value label layer: base = alt.Chart(df); bars = base.mark_bar()...; labels = base.mark_text()...; chart = alt.layer(bars, labels).properties(...)"

# Metrics
duration: 4min
completed: 2026-05-23
---

# Phase 9 Plan 03: Chart Generator Restyle Summary

**Horizontal bar charts with inter-12px charcoal value labels and VIBRANT_PALETTE, dark-theme machinery deleted, loro_piana theme handles all chrome**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-23T22:12:45Z
- **Completed:** 2026-05-23T22:16:38Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Deleted CHART_COLORS constant (10-color brutalist palette) and configure_chart_theme() function (v2.1 dark-theme machinery) — loro_piana theme (Plan 01) handles all chrome
- Rewrote bar branch as horizontal: x=value (Quantitative), y=category (Nominal, sort="-x"), layered mark_text value labels (Inter 12px charcoal #2C2420, dx=4, comma-formatted), returns alt.LayerChart
- Updated pie branch to use VIBRANT_PALETTE; updated line branch to use crimson literal "#C0392B"; added `from src.ui.altair_theme import VIBRANT_PALETTE` import
- All 11 verification checks pass; 22/22 Phase 5 UI tests green

## Task Commits

1. **Task 9-3-01: Delete CHART_COLORS + configure_chart_theme; import VIBRANT_PALETTE; rewrite bar branch + replace pie/line palette refs** - `2ecb8cd` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/chart_generator.py` — Deleted CHART_COLORS + configure_chart_theme(); added VIBRANT_PALETTE import; rewrote bar branch (horizontal, layered value labels); updated pie/line palette refs; no .configure_*() chain

## Decisions Made

- **Dynamic bar height**: `max(200, len(chart_df) * 32)` — 32px per bar with 200px floor. Old fixed 400px would crowd many-bar horizontal layouts.
- **Bar legend=None**: y-axis tick labels already name categories; explicit legend would be redundant (09-CONTEXT.md Legend rules).
- **Line mark color is literal '#C0392B'**: `mark_line(color=...)` is a mark property, not a color encoding; the theme `range.category` does not apply to mark properties. The literal is correct and matches VIBRANT_PALETTE[0].
- **Pie retains alt.Legend**: Pie has no axis labels to identify segments; legend is required per 09-CONTEXT.md Legend rules.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `src/chart_generator.py` is fully restylied per DVZ-05.
- Plan 04 (app.py integration) can now wire `import src.ui.altair_theme` as side-effect import and call `generate_chart()` — the bar branch returns `alt.LayerChart`, which `st.altair_chart()` accepts.
- No blockers.

---
*Phase: 09-data-visualization*
*Completed: 2026-05-23*
