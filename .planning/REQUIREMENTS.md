# Requirements: snow_query v2.2 — SNOWGREP Visual Revamp (Loro Piana)

**Defined:** 2026-05-22
**Core Value:** Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.
**Milestone goal:** Replace the brutalist terminal CSS with an editorial Loro Piana quiet luxury aesthetic across all screens, without touching v2.1 LLM behavior or losing any existing functionality.

**Design reference:**
- Three Stitch mockups in `.planning/design-mockups/` (00-splash-helix.png, 01-main-chat.png, 02-results-chart.png)
- Live Stitch project: https://stitch.withgoogle.com/projects/11615568135320819515
- Design system: `loro-piana-aesthetic` skill — palette, tokens, components, makeover-checklist

## v1 Requirements

### Foundation (FND) — Design tokens, fonts, palette

- [ ] **FND-01**: Google Fonts imports for EB Garamond (weights 300, 400) and Inter (weights 400, 500) are added to the global CSS injection in `app.py`. JetBrains Mono retained for code/data only.
- [ ] **FND-02**: Streamlit base CSS color variables overridden via `:root` rules — `--background-color: #F5F0EB` (warm off-white), `--primary-color: #8B7355` (cashmere brown), `--text-color: #2C2420` (charcoal), `--secondary-background-color: #FFFFFF` (white surface). No `#0a0a0a` brutalist background appears anywhere in the rendered DOM.
- [ ] **FND-03**: Existing brutalist CSS block (`app.py:44-` to closing `</style>`) is replaced with a Loro Piana CSS module (`src/ui/css.py` or equivalent) that exports a single `LORO_PIANA_CSS` constant injected once via `st.markdown(..., unsafe_allow_html=True)`. No `font-family: 'JetBrains Mono', 'Courier New', monospace` on the global `.stApp` selector.
- [ ] **FND-04**: All section labels render in Inter weight 500, UPPERCASE, `letter-spacing: 0.1em`, 11-12px, color `#6B5E52` (warm gray) — small-caps boutique-signage style. Verified via DOM grep for the label CSS class.
- [ ] **FND-05**: Page chrome refresh — `st.set_page_config(page_icon=...)` value changed from brutalist `▣` to a restrained mark (option: EB Garamond italic "S", or single warm-beige circle glyph). `page_title="SNOWGREP"` preserved.
- [ ] **FND-06**: All buttons (`st.button`, `st.chat_input` submit) render with cashmere brown `#8B7355` background, white text, 4px border-radius, uppercase tracked label (`letter-spacing: 0.1em`). Verified on at least 3 distinct button instances.

### Splash (SPL) — Boot animation

- [ ] **SPL-01**: `src/ui/splash.py` exports a `render_splash()` function that emits a self-contained `streamlit.components.v1.html(...)` block with the helix-motif CSS keyframes — two diagonal streams of INC IDs animating slowly with opacity fades, EB Garamond wordmark anchored center in protected whitespace exclusion zone.
- [ ] **SPL-02**: Splash renders in an `st.empty()` placeholder at the top of `main()` and clears once `data_loaded` AND `embeddings_ready` are both true in `st.session_state`. Total visible duration capped at 4 seconds maximum even if data load is faster (anti-flash).
- [ ] **SPL-03**: Helix animation respects `prefers-reduced-motion: reduce` — when set, INC IDs fade in/out at fixed positions instead of translating (no horizontal motion). Wordmark and labels render identically in both modes.
- [ ] **SPL-04**: Splash is shown ONCE per browser session (tracked via `st.session_state['_splash_shown']` flag). Subsequent reruns within the session skip the splash. New browser session re-shows it.

### Sidebar (SBR) — Editorial sidebar restyle

