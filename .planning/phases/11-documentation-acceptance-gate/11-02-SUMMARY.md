---
phase: 11-documentation-acceptance-gate
plan: 02
subsystem: testing
tags: [pytest, css, altair, wcag, accessibility, visual-acceptance, loro-piana]

# Dependency graph
requires:
  - phase: 06-foundation
    provides: LORO_PIANA_CSS module + token system (single source of truth for v2.2 typography + palette)
  - phase: 07-splash
    provides: render_splash callable (asserted by TST-02 renderer-signature test)
  - phase: 09-data-visualization
    provides: src.ui.altair_theme side-effect registration + _render_editorial_table (asserted by TST-02)
  - phase: 10-polish-edge-states
    provides: results.py + editorial table CSS (asserted indirectly via CSS-presence checks)
provides:
  - tests/test_phase6_visual.py — TST-02 + TST-03 acceptance gate (12 tests)
  - src/ui/css.py .lp-warn-fix font-size raised 13px → 14px (Resolution 2 option (a))
  - WCAG 2.1 contrast helper (_contrast_ratio, ~10 lines, zero deps)
  - Negative usage scan over var(--lp-text-muted) with role-marker contract
affects:
  - Future v2.2+ phases — any CSS/renderer regression flips TST-02 or TST-03 red
  - Future CSS additions painting in var(--lp-text-muted) must declare uppercase | letter-spacing ≥ 0.1em | font-size ≥ 14px

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level test imports only — zero live Streamlit / HTTP / LLM in acceptance tests"
    - "WCAG 2.1 contrast inline (no pip dep) — sRGB linearization + relative luminance"
    - "Negative usage scan via regex over LORO_PIANA_CSS — enforces design-system role contracts at the rule level"
    - "Allowlist+rationale pattern for pseudo-elements with inherited font-size (declarative, no CSS-cascade resolver)"

key-files:
  created:
    - tests/test_phase6_visual.py
  modified:
    - src/ui/css.py
    - .planning/STATE.md

key-decisions:
  - "Plan 02 enforces design-system role contracts at the CSS-rule level (negative usage scan), not at the rendered-pixel level (no Playwright)."
  - "WCAG large-text role for var(--lp-text-muted) is declared via one of three role markers (uppercase | letter-spacing ≥ 0.1em | font-size ≥ 14px), with one documented allowlist entry for the pseudo-element inheriting font-size."
  - "Resolution 2 option (a) chosen — raise .lp-warn-fix from 13px to 14px instead of writing a per-selector allowlist. 1px visual delta, aligned with WCAG large-text floor, single byte-level edit."
  - "Resolution 1 — NO upper-bound contrast assertion on the warm-gray pair. The computed 5.54 ratio passes 4.5:1; the role constraint is enforced by usage scan, not measured contrast."
  - "Altair API: alt.theme.names() (singular, Altair 6) — NOT alt.themes.names() (plural, deprecated/removed)."
  - "pytest invocation requires `PYTHONPATH=.` prefix — no pyproject.toml / pytest.ini / conftest.py adds repo root to sys.path. Adding such config is OUT OF SCOPE for Plan 02 (separate decision)."

patterns-established:
  - "TST-02 strict-spec scope: CSS presence (typography + 3 palette tokens) + CSS absence (brutalist black + JetBrains Mono on .stApp) + renderer signatures + Altair theme registration. Does NOT check Phase 9 VIBRANT_PALETTE or Phase 10 _render_empty_card signatures — those are out of scope per CONTEXT.md lock."
  - "TST-03 role-marker contract: every CSS rule painting in var(--lp-text-muted) declares text-transform: uppercase OR letter-spacing ≥ 0.1em OR font-size ≥ 14px. One documented allowlist entry for the pseudo-element with inherited font-size."
  - "Test invocation: `PYTHONPATH=. python -m pytest tests/test_phase6_visual.py -v` (Windows PowerShell) or `PYTHONPATH=. pytest ...` (POSIX). Same caveat applies to all existing tests."

# Metrics
duration: 6min
completed: 2026-05-24
---

# Phase 11 Plan 02: Acceptance Gate (TST-01..03) Summary

**v2.2 visual surface programmatically locked: 12 new tests in tests/test_phase6_visual.py covering CSS presence + absence, renderer signatures, Altair theme registration, WCAG-AA contrast, and a negative usage scan over `color: var(--lp-text-muted)` rules — combined suite grows 91 → 103 passing.**

