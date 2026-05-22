# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** v2.2 SNOWGREP Visual Revamp — Loro Piana quiet luxury aesthetic across all screens.

## Current Position

Phase: 6 — Foundation (CSS module + design tokens + page chrome)
Plan: 03 of 3 — `06-PLAN-03-smoke-render-verification.md` COMPLETE
Status: Phase 6 / Plan 03 complete / Awaiting phase verification
Last activity: 2026-05-22 — Plan 03 closed Phase 6 with user-approved visual checkpoint; all 5 success criteria + all 6 FND requirements verified PASS; three known inline-HTML cosmetic regressions explicitly deferred to Phase 8 (SBR-01/03/06)

Progress: v2.2 — Phase 6 COMPLETE (3 of 3 plans done); Phases 7 and 8 unblocked

```
[██████████] Phase 6  Foundation                       ← COMPLETE (Plans 01-03 done)
[          ] Phase 7  Splash screen                    ← UNBLOCKED
[          ] Phase 8  Screen restyle (sidebar + main)  ← UNBLOCKED
[          ] Phase 9  Data visualization
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

Last session: 2026-05-22 — Phase 6 Plan 03 complete with user-approved visual checkpoint
Stopped at: Phase 6 closeout — all 5 success criteria PASS; all 6 FND requirements complete; three inline-HTML regressions documented as Phase 8 deferred work
Resume file: None
Next: Phase 7 (Splash screen — SPL-01..04) OR Phase 8 (Screen restyle — sidebar/main two-wave) — both unblocked

---
*Last updated: 2026-05-22 after Phase 6 Plan 03 completion (Phase 6 fully shipped).*
