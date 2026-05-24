---
phase: 10-polish-edge-states
plan: "01"
subsystem: css
tags: [css, edge-states, empty-state, loading, error-card, alert-overrides, loro-piana]

dependency-graph:
  requires:
    - "Phase 6 css.py foundation (--lp-* tokens, LORO_PIANA_CSS string)"
    - "Phase 8 .lp-warn-card sidebar primitive (anatomy template for .lp-error-card)"
    - "Phase 9 Phase 9 DVZ-01..05 CSS extensions (lp-editorial-table, lp-chart-unavailable)"
  provides:
    - "POL-01 .lp-empty-card + slots (.lp-empty-heading, .lp-empty-divider, .lp-empty-subtitle)"
    - "POL-02 .lp-loading + @keyframes lp-pulse"
    - "POL-03 .lp-error-card + slots (.lp-error-label, .lp-error-body)"
    - "POL-04 stAlert* overrides (stAlertContainer, stAlertContent{Success,Error,Warning,Info}, stAlertDynamicIcon)"
  affects:
    - "Plan 02 (src/ui/results.py renderer functions consume .lp-empty-card, .lp-loading, .lp-error-card)"
    - "Plan 03 (app.py integration sites consume all four POL CSS vocabularies)"

tech-stack:
  added: []
  patterns:
    - "CSS-only Streamlit alert overrides via :has() + ::before pseudo-elements"
    - "Alert-scoped icon suppression (stAlert-parent → stAlertDynamicIcon child)"

file-tracking:
  key-files:
    created: []
    modified:
      - path: "src/ui/css.py"
        change: "Appended 188 net new lines (four POL-01..04 annotated sections)"

decisions:
  - "stAlertDynamicIcon is the correct testid (not stAlertContentIcon which appeared in CONTEXT.md — RESEARCH.md verified against Streamlit 1.52.1)"
  - "Alert icon suppression is scoped under [data-testid='stAlert'] parent to avoid global icon kills"
  - "POL-03 .lp-error-card is main-panel scoped; anatomy mirrors Phase 8 .lp-warn-card but selector is NOT nested under stSidebar"
  - "lp-neutral-400 token used for INFO alert and .lp-loading color (muted gold — no new token introduced)"

metrics:
  duration: "~8 minutes"
  completed: "2026-05-24"
---

# Phase 10 Plan 01: Polish Edge States — CSS Vocabulary Summary

**One-liner:** Four annotated CSS sections (POL-01..04, 188 lines) extend LORO_PIANA_CSS with empty-card, loading pulse, error card, and Streamlit alert palette overrides using only existing --lp-* tokens.

## What Was Done

Extended `src/ui/css.py` with all CSS vocabulary required by Phase 10's four polish requirements. The file grew from ~1083 lines to 1271 lines (+188 lines net new CSS). No Python logic was changed. No tokens were introduced.

### CSS Blocks Appended

| Block | Selector(s) | Token Usage | Lines |
|-------|-------------|-------------|-------|
| POL-01 Empty card | `.lp-empty-card`, `.lp-empty-heading`, `.lp-empty-divider`, `.lp-empty-subtitle` | `--lp-bg`, `--lp-border`, `--lp-radius-md`, `--lp-space-4/8`, `--lp-font-display`, `--lp-font-body`, `--lp-text`, `--lp-text-muted` | ~30 |
| POL-02 Loading pulse | `.lp-loading`, `@keyframes lp-pulse` | `--lp-font-body`, `--lp-neutral-400`, `--lp-space-2` | ~15 |
| POL-03 Error card | `.lp-error-card`, `.lp-error-label`, `.lp-error-body` | `--lp-bg`, `--lp-danger`, `--lp-border`, `--lp-radius-md`, `--lp-space-2/4`, `--lp-font-body`, `--lp-text` | ~25 |
| POL-04 Alert overrides | `[data-testid="stAlert"] [data-testid="stAlertContainer"]`, stAlertContent{Success,Error,Warning,Info}, `stAlertDynamicIcon` | `--lp-radius-md`, `--lp-space-4/2`, `--lp-bg`, `--lp-font-body`, `--lp-text`, `--lp-border`, `--lp-success`, `--lp-danger`, `--lp-warning`, `--lp-neutral-400` | ~90 |

## Verified Testid Corrections vs CONTEXT.md

CONTEXT.md contained a typo for the alert icon testid. This plan uses the corrected value verified against Streamlit 1.52.1 (per `10-RESEARCH.md`):

| Attribute | CONTEXT.md (wrong) | RESEARCH.md + this plan (correct) |
|-----------|-------------------|----------------------------------|
| Alert icon suppression | `stAlertContentIcon` | `stAlertDynamicIcon` |

Verification: `grep -c "stAlertContentIcon" src/ui/css.py` returns **0**. `grep -c "stAlertDynamicIcon" src/ui/css.py` returns **1** (alert-scoped under `[data-testid="stAlert"]` parent).

## Phase 6/8/9 CSS Regression Confirmation

All pre-edit regression counts verified unchanged after both task commits:

| CSS Pattern | Pre-edit Count | Post-edit Count | Status |
|-------------|---------------|----------------|--------|
| `lp-warn-card` (CSS rules) | 5 rules | 5 rules (+ 1 comment reference) | PASS — rules unmodified |
| `lp-section-header` | 1 | 1 | PASS |
| `lp-editorial-table` | 9 | 9 | PASS |
| `lp-chart-unavailable` | 3 | 3 | PASS |
| Phase 8 `stSidebar` Material Symbols restoration | 1 | 1 | PASS — byte-identical at css.py:280-287 |

Note: `lp-warn-card` grep count shows 6 post-edit because POL-03's comment block references the name for documentation context (`does NOT reuse the sidebar .lp-warn-card selector`). All 5 actual CSS rule occurrences are unchanged.

Composite 15-token assertion passed:
```
All 15 Phase 10 CSS tokens present; no stale typo.
```

`python -c "import app; print('app imports OK')"` passed.

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1: POL-01/02/03 | eecf8b9 | feat(10-01): append POL-01/02/03 CSS blocks to LORO_PIANA_CSS |
| Task 2: POL-04 | 9bd5da9 | feat(10-01): append POL-04 Streamlit alert palette overrides |

## Deviations from Plan

None — plan executed exactly as written. The `lp-warn-card` grep count showing 6 (vs the plan's expected 5) is explained by the POL-03 comment reference and does not represent a regression to Phase 8 CSS rules.

## Hand-off Notes for Plan 02 and Plan 03

**Plan 02 (src/ui/results.py — renderer functions):**
The CSS vocabulary is now available. Renderer functions can emit HTML with these classes:
- Empty state: `<div class="lp-empty-card">` + `<h2 class="lp-empty-heading">` + `<hr class="lp-empty-divider">` + `<p class="lp-empty-subtitle">`
- Loading: `<p class="lp-loading">LOADING…</p>` (or ANALYZING…, BUILDING EMBEDDINGS…)
- Error: `<div class="lp-error-card">` + `<div class="lp-error-label">ERROR</div>` + `<div class="lp-error-body">{message}</div>`

**Plan 03 (app.py — integration):**
Alert callsites (`st.success`, `st.error`, `st.warning`) require NO changes — POL-04 is a pure CSS sweep. The six existing callsites (app.py:133, 138, 146, 194, 455, 461) are already covered. The integration work for Plan 03 is wiring `_render_empty_card()`, `_render_loading_html()`, and `_render_error_html()` from Plan 02 into the appropriate display branches.
