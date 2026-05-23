# Roadmap: snow_query

## Milestones

- ✅ **v2.1 Multi-Provider LLM Integration** — Phases 1-5 (shipped 2026-05-22) — see [milestones/v2.1-ROADMAP.md](milestones/v2.1-ROADMAP.md)
- 🔄 **v2.2 SNOWGREP Visual Revamp (Loro Piana)** — Phases 6-11 (in progress, started 2026-05-22)

## Overview (v2.2)

Replace the brutalist terminal CSS with an editorial Loro Piana quiet luxury aesthetic across every screen — splash, sidebar, main chat, results, and charts — without touching v2.1 LLM behavior and without losing any v2.1 functionality.

The six-phase structure follows a strict **foundation → screen restyle → results layer → polish → documentation/gate** order. Phase 6 lands the design tokens, fonts, palette, and global CSS module that every subsequent phase consumes. Phase 7 lands the splash screen (depends on Phase 6 fonts). Phase 8 restyles the sidebar AND main panel together — disjoint DOM regions sharing the same CSS module, naturally parallelizable inside the phase as two waves. Phase 9 layers the editorial dataframe + Altair theme onto the main panel (depends on Phase 8 assistant-card context). Phase 10 polishes edge states (empty state, loading, error, provider warning) across all screens. Phase 11 closes documentation and locks the acceptance gate — including the load-bearing invariant that all 22 v2.1 Phase 5 UI tests stay green throughout.

Three Stitch mockups (`.planning/design-mockups/00-splash-helix.png`, `01-main-chat.png`, `02-results-chart.png`) are the visual contract; the `loro-piana-aesthetic` skill is the design system source.

**v2.1 invariants that v2.2 work MUST preserve:**

1. `_render_provenance_caption(provider, model)` MUST NOT read `st.session_state` — AST-based regression test locks this. Phase 8 restyle (MAIN-04) only changes CSS, not the helper's read sources.
2. Locked v2.1 UI strings stay verbatim: `"LLM provider"` (selectbox label), `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"QUERY DISABLED — see sidebar warning"`. Phase 5 has 22 tests asserting these; Phase 11 gates v2.2 with them still green.
3. All 91 v2.1 tests stay green throughout v2.2.

## Phases (v2.2)

- [x] Phase 6: Foundation — CSS module + design tokens + page chrome (6 requirements) ✓ 2026-05-22
- [ ] Phase 7: Splash screen — Helix-motif boot animation (4 requirements)
- [ ] Phase 8: Screen restyle — Sidebar + main panel + chat editorial pass (12 requirements)
- [ ] Phase 9: Data visualization — Editorial HTML table + collapsible interactive view + Altair theme (5 requirements)
- [ ] Phase 10: Polish + edge states — Empty state, loading indicators, error rendering, toasts (4 requirements)
- [ ] Phase 11: Documentation + acceptance gate — USER_GUIDE/README + visual regression test suite + WCAG check (5 requirements)

## Phase Details

### Phase 6: Foundation

**Goal**: Replace the brutalist global CSS with a Loro Piana CSS module exposing design tokens (fonts, palette, spacing) and refresh page chrome. Every subsequent phase consumes this foundation; nothing else in v2.2 is unblocked until it lands.

**Depends on**: Nothing (first v2.2 phase; v2.1 is shipped)

**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06

**Success Criteria**:

1. Opening the app in a browser shows a warm off-white background (`#F5F0EB`) — DOM inspection confirms no `#0a0a0a` brutalist background anywhere in the rendered tree, and the body computed font-family is `Inter` (not `JetBrains Mono`).
2. The global stylesheet contains Google Fonts imports for EB Garamond (weights 300, 400) and Inter (weights 400, 500); JetBrains Mono is retained for code blocks/data only.
3. CSS is sourced from a single module (`src/ui/css.py` or equivalent) exporting one `LORO_PIANA_CSS` constant injected once via `st.markdown(..., unsafe_allow_html=True)` from `app.py` — no inline `<style>` strings remain in `app.py`.
4. A test button rendered via `st.button` shows cashmere brown `#8B7355` background, white text, 4px border-radius, uppercase tracked label (`letter-spacing: 0.1em`) — verified on at least three distinct button instances.
5. Browser tab shows the refreshed `page_icon` (restrained mark, not brutalist `▣`); `page_title="SNOWGREP"` is preserved.

**Plans:** 3 plans in 3 waves