## Performance

- **Duration:** ~6 min (single agent, no checkpoints, no deviations)
- **Started:** 2026-05-24T09:44:09Z
- **Completed:** 2026-05-24T09:50:08Z
- **Tasks:** 2 (1 byte-level edit + 1 new file)
- **Files modified/created:** 2 production-affecting (`src/ui/css.py` modified, `tests/test_phase6_visual.py` created)

## Accomplishments

- **TST-01 preserved** — `tests/test_phase5_ui.py` 22/22 green (locked v2.1 UI strings + the AST-based `_render_provenance_caption` invariant).
- **TST-02 acceptance gate live** — 9 tests across CSS presence (4) + CSS absence (2) + renderer signatures (2) + Altair theme registration (1). Every check imports module-level from `src.ui.*`; zero live Streamlit / HTTP / LLM.
- **TST-03 acceptance gate live** — 3 tests across WCAG-AA contrast (2) + negative usage scan (1). WCAG ratios computed inline (`#2C2420`/`#F5F0EB` → 13.4363; `#6B5E52`/`#F5F0EB` → 5.5393), no pip dep added.
- **Negative usage scan** iterates all 11 rules in `LORO_PIANA_CSS` that paint in `var(--lp-text-muted)` and asserts each declares a large-text role marker (uppercase | letter-spacing ≥ 0.1em | font-size ≥ 14px) OR is the one documented allowlist entry.
- **Single byte-level production edit** to `src/ui/css.py`: `.lp-warn-fix` font-size raised 13px → 14px (Resolution 2 option (a)) so the scan passes without a per-selector allowlist.
- **Combined test baseline grew from 91/91 to 103/103.** Phase 11 ready for verifier.

## Task Commits

1. **Task 1: Raise .lp-warn-fix font-size 13px → 14px** — `7ed4fd9` (fix)
2. **Task 2: Add v2.2 visual + WCAG acceptance gate** — `6aa3344` (test)

**Plan metadata commit:** (pending — staged after this SUMMARY.md + STATE.md)

## Files Created/Modified

- `src/ui/css.py` — single byte-level edit: `[data-testid="stSidebar"] .lp-warn-card .lp-warn-fix` rule font-size changed from `13px` to `14px` (line ~606). All other CSS rules / tokens / `__all__` exports unchanged. LORO_PIANA_CSS length: 42779 chars.
- `tests/test_phase6_visual.py` — NEW. 12 test functions across 6 `# ---` divided groups; module-level helpers `_contrast_ratio`, `_parse_letter_spacing_em`, `_parse_font_size_px`; `_ROLE_MARKER_ALLOWLIST` set with one entry (`.lp-ghost-queries .stButton > button::before`).

## The 12 Test Functions (grouped by concern)

### (a) CSS presence — 4 tests
- `test_css_imports_eb_garamond` — `"EB Garamond"` substring present in `LORO_PIANA_CSS`.
- `test_css_imports_inter` — `"Inter"` substring present.
- `test_css_contains_palette_muted_gold` — `"#8B7355"` (muted gold accent) present.
- `test_css_contains_palette_warm_beige_and_charcoal` — both `"#F5F0EB"` (warm beige page bg) and `"#2C2420"` (charcoal body text) present.

### (b) CSS absence — 2 tests
- `test_css_does_not_contain_brutalist_black` — `"#0a0a0a"` (case-insensitive) NOT present anywhere in `LORO_PIANA_CSS`.
- `test_stapp_block_does_not_use_jetbrains_mono` — extract the `.stApp { ... }` block via regex; assert `"JetBrains Mono"` NOT present in that block (the mono boundary is preserved per Phase 6 Plan 01 decision).

### (c) Renderer signatures — 2 tests
- `test_render_editorial_table_is_callable` — `_render_editorial_table` is callable AND `__module__ == "src.ui.results"`.
- `test_render_splash_is_callable` — `render_splash` is callable AND `__module__ == "src.ui.splash"`.

### (d) Altair theme registration — 1 test
- `test_altair_loro_piana_theme_registered` — `'loro_piana' in alt.theme.names()` (Altair 6 API). Side-effect-import of `src.ui.altair_theme` at module top triggers the `@alt.theme.register('loro_piana', enable=True)` decorator.

