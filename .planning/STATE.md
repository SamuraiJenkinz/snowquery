# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Current focus:** v2.2 SNOWGREP Visual Revamp — Loro Piana quiet luxury aesthetic across all screens.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-22 — Milestone v2.2 started; PROJECT.md updated, research skipped (loro-piana-aesthetic skill is the design source)

Progress: v2.2 phases TBD (defining)

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

- **v2.1 Phase 5 invariant carries forward**: `_render_provenance_caption(provider, model)` must never read `st.session_state` — history messages keep original provenance after mid-session switches. AST-based regression test in `tests/test_phase5_ui.py` locks this. v2.2 visual changes must preserve this invariant.
- **v2.2 dataframe pattern**: editorial HTML hero + `st.expander` containing native `st.dataframe` — zero functionality loss vs. fighting glide-data-grid CSS. Removes 4-6h estimate risk.
- **v2.2 skip research**: loro-piana-aesthetic skill is the design source; Stitch mockups have validated the look; Streamlit CSS limits are implementation knowledge not domain research.

Full decision log: `.planning/PROJECT.md` Key Decisions table.

### Resolved Blockers

(None active)

### Open Blockers/Concerns

(None for v2.2 start)

## Session Continuity

Last session: 2026-05-22 — v2.2 milestone initialization
Stopped at: PROJECT.md + STATE.md updated; about to define requirements and spawn roadmapper
Resume file: None

---
*Last updated: 2026-05-22 after v2.2 milestone initialization*