- [ ] **SBR-01**: Sidebar background is `#F5F0EB` (warm off-white) with 320px fixed width. "SNOWGREP" wordmark renders at top in EB Garamond 28px weight 300, color `#2C2420`, `letter-spacing: 0.02em`.
- [ ] **SBR-02**: Section headers — DATA, EMBEDDINGS, LLM PROVIDER, MODE — render as small-caps Inter weight 500, `letter-spacing: 0.1em`, 11-12px, color `#6B5E52`. Verbatim string match required.
- [ ] **SBR-03**: MODE selector replaces the existing `st.selectbox` with a pill-style toggle row — three buttons "AUTO" / "SQL" / "SEMANTIC". Selected pill has cashmere brown `#8B7355` background + white text; unselected have transparent background + warm-gray text. Selection persists in `st.session_state["query_mode"]` exactly as before (no behavior change).
- [ ] **SBR-04**: EMBEDDINGS status renders as a pill — "READY" in sage tint (`#8A9A7D` at 10% opacity background, `#8A9A7D` text) when embeddings exist; "MISSING" in terracotta tint (`#A67866` at 10% opacity bg, `#A67866` text) when not.
- [ ] **SBR-05**: LLM PROVIDER dropdown (`st.selectbox` labeled "LLM provider") restyled — thin bottom border only (`border-bottom: 1px solid #E8E0D8`), no full box, white background. Active model name renders directly beneath in muted gold `#B8A88A` Inter 11px tracked. The locked v2.1 label string "LLM provider" stays verbatim (Phase 5 test asserts this).
- [ ] **SBR-06**: Provider-warning state (missing env vars) restyles — warning box with warm-beige background `#F5F0EB`, terracotta `#A67866` thin left border (3px), `WARNING — provider not configured` heading in small-caps tracked, body copy in Inter `#2C2420`. The locked v2.1 string "QUERY DISABLED — see sidebar warning" placeholder is preserved verbatim on `st.chat_input` when blocked.

### Main Panel (MAIN) — Chat + page chrome

- [ ] **MAIN-01**: Page header renders "Incident Intelligence" in EB Garamond 36px weight 300 charcoal, with subtitle "Ask in natural language. All data stays local." in Inter 15px warm-gray `#6B5E52` directly below. No brutalist all-caps wordmark in the main area.
- [ ] **MAIN-02**: User messages in chat history render as warm-beige `#F5F0EB` cards with 4px border-radius, aligned right (max-width 70%, `margin-left: auto`). No avatar / role label.
- [ ] **MAIN-03**: Assistant messages render as white `#FFFFFF` cards with `1px solid #E8E0D8` border, 4px border-radius, aligned left (max-width 85%). Soft warm shadow `0 1px 2px rgba(139,115,85,0.06)` permitted; no harsh box-shadow.
- [ ] **MAIN-04**: Provenance caption (`_render_provenance_caption(provider, model)`) restyles to render `VIA <PROVIDER> · <model>` in Inter weight 500 small-caps `letter-spacing: 0.1em`, color muted gold `#B8A88A`, 11px. **The v2.1 invariant carries forward: the helper MUST NOT read `st.session_state` — history messages keep original provenance after mid-session provider switches.** AST-based regression test in `tests/test_phase5_ui.py` must still pass.
- [ ] **MAIN-05**: `st.chat_input` restyled — thin bottom border only (`border-bottom: 1px solid #E8E0D8`), placeholder "Ask anything about your incidents…" in Inter 15px warm-gray. Submit button renders the cashmere brown "ASK" pattern from FND-06.
- [ ] **MAIN-06**: The v2.1 chat-input blocked state preserved verbatim — when `_llm_provider_blocked=True`, `st.chat_input(disabled=True)` with placeholder "QUERY DISABLED — see sidebar warning". Locked string from v2.1 Phase 5 tests.

### Data Visualization (DVZ) — Editorial dataframe + charts

