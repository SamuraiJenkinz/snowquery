# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** v2.2 SNOWGREP Visual Revamp — Loro Piana quiet luxury aesthetic across all screens.

## Current Position

Phase: 9 — Data visualization — In progress
Plan: 3 of 4 complete
Status: Phase 8 COMPLETE + verified; Phase 9 Plans 01-03 complete
Last activity: 2026-05-23 — Completed 09-03-PLAN.md (chart_generator restyle — horizontal bars, vibrant palette, value labels)

Progress: v2.2 — Phases 6-8 COMPLETE; Phase 9 in progress (2/4 plans done)

```
[██████████] Phase 6  Foundation                       ← COMPLETE (Plans 01-03 done)
[██████████] Phase 7  Splash screen                    ← COMPLETE (Plans 01-02 done)
[██████████] Phase 8  Screen restyle (sidebar + main)  ← COMPLETE (Plans 01-02 done)
[██████    ] Phase 9  Data visualization               ← IN PROGRESS (Plans 01-03 done)
[          ] Phase 10 Polish + edge states
[          ] Phase 11 Documentation + acceptance gate
```

## v2.2 Phase Map (summary)

| Phase | Name                                   | Requirements                                                                                          | Depends on   |
| ----- | -------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------ |
| 6     | Foundation (CSS + tokens)              | FND-01..06                                                                                            | —            |
| 7     | Splash screen                          | SPL-01..04                                                                                            | 6            |
| 8     | Screen restyle (sidebar + main)        | SBR-01..06, MAIN-01..06 (12 reqs)                                                                     | 6            |
| 9     | Data visualization                     | DVZ-01..05                                                                                            | 8            |
| 10    | Polish + edge states                   | POL-01..04                                                                                            | 6, 8, 9      |
| 11    | Documentation + acceptance gate        | DOC-01..02, TST-01..03                                                                                | 6-10         |

Phase 8 contains two parallelizable waves (sidebar SBR-* and main panel MAIN-*) — disjoint DOM regions sharing the Phase 6 CSS module read-only.

## v2.2 Design Reference

Three Stitch mockups generated 2026-05-22 and validated by user:
- `.planning/design-mockups/00-splash-helix.png` — splash with helix data motion
- `.planning/design-mockups/01-main-chat.png` — hero chat + sidebar
- `.planning/design-mockups/02-results-chart.png` — query results with chart

Live in Stitch: https://stitch.withgoogle.com/projects/11615568135320819515