Plans:
- [ ] 06-PLAN-01-create-css-module.md — Create `src/ui/__init__.py` + `src/ui/css.py` exporting `LORO_PIANA_TOKENS` dict and `LORO_PIANA_CSS` string (Wave 1)
- [ ] 06-PLAN-02-wire-app-and-page-chrome.md — Delete brutalist CSS from `app.py`, inject `LORO_PIANA_CSS` once, flip `page_icon` from `▣` to `✦` (Wave 2)
- [ ] 06-PLAN-03-smoke-render-verification.md — Static checks + visual checkpoint confirming warm bg, Inter body font, three cashmere buttons, `✦` favicon (Wave 3)

### Phase 7: Splash screen

**Goal**: Add the helix-motif boot splash that displays the EB Garamond wordmark over two slowly-animating diagonal streams of INC IDs while data + embeddings load, then clears once both are ready. Single-shot per browser session, reduced-motion compliant.

**Depends on**: Phase 6 (consumes EB Garamond font import and palette tokens)

**Requirements**: SPL-01, SPL-02, SPL-03, SPL-04

**Success Criteria**:

1. Opening a fresh browser session shows the splash with EB Garamond wordmark center-anchored over two diagonal animated streams of INC IDs; splash is rendered via `streamlit.components.v1.html(...)` from `src/ui/splash.py::render_splash()`.
2. Splash clears automatically the moment `data_loaded` AND `embeddings_ready` are both true in `st.session_state`, and never persists beyond 4 seconds even when data load is faster (anti-flash cap).
3. Setting the browser's `prefers-reduced-motion: reduce` swaps the helix translation for fixed-position opacity fades — INC IDs do not move horizontally; wordmark and labels render identically in both modes.
4. Reloading the page within the same browser session (`st.session_state['_splash_shown']` already true) skips the splash and goes straight to the main app; opening a new browser session shows it again.

**Plans-TBD**: To be decomposed by `/gsd:plan-phase 7`.

### Phase 8: Screen restyle (sidebar + main panel + chat)

**Goal**: Restyle the entire visible surface — sidebar AND main panel — to the editorial Loro Piana pattern in one phase. Sidebar gets small-caps tracked labels, MODE pill toggle, EMBEDDINGS status pill, bottom-border-only LLM PROVIDER dropdown, restyled provider warning. Main panel gets serif page header, warm-beige user message cards (right-aligned), white assistant cards with thin border (left-aligned), restyled per-message provenance caption, restyled chat input with cashmere ASK submit, and preserves the v2.1 blocked-state contract verbatim. Behavior is byte-identical to v2.1 across both regions (session_state keys, query_mode persistence, provider selection wiring, blocked chat_input placeholder). The sidebar and main panel touch disjoint regions of `app.py` and consume the Phase 6 tokens read-only — the two natural waves inside this phase can be executed in parallel by `/gsd:execute-phase 8`.

**Depends on**: Phase 6 (tokens + CSS module)

**Requirements**: SBR-01, SBR-02, SBR-03, SBR-04, SBR-05, SBR-06, MAIN-01, MAIN-02, MAIN-03, MAIN-04, MAIN-05, MAIN-06 (12 requirements)

**Success Criteria**:

1. **Sidebar — structure + labels**: renders with `#F5F0EB` background, 320px fixed width, "SNOWGREP" wordmark at top in EB Garamond 28px weight 300 charcoal; the four section headers DATA, EMBEDDINGS, LLM PROVIDER, MODE render as small-caps Inter 500 11-12px warm-gray `#6B5E52` with `letter-spacing: 0.1em` (verbatim string match).
2. **Sidebar — controls**: MODE is a three-button pill row (AUTO / SQL / SEMANTIC) that updates `st.session_state["query_mode"]` to the exact same value the legacy `st.selectbox` produced; EMBEDDINGS pill renders sage tint "READY" or terracotta tint "MISSING"; LLM PROVIDER `st.selectbox` shows bottom-border-only style with locked label "LLM provider" verbatim and active model in muted gold beneath; missing-env warning renders with warm-beige bg + terracotta 3px left border + small-caps "WARNING — provider not configured".
3. **Main panel — header + chat cards**: "Incident Intelligence" in EB Garamond 36px weight 300 charcoal page header with "Ask in natural language. All data stays local." subtitle in Inter 15px warm-gray; user messages render as warm-beige `#F5F0EB` cards aligned right (max-width 70%, `margin-left: auto`, 4px radius, no avatar / role label); assistant messages render as white cards with `1px solid #E8E0D8` border aligned left (max-width 85%, soft warm shadow permitted, no harsh box-shadow).
4. **Main panel — provenance + invariant**: caption above each assistant message renders as `VIA <PROVIDER> · <model>` in Inter 500 small-caps 11px muted gold `#B8A88A`; switching providers mid-session and re-rendering history keeps the ORIGINAL provenance on historical messages — the v2.1 AST-based test in `tests/test_phase5_ui.py` still passes (helper never reads `st.session_state`).
5. **Main panel — chat input**: `st.chat_input` shows thin bottom-border-only style with placeholder "Ask anything about your incidents…" and a cashmere ASK submit; when `_llm_provider_blocked=True`, `st.chat_input(disabled=True)` renders the locked v2.1 placeholder "QUERY DISABLED — see sidebar warning" verbatim.