### (e) WCAG-AA contrast — 2 tests (Resolution 1)
- `test_wcag_body_text_passes_aa_4_5` — `_contrast_ratio("#2C2420", "#F5F0EB") >= 4.5`. Computed: **13.4363** (well above 4.5:1).
- `test_wcag_warm_gray_on_beige_passes_aa_large_3` — `_contrast_ratio("#6B5E52", "#F5F0EB") >= 3.0`. Computed: **5.5393** (above 3.0:1, also above 4.5:1 — but per Resolution 1, NO upper-bound assertion is written; the role constraint is enforced by the usage scan, not by measured contrast).

### (f) Negative usage scan — 1 test (Resolution 2)
- `test_negative_usage_scan_var_text_muted_role_markers` — for every CSS rule containing `color: var(--lp-text-muted)` in `LORO_PIANA_CSS`, assert the rule body declares one of:
  - `text-transform: uppercase` OR
  - `letter-spacing` ≥ `0.1em` (literal `Xem` value, OR the `var(--lp-tracking-wider)` token via `TOKEN_LETTER_SPACING_OK`) OR
  - `font-size` ≥ `14px` (literal `Xpx` value)
  
  Rules whose selector is in `_ROLE_MARKER_ALLOWLIST` (one entry: `.lp-ghost-queries .stButton > button::before`, which inherits 14px from its parent rule) are explicitly skipped.

## Negative usage scan — full enumeration of var(--lp-text-muted) rules

At commit time, the regex finds **11 rules** painting in `var(--lp-text-muted)` in `LORO_PIANA_CSS`. Each satisfies a role marker (or is allowlisted):