- [ ] **DVZ-01**: New helper `_render_editorial_table(df: pd.DataFrame) -> str` in `src/utils.py` returns an HTML table string with: italic priority labels in cells where the column name matches "priority" (case-insensitive), warm-beige `#E8E0D8` 1px row dividers, no zebra stripes, no vertical column borders, EB Garamond serif column headers in small-caps tracked, generous cell padding (16px vertical, 24px horizontal), warm-beige background only on header row.
- [ ] **DVZ-02**: Every assistant response that returns a DataFrame renders the editorial HTML table FIRST (as the hero view, matches mockup), followed by a single `st.expander("EXPAND · INTERACTIVE VIEW", expanded=False)` containing the full native `st.dataframe(df, use_container_width=True, hide_index=True)` plus a CSV download button. Zero functionality loss vs. v2.1.
- [ ] **DVZ-03**: When the result DataFrame has >1000 rows, the editorial HTML table shows only the first 50 rows with a small-caps tracked caption beneath: "SHOWING 50 OF <N> ROWS  ·  EXPAND BELOW FOR FULL DATA". The `st.dataframe` inside the expander always renders the full frame.
- [ ] **DVZ-04**: New `src/ui/altair_theme.py` registers a custom Altair theme `loro_piana` (via `alt.themes.register` + `alt.themes.enable`) with: cashmere graduated palette for bar marks (`['#8B7355', '#A89178', '#C4B5A0', '#D4C5B0', '#E5DACB']`), warm-beige `#E8E0D8` gridlines at 1px, no axis box stroke, EB Garamond chart titles 20px weight 300 color `#2C2420`, Inter axis labels 11px warm-gray `#6B5E52`.
- [ ] **DVZ-05**: All chart rendering call sites (`src/chart_generator.py::generate_chart`) consume the new theme — verified by removing `theme="dark"` references and confirming no Altair chart renders with a dark background or default colors. Single-series charts have no legend (`legend=None`).

### Polish (POL) — Edge states + indicators

- [ ] **POL-01**: Empty state (no CSV loaded) renders an editorial centered card in the main panel — EB Garamond 24px "No data loaded" heading, Inter 15px warm-gray subtitle "Upload incidents.csv from the sidebar to begin.", and a hairline divider beneath. No brutalist "DATA INGEST REQUIRED" message.
- [ ] **POL-02**: Loading spinners — `st.spinner` calls swap to a small-caps tracked text indicator. Replace "Generating response..." → "ANALYZING…"; replace "Loading embeddings..." → "BUILDING EMBEDDINGS…"; replace "Executing query..." → "QUERYING…". Inter weight 500 11px muted gold `#B8A88A` tracked wide.
- [ ] **POL-03**: Error rendering — `QueryError` / `LLMError` surface in the assistant card with: terracotta `#A67866` left border 3px, "ERROR" small-caps tracked label at top, error message in Inter weight 400 color `#2C2420`, no red brutalist banner.
- [ ] **POL-04**: Toast / notification rendering — any `st.success` / `st.error` / `st.warning` calls restyle to the Loro Piana palette via CSS overrides. No browser-default colors leak through.

### Documentation (DOC) — User-facing docs

- [ ] **DOC-01**: USER_GUIDE.md gains a new section "VISUAL REFRESH (v2.2)" near the top with: one-paragraph summary of the aesthetic change, "What changed" bullet list (splash, sidebar style, editorial table, expandable interactive view, restyled charts), "What did NOT change" reassurance list (all v2.1 functionality, locked UI strings, LLM behavior, data privacy). Version stamp footer bumped from "v2.1" to "v2.2".
- [ ] **DOC-02**: README.md gains a small "Screenshots" subsection near the top linking to `.planning/design-mockups/` (or moved to `docs/screenshots/` as part of this milestone). Reference to the loro-piana-aesthetic design system noted in passing — does not duplicate it.

### Testing (TST) — Regression coverage

- [ ] **TST-01**: All 22 tests in `tests/test_phase5_ui.py` (v2.1 Phase 5 acceptance gate) stay green. The AST-based session_state-invariant test on `_render_provenance_caption` is load-bearing. Combined Phase 1+2+3+4+5 suite remains 91/91.
- [ ] **TST-02**: New `tests/test_phase6_visual.py` acceptance gate proving v2.2 success criteria with zero live Streamlit / HTTP / LLM: CSS string presence checks (EB Garamond import, Inter import, palette tokens `#8B7355` / `#F5F0EB` / `#2C2420`); absence checks (no `#0a0a0a`, no `JetBrains Mono` on `.stApp`); helper function signature checks (`_render_editorial_table`, `render_splash`, Altair theme `loro_piana` registered).
- [ ] **TST-03**: Accessibility contrast check — programmatic verification that `#2C2420` on `#F5F0EB` passes WCAG AA for body text (4.5:1 minimum) and `#6B5E52` on `#F5F0EB` passes AA for large text only (3:1 minimum, NOT small body). Test fails with clear message if any palette color used outside its valid contrast role.

