# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** v2.2 SNOWGREP Visual Revamp — Loro Piana quiet luxury aesthetic across all screens.

## Current Position

Phase: 6 — Foundation (CSS module + design tokens + page chrome)
Plan: — (ready for `/gsd:plan-phase 6`)
Status: Roadmap approved; Phase 6 ready to plan
Last activity: 2026-05-22 — v2.2 roadmap approved with 6 phases (6-11), 36/36 requirements mapped (Phases 8+9 merged into single Phase 8 per user feedback)

Progress: v2.2 — 0/6 phases complete

```
[          ] Phase 6  Foundation                       ← READY TO PLAN
[          ] Phase 7  Splash screen
[          ] Phase 8  Screen restyle (sidebar + main)
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

Last session: 2026-05-22 — v2.2 roadmap creation
Stopped at: ROADMAP.md, STATE.md, REQUIREMENTS.md traceability written; Phase 6 ready to plan
Resume command: `/gsd:plan-phase 6`

---
*Last updated: 2026-05-22 after v2.2 roadmap creation.*