| # | Selector (truncated) | Role marker |
|---|---|---|
| 1 | `.lp-label` | text-transform: uppercase |
| 2 | `[data-testid="stSidebar"] .lp-section-header` | text-transform: uppercase |
| 3 | `[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label …` | text-transform: uppercase |
| 4 | `[data-testid="stSidebar"] .lp-bb-select .stSelectbox label` | text-transform: uppercase |
| 5 | `[data-testid="stSidebar"] .lp-warn-card .lp-warn-fix` | **font-size: 14px** (this plan's edit) |
| 6 | `[data-testid="stSidebar"] [data-testid="stExpander"] summary` (+ siblings) | text-transform: uppercase |
| 7 | `[data-testid="stSidebar"] [data-testid="stSlider"] label p` | text-transform: uppercase |
| 8 | `.lp-page-subtitle` | font-size: 15px |
| 9 | `.lp-ghost-queries .stButton > button::before` | **ALLOWLISTED** (inherits 14px from parent rule) |
| 10 | `[data-testid="stChatInput"] textarea::placeholder` | font-size: 15px |
| 11 | `.lp-empty-card .lp-empty-subtitle` | font-size: 15px |

The plan body anticipated "5 affected sites"; the regex finds 11 (more uppercase small-caps label rules than the plan body enumerated). All 11 still pass — the role-marker contract is broader and more robust than the plan body's narrative.

## Decisions Made

- **PYTHONPATH=. is required for pytest invocation in this repo** (Phase 11 Plan 01 carry-forward, confirmed in Plan 02). The repo has NO `pyproject.toml`, NO `pytest.ini`, NO root `conftest.py`. Bare `pytest tests/test_phase6_visual.py` fails with `ModuleNotFoundError: No module named 'src'`. All verification commands in this plan's `<verify>` blocks were executed with the `PYTHONPATH=.` prefix. Adding `[tool.pytest.ini_options]\npythonpath = ["."]` to a future `pyproject.toml` is OUT OF SCOPE for Plan 02 — it's a separate orthogonal change that should be its own plan/decision in a later phase.
- **Two literal grep guards in the plan's `<verify>` block required minor docstring rephrasings to satisfy:**
  - The plan's composite verification asserts `'alt.themes.names()' not in test_src`. The first draft of the file mentioned `"alt.themes.names() (deprecated, removed in Altair 5+)"` in a docstring. Rephrased to "the deprecated themes-plural namespace (removed in Altair 5+)" — preserves educational intent without leaking the forbidden literal.
  - The plan's composite verification asserts `'assert ratio < 4.5' not in test_src`. The first draft had a section comment "(per Resolution 1: positive 3:1 only for the warm-gray pair; NO `assert ratio < 4.5`)". Rephrased to "NO upper-bound contrast assertion" — preserves Resolution 1 intent without the forbidden literal.
  - Similarly, the comment phrasing "not literal `color: #6B5E52`" was rephrased to "not literal hex strings" to satisfy `grep -c "color: #6B5E52" → 0`.
- **All other plan-verbatim choices honored:** module-level `from __future__ import annotations`, six `# ---` divided groups, no class wrappers, no parametrization (one `def test_*` per spec assertion), `_contrast_ratio` helper at module top (~10 lines, zero deps), `_ROLE_MARKER_ALLOWLIST` with one documented entry, `TOKEN_LETTER_SPACING_OK = {"var(--lp-tracking-wider)"}`.

## Deviations from Plan

**None substantive.** Plan executed as written. The three docstring/comment rephrasings noted above (to satisfy the plan's own composite verification's literal-substring asserts) are not deviations — they're edits to satisfy the plan's stated post-condition. Semantics + test count + WCAG ratios + grep-guard outcomes all match the plan-of-record exactly:

- 12 test functions ✓
- WCAG ratios 13.4363 + 5.5393 within 0.01 tolerance ✓
- No `import streamlit`, no `import requests`, no openai/anthropic ✓
- No `alt.themes.names()` (deprecated form), 4 occurrences of `alt.theme.names()` (current form) ✓
- No `color: #6B5E52` literal ✓
- No `assert ratio < 4.5` literal ✓
- `var(--lp-text-muted)` appears 6 times (well above the ≥2 floor) ✓
- TST-01 (test_phase5_ui.py) still 22/22 ✓
- Combined test suite 103/103 ✓

## Issues Encountered

None. Pre-existing baseline measured at 91/91 (with `PYTHONPATH=.`) before any edits. After Task 1, baseline still 91/91. After Task 2, combined 103/103. WCAG helper math matched the planning-documented expected values on first run.

## Notes / observations

- **pytest invocation requires `PYTHONPATH=.`** (carry-forward from Phase 11 Plan 01). Confirmed at both task-level verification and full-suite verification. Sample commands as executed:
  - `PYTHONPATH=. python -m pytest tests/test_phase6_visual.py -v` → 12 passed
  - `PYTHONPATH=. python -m pytest tests/test_phase5_ui.py -q` → 22 passed
  - `PYTHONPATH=. python -m pytest tests/ -q` → 103 passed
  
  Bare `pytest tests/test_phase6_visual.py` (no PYTHONPATH) fails with `ModuleNotFoundError: No module named 'src'`. Adding `[tool.pytest.ini_options]\npythonpath = ["."]` to a future `pyproject.toml` would resolve this but is OUT OF SCOPE for Plan 02 — flagged for follow-up.
- **The negative usage scan finds 11 var(--lp-text-muted) rules, not 5** as the plan body's narrative suggested. The extra 6 are all small-caps label rules with `text-transform: uppercase` (sidebar section headers, expander summaries, slider labels, mode-radio labels, etc.) — they pass on the uppercase marker. The plan's narrative was incomplete; the scan's contract is correct and stricter.
- **WCAG helper is dependency-free** (~10 lines of math). No new pip dependency added by this plan.
- **TST-02 is intentionally strict-spec scope** (CONTEXT.md lock). It does NOT yet check VIBRANT_PALETTE (Phase 9 chart palette) or `_render_empty_card` / `_render_error_html` (Phase 10 polish renderers). Future plans may extend the gate.

## User Setup Required

None — purely test additions + a 1px CSS font-size bump. No external service config. No new pip dependency. No environment variables.

## Next Phase Readiness

**Phase 11 ready for gsd-verifier.** Both plans complete:
- Plan 01 (DOC-01 + DOC-02) — USER_GUIDE.md Visual Refresh + README.md Screenshots subsection + docs/screenshots/ PNG copies. Committed on `main` (d977c56, d91a11b, 0c69ec7).
- Plan 02 (TST-01..03) — v2.2 visual acceptance gate live. Committed on `main` (7ed4fd9, 6aa3344).

**v2.2 milestone closed at the code level.** All six phases (6-11) green. Acceptance gates in place. Ready for verifier sign-off + v2.2 milestone audit.

---
*Phase: 11-documentation-acceptance-gate*
*Completed: 2026-05-24*