**Plans-TBD**: To be decomposed by `/gsd:plan-phase 8`. Expected wave structure: Wave A = sidebar (SBR-01..06), Wave B = main panel (MAIN-01..06) — independent, parallelizable.

### Phase 9: Data visualization

**Goal**: Replace the v2.1 native `st.dataframe` hero with an editorial HTML table as the primary view, while preserving full interactivity behind a single `st.expander` (zero functionality loss). Register a custom Altair theme so all charts render in cashmere palette / no axis box / warm gridlines / EB Garamond titles.

**Depends on**: Phase 8 (the editorial table renders inside the assistant card pattern from MAIN-03)

**Requirements**: DVZ-01, DVZ-02, DVZ-03, DVZ-04, DVZ-05

**Success Criteria**:

1. Submitting a query that returns a 12-row DataFrame renders an editorial HTML table as the hero view via `_render_editorial_table(df)` in `src/utils.py` — italic priority labels, warm-beige row dividers, EB Garamond small-caps headers, generous cell padding (16/24), warm-beige header background only.
2. A single `st.expander("EXPAND · INTERACTIVE VIEW", expanded=False)` appears directly beneath every editorial table; expanding it reveals the native `st.dataframe(df, use_container_width=True, hide_index=True)` plus a CSV download button — zero functionality loss versus v2.1.
3. Submitting a query that returns >1000 rows renders only the first 50 rows in the editorial HTML view with a small-caps tracked caption beneath ("SHOWING 50 OF <N> ROWS · EXPAND BELOW FOR FULL DATA"); the expander still contains the full DataFrame.
4. A new module `src/ui/altair_theme.py` registers and enables a `loro_piana` Altair theme with cashmere graduated bar palette (`['#8B7355', '#A89178', '#C4B5A0', '#D4C5B0', '#E5DACB']`), warm-beige `#E8E0D8` 1px gridlines, no axis box stroke, EB Garamond 20px chart titles, Inter 11px warm-gray axis labels.
5. Every Altair chart rendered by `src/chart_generator.py::generate_chart` uses the new theme — DOM inspection confirms no dark background, no default Altair colors; single-series charts have no legend.

**Plans-TBD**: To be decomposed by `/gsd:plan-phase 9`.

### Phase 10: Polish + edge states

**Goal**: Restyle every remaining edge state — empty state (no CSV), loading indicators, error rendering, and toast/notification calls — to the Loro Piana palette and small-caps tracked label pattern. Closes the visual surface area; after this phase nothing brutalist leaks through.

**Depends on**: Phases 6, 8, 9 (edge states span the sidebar, main panel, and data layers)

**Requirements**: POL-01, POL-02, POL-03, POL-04

**Success Criteria**:

1. Opening the app with no CSV loaded shows a centered editorial card with "No data loaded" in EB Garamond 24px and "Upload incidents.csv from the sidebar to begin." in Inter 15px warm-gray — no brutalist "DATA INGEST REQUIRED" copy anywhere.
2. Triggering any LLM-bound action shows a small-caps tracked indicator instead of Streamlit's default spinner: "ANALYZING…" while a response generates, "BUILDING EMBEDDINGS…" while embeddings build, "QUERYING…" while a query executes — Inter 500 11px muted gold with wide tracking.
3. Forcing a `QueryError` or `LLMError` (e.g. via missing env vars + retry) renders the message in the assistant card with a terracotta 3px left border, "ERROR" small-caps tracked label at top, and the error text in Inter 400 charcoal — no red brutalist banner.
4. `st.success` / `st.error` / `st.warning` calls anywhere in the app render with Loro Piana palette colors via CSS overrides — no browser-default toast colors leak through.

**Plans-TBD**: To be decomposed by `/gsd:plan-phase 10`.

### Phase 11: Documentation + acceptance gate

**Goal**: Close the milestone with user-facing documentation updates (USER_GUIDE, README), a visual-regression test module that locks v2.2 against silent revert, and a programmatic WCAG-AA contrast verification. The v2.1 Phase 5 acceptance suite (22 tests, locked UI strings) MUST remain green.