## v2 Requirements (deferred)

Tracked but not in current roadmap.

### Theming (THM)

- **THM-01**: Theme toggle in sidebar to switch between Loro Piana (default) and brutalist (preserved as alternate). Needs decision on whether to keep brutalist CSS as a callable alternate or fully retire it.
- **THM-02**: Dark-mode luxury variant — same warm earth tones at lower luminance for low-light operator environments.

### Microinteractions (MIC)

- **MIC-01**: Card hover states — subtle warm-beige shadow lift on assistant message cards.
- **MIC-02**: Provider switch transition — fade between sidebar widget states when provider dropdown changes.

### Charts (CHT)

- **CHT-01**: Sparkline column in editorial table for time-series fields.
- **CHT-02**: Interactive crossfilter between editorial table and chart (click a bar → filter the table).

## Out of Scope

Explicitly excluded for v2.2. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Backend / LLM behavior changes | v2.2 is presentation only; LLM seam from v2.1 stays untouched |
| Mobile responsive layout | Streamlit is desktop-first; no in-house mobile use case yet |
| Backwards-compatibility shim for brutalist theme | Theme toggle is v2 work (THM-01); v2.2 replaces brutalist cleanly |
| Porting `app_brutalist.py` / `fixedapp.py` / `designui.py` variants | They are experimental siblings; not in scope |
| Streamlit version upgrade | Stays on current pin; CSS selectors target current DOM only |
| Custom Streamlit components (React) for widgets | Native `st.*` + CSS injection is sufficient; building custom components is 10x the scope |
| New LLM call sites or routing changes | v2.1 architecture is locked |
| Animations beyond the splash | Splash is the one motion concession to "quiet luxury"; everything else is still |
| Font subsetting / self-hosted fonts | Google Fonts CDN is acceptable; subsetting is a perf-pass for v2 |
| Theme tokens as a published design system module | Keep tokens inline in `src/ui/css.py`; export as a package only when a second app needs them |

## Traceability

Phases mapped during roadmap creation 2026-05-22.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01      | 6     | Complete |
| FND-02      | 6     | Complete |
| FND-03      | 6     | Complete |
| FND-04      | 6     | Complete |
| FND-05      | 6     | Complete |
| FND-06      | 6     | Complete |
| SPL-01      | 7     | Pending |
| SPL-02      | 7     | Pending |
| SPL-03      | 7     | Pending |
| SPL-04      | 7     | Pending |
| SBR-01      | 8     | Pending |
| SBR-02      | 8     | Pending |
| SBR-03      | 8     | Pending |
| SBR-04      | 8     | Pending |
| SBR-05      | 8     | Pending |
| SBR-06      | 8     | Pending |
| MAIN-01     | 8     | Pending |
| MAIN-02     | 8     | Pending |
| MAIN-03     | 8     | Pending |
| MAIN-04     | 8     | Pending |
| MAIN-05     | 8     | Pending |
| MAIN-06     | 8     | Pending |
| DVZ-01      | 9     | Pending |
| DVZ-02      | 9     | Pending |
| DVZ-03      | 9     | Pending |
| DVZ-04      | 9     | Pending |
| DVZ-05      | 9     | Pending |
| POL-01      | 10    | Pending |
| POL-02      | 10    | Pending |
| POL-03      | 10    | Pending |
| POL-04      | 10    | Pending |
| DOC-01      | 11    | Pending |
| DOC-02      | 11    | Pending |
| TST-01      | 11    | Pending |
| TST-02      | 11    | Pending |
| TST-03      | 11    | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-22. Traceability updated 2026-05-22 after roadmap revision (Phases 8+9 merged into single Phase 8).*