Design system: Loro Piana Luxe — palette, tokens, components at `C:\Users\taylo\.claude\skills\loro-piana-aesthetic\`

## v2.1 Open Pre-Prod Gates (carried forward)

- **SMK-05 live smoke run against staging gateway** (`python scripts/smoke_llm.py --provider both --verbose`) — pre-authorized operator gate before production deploy. Documented in `.planning/milestones/v2.1-MILESTONE-AUDIT.md` §7.

## Accumulated Context

### Decisions (recent)

- **Phase 9 Plan 02 — results.py in src/ui/ (NOT src/utils.py)**: utils.py has zero Streamlit-adjacent helpers; results.py is the logical home alongside css.py and splash.py. Plan 04 imports from `src.ui.results`.
- **Phase 9 Plan 02 — DVZ-03 truncation cap confirmed at 50**: User-approved deviation from REQUIREMENTS.md `>1000` literal; editorial table is the hero view and must be scannable at a glance. The 50-row cap is encoded in `_TRUNCATION_CAP` constant; caption spec-locked verbatim with U+00B7 middot and comma-formatted N.
- **Phase 9 Plan 02 — hover background rgba(245,240,235,0.5) is a literal exception**: No half-alpha token exists in the design system; this one CSS value is kept as a literal and documented in the SUMMARY. All other new CSS uses existing `var(--lp-*)` tokens.
- **Phase 9 Plan 02 — Pure-HTML-string renderer pattern**: `results.py` functions return strings; `st.markdown(html, unsafe_allow_html=True)` call lives at the Plan 04 integration site in `display_results`. No Streamlit import in `results.py`.
- **Phase 9 Plan 01 — Altair 6 `@alt.theme.register` API**: Use `@alt.theme.register('loro_piana', enable=True)` decorator — NOT the deprecated `alt.themes.*` namespace. The `enable=True` kwarg registers and activates in one call; no separate `.enable()` needed. This is the SNOWGREP canonical pattern for Altair theme registration; applies process-wide at import time.
- **Phase 9 Plan 03 — Bar chart height dynamic**: `max(200, len(chart_df) * 32)` — 32px per bar, 200px floor. Old fixed 400px would crowd many-bar horizontal layouts.
- **Phase 9 Plan 03 — Line mark color is literal '#C0392B'**: `mark_line(color=...)` is a mark property not a color encoding; theme `range.category` does not apply to mark properties. Literal matches VIBRANT_PALETTE[0].
- **Phase 9 Plan 01 — VIBRANT_PALETTE is the canonical chart data palette source**: `src/ui/altair_theme.py` is the single source of truth for the 5-color vibrant palette. Plan 03 (chart_generator.py) imports `VIBRANT_PALETTE` from here; Plan 04 (app.py) adds the side-effect import. No other module may redefine these colors.
- **Phase 9 Plan 01 — `background: transparent` in chart theme**: Chart background inherits the assistant-card white; setting transparent future-proofs against card color changes. Charts visually integrate with the card without needing a matching hardcoded color.
- **Phase 8 — Branded logo PNG replaces both sidebar wordmark and main panel hero**: Single asset at `static/snowgrep-logo.png` (copper SNOWGREP box outline + blue INCIDENT INTELLIGENCE tagline on dark backdrop). Served via Streamlit static serving (`.streamlit/config.toml: enableStaticServing = true`). Sidebar uses `max-width: 240px` (fits 320px sidebar), main panel uses `max-width: 480px`. The dark backdrop of the PNG is intentional — it provides high contrast against the warm-beige page bg, framing the logo as a deliberate brand mark. Future asset additions should drop into `static/` and reference via `app/static/<filename>`. Original PNG had a "SNOWGRP" typo; patched via Pillow (cover existing text with bg color, re-render with Impact font + matching copper #aa7346) — original grunge stencil texture lost in the patch (not recoverable without source PSD).
- **Phase 8 SBR-03 — MODE selector uses `st.radio(horizontal=True)` not three st.button pills**: The button-in-columns approach failed because `st.markdown('<div class="...">')` + subsequent `st.button` render as sibling DOM nodes, so the active-state CSS selector never matched. Also at 320px / 3 cols, "SEMANTIC" wrapped per-character. The radio uses a custom sage dot (`#8A9A7D` filled circle when checked) via `:has(input:checked) > div:first-child` — clean active-state contract with no Python-side class juggling. Pattern is reusable for other small toggle groups: native primitives with `:has(input:checked)` beats manual sibling-state tracking.
- **Phase 8 — `.lp-pill-warn` is the v2.2 soft-warning pill primitive**: Used by USING DEFAULT PASSWORD, NO DATA LOADED, and UNLOCK UPLOAD (via per-button `.st-key-unlock_upload` override). Warm-beige tint bg + terracotta text + rounded pill. Phase 9-10 should reuse this class for sibling status indicators rather than re-rolling.
- **Phase 8 — `.st-key-{key}` is the per-button CSS override pattern** for Streamlit 1.36+. Used here to make UNLOCK UPLOAD a soft pill that overrides Phase 6's global cashmere fill. Future phases needing per-button visual variants should use this pattern. Streamlit emits `class="st-key-<key>"` on the button wrapper when `key=` is set on `st.button(...)`.
- **Phase 8 — Sidebar is non-collapsible in v2.2**: Phase 6 hides Streamlit's `<header>` element globally, which also hides the sidebar expand toggle. Once collapsed, no in-UI recovery. Forced sidebar always-visible via `transform: none !important; margin-left: 0 !important; visibility: visible !important` on `[data-testid="stSidebar"]` regardless of `aria-expanded`; collapse buttons hidden via `display: none`. Sidebar is mission-critical for this app (only place to upload data + configure LLM).
- **Phase 8 — Streamlit `*` font-family override breaks Material Symbols icons**: Phase 6's universal `[data-testid="stSidebar"] *` font-family override clobbered Streamlit's Material Symbols font, causing icon names like `keyboard_arrow_down` to render as literal text in the expander chevron and help tooltips. Fixed by restoring Material Symbols on `[class*="material-symbols"]`, `[class*="material-icons"]`, `[data-testid*="Icon"]` inside the universal rule's scope. Future phases adding broad font-family rules MUST exclude icon-bearing spans.
- **Phase 7 Plan 02 — Splash lifecycle owns timing client-side**: Python only emits `snowgrep-splash-dismiss` postMessage + sleeps 400ms for fade teardown. The 4s hard cap lives entirely in the iframe script. This pattern is reusable for any future iframe-based overlay: enforce timing constraints client-side; Python manages mount/dismiss only.
- **Phase 7 Plan 02 — st.empty() placeholder handle stored in session_state**: Storing the `st.empty()` handle in `st.session_state._splash_placeholder` allows a later rerun to clear what a previous rerun mounted. Required pattern whenever a placeholder is created in one Streamlit rerun and torn down in another.
- **Phase 7 Plan 01 — str.format() requires doubled CSS braces**: Plan 07-01 incorrectly stated "CSS braces pass through .format() untouched." Python's str.format() parses ALL {…} as placeholders. The template uses {{…}} for all CSS rule blocks, keyframe percentages, and JS function bodies. Only the 6 actual Python values use single braces. This is a carry-forward: any future phase using str.format() for HTML/CSS templates must double all non-placeholder braces.
- **Phase 7 Plan 01 — JS const DISMISS_TYPE pattern**: Instead of writing JS object literals like `{type: 'snowgrep-splash-dismiss'}` inside a str.format() template (which causes KeyError), declare the string as a JS const first and reference it. This avoids {key: value} shapes in the template body.
- **Phase 7 Plan 01 — splash comment hex quotes break grep invariant**: Python comments containing quoted hex strings like `# "#F5F0EB"` still match the brand-hex-literal grep test. Use descriptive comments instead (`# warm off-white`).
- **Phase 6 Plan 03 — verification = static grep battery + DevTools human-verify, screenshot optional**: Phase 6 closeout used a 7-group / 15-assertion static grep battery followed by a live human-verify DevTools checkpoint. User performed live DevTools Computed-tab inspection rather than saving a screenshot; observed values (background `rgb(245, 240, 235)`, body `font-family: Inter, ...`, cashmere `UNLOCK UPLOAD` button) recorded directly in SUMMARY. Network-tab inspection of Google Fonts skipped — resolved-font evidence (body computes to Inter, not fallback) accepted as sufficient. Pattern: future phase verification plans can substitute live DevTools observations for screenshots when the user is co-present.
- **Phase 6 Plan 03 — inline-HTML brutalist regressions are Phase 8 work, not Phase 6 gaps**: User's live inspection surfaced three cosmetic regressions in `app.py` — green "SNOWGREP" wordmark + "S" box + divider line, warning panel text overlap, amber "NO EMBEDDINGS" / "USING DEFAULT PASSWORD" status colors. All three are caused by inline `st.markdown(<div style="...">)` HTML chunks with hardcoded brutalist colors that bypass the Phase 6 token system. Phase 6's contract is the CSS module + global selectors; converting inline HTML to consume tokens is Phase 8's contract. User explicitly approved Phase 6 closure with this understanding. Owners: SBR-01 (wordmark hero → EB Garamond 28px charcoal), SBR-06 (warning panel → warm-beige + terracotta 3px left border + small-caps label), SBR-03 (status pills → sage/terracotta).
- **Phase 6 Plan 02 — app.py is a CSS consumer, never a duplicator**: `app.py` now imports `LORO_PIANA_CSS` from `src.ui.css` and injects it once via `st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)`. The brutalist CSS slab (315 lines, lines 38-352 pre-edit) was deleted outright — no `legacy_brutalist_css.py` archive. Recovery path is `git show 99befab^:app.py` if ever needed. Future phases that need new CSS extend `src/ui/css.py`; `app.py` stays untouched for styling.
- **Phase 6 Plan 02 — page chrome glyph**: `page_icon="✦"` (U+2726 BLACK FOUR POINTED STAR) replaces `▣` (U+25A3). Single character glyph in source as UTF-8, no escape sequence. `page_title="SNOWGREP"` LOCKED — every future phase preserves it verbatim.
- **Phase 6 Plan 01 — single source of truth pattern**: `src/ui/css.py` exports exactly two constants (`LORO_PIANA_TOKENS` dict, `LORO_PIANA_CSS` string) with `__all__` whitelist. All future v2.2 code reads tokens/CSS from this module — no module is permitted to hardcode Loro Piana hex values or Streamlit selector overrides. Plan 02+ extends here, never duplicates.
- **Phase 6 Plan 01 — mono boundary established**: JetBrains Mono confined to `code, pre, kbd, samp, .lp-mono, [data-testid="stCodeBlock"], [data-testid="stCode"]`. Everything else renders in Inter (body) and EB Garamond (headlines). Streamlit's monospace default is clobbered via `.stApp { font-family: var(--lp-font-body) !important; }`. Future phases preserve this boundary.
- **v2.1 Phase 5 invariant carries forward**: `_render_provenance_caption(provider, model)` must never read `st.session_state` — history messages keep original provenance after mid-session switches. AST-based regression test in `tests/test_phase5_ui.py` locks this. v2.2 Phase 8 (MAIN-04) only restyles CSS — does NOT touch the helper's read sources.
- **v2.1 locked UI strings carry forward verbatim**: `"LLM provider"`, `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"QUERY DISABLED — see sidebar warning"`. Phase 8 (SBR-05, SBR-06, MAIN-06) restyles MUST preserve them; Phase 11 (TST-01) gates the milestone with them still asserted true.
- **v2.2 dataframe pattern**: editorial HTML hero + `st.expander` containing native `st.dataframe` — zero functionality loss vs. fighting glide-data-grid CSS. Removes 4-6h estimate risk. Phase 9 lands this.
- **v2.2 skip research**: loro-piana-aesthetic skill is the design source; Stitch mockups have validated the look; Streamlit CSS limits are implementation knowledge not domain research.
- **v2.2 Phase 8 merged from sidebar + main panel**: per user feedback, the two parallelizable regions are one phase with two waves (Wave A: sidebar SBR-*, Wave B: main panel MAIN-*) rather than two separate phases. Total v2.2 phases drop from 7 to 6; coverage stays 36/36.
- **v2.2 phase structure**: foundation → splash → screen restyle (two waves) → results layer → polish → docs/gate. Mirrors the v2.1 seam-first pattern but applied to CSS.

Full decision log: `.planning/PROJECT.md` Key Decisions table.

### Resolved Blockers

(None active)

### Open Blockers/Concerns

(None for Phase 6 start)

## Session Continuity

Last session: 2026-05-23 — Phase 9 Plan 03 execution (chart_generator restyle, horizontal bars, VIBRANT_PALETTE, value labels, 22/22 tests green)
Stopped at: Phase 9 Plan 03 COMPLETE — 2ecb8cd feat(9-3): restyle chart_generator horizontal bars vibrant palette theme
Resume file: None
Next: Phase 9 Plan 04 (app.py integration — wire altair_theme side-effect import, display_results wiring)

---
*Last updated: 2026-05-23 after Phase 9 Plan 01 completion.*