**Depends on**: Phases 6, 7, 8, 9, 10 (gate validates the assembled product)

**Requirements**: DOC-01, DOC-02, TST-01, TST-02, TST-03

**Success Criteria**:

1. `pytest tests/test_phase5_ui.py` passes 22/22 — every locked v2.1 UI string ("LLM provider", "Azure OpenAI", "Anthropic Claude (MGTI)", "QUERY DISABLED — see sidebar warning") still asserts true, and the AST-based `_render_provenance_caption`-does-not-read-`st.session_state` invariant test still passes.
2. `pytest tests/test_phase6_visual.py` (new) passes — asserts CSS presence of EB Garamond + Inter imports and palette tokens (`#8B7355`, `#F5F0EB`, `#2C2420`); asserts CSS absence of `#0a0a0a` and `JetBrains Mono` on `.stApp`; asserts presence of `_render_editorial_table`, `render_splash`, and registered `loro_piana` Altair theme. Zero live Streamlit / HTTP / LLM.
3. WCAG-AA contrast check runs and passes — `#2C2420` on `#F5F0EB` passes 4.5:1 for body text; `#6B5E52` on `#F5F0EB` passes 3:1 for large text only (with a guard error if any palette color is used outside its valid contrast role).
4. `USER_GUIDE.md` contains a new "VISUAL REFRESH (v2.2)" section near the top with the aesthetic-summary paragraph, "What changed" bullet list (splash, sidebar, editorial table, expandable interactive view, restyled charts), "What did NOT change" reassurance list (v2.1 functionality, locked UI strings, LLM behavior, data privacy), and the version-stamp footer is bumped from "v2.1" to "v2.2".
5. `README.md` contains a small "Screenshots" subsection near the top linking to `.planning/design-mockups/` (or `docs/screenshots/` if moved), with a pass-through reference to the `loro-piana-aesthetic` design system.

**Plans-TBD**: To be decomposed by `/gsd:plan-phase 11`.

## Phases (v2.1, archived)

<details>
<summary>✅ v2.1 Multi-Provider LLM Integration (Phases 1-5) — SHIPPED 2026-05-22</summary>

- [x] Phase 1: Abstraction Seam (3/3 plans) — completed 2026-05-19
- [x] Phase 2: Azure Extraction + Parity Gate (4/4 plans) — completed 2026-05-20
- [x] Phase 3: Anthropic MGTI Adapter (4/4 plans) — completed 2026-05-21
- [x] Phase 4: Strict-Tools + Smoke Test (4/4 plans) — completed 2026-05-21
- [x] Phase 5: Sidebar UI Toggle + Documentation (5/5 plans) — completed 2026-05-22

Full details: [milestones/v2.1-ROADMAP.md](milestones/v2.1-ROADMAP.md)
Audit report: [milestones/v2.1-MILESTONE-AUDIT.md](milestones/v2.1-MILESTONE-AUDIT.md)

</details>

## Progress

| Phase                                | Milestone | Plans Complete | Status      | Completed  |
| ------------------------------------ | --------- | -------------- | ----------- | ---------- |
| 1. Abstraction Seam                  | v2.1      | 3/3            | Complete    | 2026-05-19 |
| 2. Azure Extraction + Parity         | v2.1      | 4/4            | Complete    | 2026-05-20 |
| 3. Anthropic MGTI Adapter            | v2.1      | 4/4            | Complete    | 2026-05-21 |
| 4. Strict-Tools + Smoke Test         | v2.1      | 4/4            | Complete    | 2026-05-21 |
| 5. Sidebar UI Toggle + Docs          | v2.1      | 5/5            | Complete    | 2026-05-22 |
| 6. Foundation (CSS + tokens)         | v2.2      | 3/3            | Complete    | 2026-05-22 |
| 7. Splash screen                     | v2.2      | 0/TBD          | Not started | —          |
| 8. Screen restyle (sidebar + main)   | v2.2      | 0/TBD          | Not started | —          |
| 9. Data visualization                | v2.2      | 0/TBD          | Not started | —          |
| 10. Polish + edge states             | v2.2      | 0/TBD          | Not started | —          |
| 11. Documentation + acceptance gate  | v2.2      | 0/TBD          | Not started | —          |

## Coverage (v2.2)

- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

Detailed traceability lives in `REQUIREMENTS.md` Traceability section.

---
*Last updated: 2026-05-22 after Phase 6 (Foundation) execution complete — all FND-01..06 verified, 5/5 success criteria PASS.*
