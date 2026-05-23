# Phase 9: Data visualization - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Restyle the results layer that renders inside the Phase 8 assistant-card DOM bay. Three deliverables:

1. An editorial HTML table as the **hero view** for query results (replacing the v2.1 native `st.dataframe` hero).
2. A single `st.expander("EXPAND · INTERACTIVE VIEW", expanded=False)` beneath every editorial table containing the native `st.dataframe` + CSV download — zero functionality loss vs v2.1.
3. A registered Altair theme (`loro_piana`) that themes chart **chrome** (title, axis labels, gridlines, no axis box) while data colors use a vibrant categorical palette tuned for legibility.

In scope: editorial table cell/row styling, truncation behavior, expander + CSV layout, Altair theme + chart restyle for bar/pie/line, empty-state and edge-case rendering inside the assistant card.

Out of scope (new capabilities — belong in other phases): sort/filter/inline-edit UI on the editorial table, multi-chart-type selection by user, drill-down/click-through interactions, new chart types (scatter, heatmap, area), saved-view/bookmark UX.

</domain>

<decisions>
## Implementation Decisions

### Spec deviations (user-approved)

Two of the decisions below deviate from the literal ROADMAP.md success-criteria text. Both were explicitly approved by the user during discuss-phase. Downstream agents (researcher, planner, verifier) should treat these as the authoritative spec for Phase 9:

- **Truncation threshold is `> 50` rows, NOT `> 1000`** — overrides DVZ-03's literal ">1000" trigger. Rationale: editorial table is the hero view, must always be scannable at a glance; anything beyond 50 rows belongs in the expander's native dataframe.
- **Chart data palette is vibrant categorical, NOT cashmere graduated** — overrides DVZ-04's literal `['#8B7355','#A89178','#C4B5A0','#D4C5B0','#E5DACB']` palette text. The Loro Piana aesthetic applies to chart **chrome** (titles, gridlines, axis labels, no axis box, fonts). Data colors are intentionally vibrant for legibility against the warm beige `#F5F0EB` and white card backgrounds.

The Phase 9 verifier should validate against THIS document's decisions, not the literal DVZ-03/DVZ-04 text. ROADMAP.md should be updated post-execution with a footnote referencing this CONTEXT.md.

### Text contrast (cross-cutting principle)

Default to **charcoal `#2C2420`** for all body text on the warm-beige and white card backgrounds. The MODE selector labels (AUTO / SQL / SEMANTIC) are the contrast reference — table cells must read as cleanly as those labels do. Muted gold `#B8A88A` and warm-gray `#6B5E52` are **decorative-only** — reserved for:

- The assistant-card provenance caption (`VIA AZURE · gpt-4`) — intentional de-emphasis, tiny text
- The Altair chart axis labels (Inter 11px) — secondary to the chart's data

Everywhere else in Phase 9, body and label text is charcoal.

### Editorial table — cell/row treatment

- **Per-column type styling** (all on warm-beige row bg, charcoal text unless noted):
  - `number` (INC IDs) → JetBrains Mono 13px charcoal
  - `opened_at` and other dates → italic Inter 14px charcoal
  - `priority` → italic Inter 15px charcoal (matches the spec-locked italic-priority requirement)
  - `short_description` → regular Inter 15px charcoal (hero content)
  - `similarity_score` → JetBrains Mono 13px charcoal, right-aligned (feels like a metric)
  - Other text columns → regular Inter 15px charcoal
  - Numeric columns → regular Inter 15px charcoal, right-aligned
- **Row hover** → subtle warm-beige tint `rgba(245, 240, 235, 0.5)`. No animation. Quietly interactive.
- **Sticky header** → **NO**. Editorial view is row-capped (see truncation); long scroll belongs in the expander.
- **Column widths** → auto, with `short_description` getting `min-width: 320px` to stay readable; numeric columns `width: max-content` to stay tight.
- **Long-text truncation** → `short_description` truncated at 140 chars with ellipsis; full text shown on hover via HTML `title` attribute (simple, accessible). The expander has untruncated.
- **Header treatment** (spec lock, preserved) → EB Garamond small-caps headers, warm-beige header bg, 16/24 cell padding, warm-beige row dividers.

### Truncation + row-count UX

- **Threshold** → editorial table truncates at `> 50` rows (see "Spec deviations" above).
- **Caption** (literal, spec-locked) → `SHOWING 50 OF <N> ROWS · EXPAND BELOW FOR FULL DATA`, rendered in small-caps tracked **charcoal**.
- **N formatting** → thousands separator with commas (`1,234`, not `1234`). Matches the existing app convention (`f"{x:,}"` is used throughout app.py).
- **Which 50 rows** → first 50 in the result's natural sort order (whatever the query produced — SQL `ORDER BY`, semantic similarity rank, etc.). No re-sampling, no "best of" logic — that would betray the query's intent.
- **Gradient fade at table bottom** → **NO**. The caption alone is the affordance. Editorial aesthetic prefers explicit text labels over implicit visual cues.
- **0 < rows ≤ 50** → full editorial table, no truncation caption.

### Chart palette + chart-type logic

- **Data palette (vibrant categorical, 5 colors)** — tuned to read against both warm beige `#F5F0EB` and white `#FFFFFF`:
  - Crimson `#C0392B`
  - Royal blue `#2E5BBA`
  - Forest green `#2E7D32`
  - Burnt orange `#E67E22`
  - Mustard yellow `#F39C12`
- **Palette cycling** → categories 6+ wrap through the palette in order.
- **Existing vibrant `CHART_COLORS` in src/chart_generator.py is DELETED** (not kept as fallback). The new vibrant palette lives in `src/ui/altair_theme.py`.
- **Bar orientation: HORIZONTAL** — flips existing vertical bars. Encoding changes from `x=category, y=value` to `x=value (quantitative), y=category (nominal)`. Matches the validated mockup at `.planning/design-mockups/02-results-chart.png`.
- **Sort** → preserve existing `sort="-y"` (descending by value) — in horizontal layout this stacks largest at top.
- **Bar value labels** → render the numeric value to the right of each bar via a layered Altair `text` mark (Inter 12px charcoal). Mockup shows this clearly.
- **Pie palette** → same 5 vibrant colors in order; for slices 6-10 (up to existing `MAX_PIE_SLICES=10`) wrap through palette.
- **Line chart** → single color crimson `#C0392B` for single-series lines (replaces single-color cashmere). Multi-series lines out of scope.
- **Legend rules** → no legend when y-axis labels already name the categories (the horizontal-bar case, e.g., bar by priority). Show legend ABOVE chart, right-aligned, small-caps Inter 11px warm-gray (no border) for pie charts and any future grouped/stacked bars.
- **Tooltip styling** → keep Altair's default tooltip rendering, theme only the font (Inter 12px charcoal on warm off-white bg). **Don't restyle the tooltip box itself** — over-customizing risks browser breakage. Pragmatic concession over aesthetic purity.
- **Chart chrome (theme, spec lock)** → EB Garamond 20px chart titles, Inter 11px warm-gray `#6B5E52` axis labels, warm-beige `#E8E0D8` 1px gridlines, no axis box stroke. This is the "Loro Piana" part of the theme.
- **Chart types in scope** → bar, pie, line only. No new types. Restyle existing `chart_generator.generate_chart`, don't expand its surface area.

### Expander + CSV layout (Claude's Discretion, but committed)

- **Label (spec-locked verbatim)** → `EXPAND · INTERACTIVE VIEW`, default state `expanded=False`.
- **Inside the expander** → `st.dataframe(df, use_container_width=True, hide_index=True)` followed by the CSV `st.download_button`. CSV button aligned LEFT beneath the dataframe (matches existing v2.1 layout — minimal change to a working pattern).
- **CSV button label** → `EXPORT CSV` (preserves the v2.1 string).

### Edge states

- **0-row result** → editorial empty state inside the assistant card. Structure:
  - Small-caps tracked label `NO RESULTS` in **charcoal** (NOT muted gold — contrast principle)
  - Body text `No incidents matched your query. Try a different search or mode.` in Inter 15px charcoal italic
  - Centered, 48px vertical padding
  - **No** editorial table, **no** expander, **no** chart
  - Replaces the current `_No results. Try different query or mode._` italic line in app.py `process_query`
- **1-row result** → render the editorial table normally. **No** flatten-to-definition-list. A third rendering path is hard to test and only marginally prettier. Consistency > cleverness.
- **1-data-point chart** → don't render the chart (preserves existing `MIN_ROWS_FOR_CHART = 2` guard). Restyle the existing `chart_feedback` message to the editorial pattern (small-caps `CHART UNAVAILABLE` charcoal label + italic charcoal body containing the feedback string). Logic unchanged.
- **0-row + chart was requested** → show the 0-row editorial empty state ONLY. Suppress the chart_feedback warning (redundant). Implementation note: in `display_results` (or its Phase 9 replacement), the 0-row branch must short-circuit before chart-feedback rendering.

### Claude's Discretion

These are areas where the user explicitly declined to predetermine the exact form; planner/executor has flexibility within the constraints already captured:

- Exact CSS class names for the editorial table (`.lp-editorial-table` or similar — pick something consistent with Phase 6 naming).
- Whether the new editorial-table CSS lives in `src/ui/css.py` (extending the single source of truth) or in a new sibling module — recommend extending `src/ui/css.py` to preserve the Phase 6 "single CSS source" decision unless there's a strong reason not to.
- Exact location of `_render_editorial_table(df)` — DVZ-01 says `src/utils.py`, but recommend revisiting: if it's the only Streamlit-touching function in utils, it may belong in a new `src/ui/results.py` module. Decision deferred to planner.
- Exact Altair theme registration mechanics (one-shot at import vs. context manager — pick whatever survives Streamlit reruns cleanly).
- How the expander chevron icon renders if Streamlit's Material Symbol look conflicts with Loro Piana — fix iff visible regression appears; don't pre-emptively restyle.

</decisions>

<specifics>
## Specific Ideas

- **Validated visual contract**: `.planning/design-mockups/02-results-chart.png` is the authoritative reference for the chart visual. Note: that mockup shows cashmere graduated bars — the user has since redirected to a vibrant palette. The mockup is still authoritative for everything ELSE (horizontal bars, value labels to the right, no axis box, serif chart title, layout inside the assistant card).
- **Contrast reference**: the MODE selector labels (`AUTO`, `SQL`, `SEMANTIC`) in the sidebar are the readability bar. Table body text must read at least as cleanly.
- **Existing app behavior to preserve**: the `display_results` function in `app.py:530` currently renders executive summary → chart → `st.dataframe`. Phase 9 replaces the `st.dataframe` block with the editorial table + expander pattern. The executive summary + chart rendering stays — just gets chart restyle from the new Altair theme.
- **Mono boundary already established**: Phase 6 locked JetBrains Mono to `code, pre, kbd, samp, .lp-mono, [data-testid="stCodeBlock"], [data-testid="stCode"]`. The editorial table's INC ID + similarity_score cells need to inherit mono — easiest via a `.lp-mono` class on those `<td>` elements rather than expanding the global mono selector.
- **Test invariants carry forward**: The 22 v2.1 Phase 5 UI tests in `tests/test_phase5_ui.py` must stay green. Phase 9 does not touch `_render_provenance_caption` — only the surrounding card content (executive summary, table, chart) is restyled.

</specifics>

<deferred>
## Deferred Ideas

(None surfaced during discussion — user direction was decisive and scope stayed within the boundary.)

Potential future-phase candidates if they come up later: sort/filter UI on the editorial table, click-to-drill-down on chart segments, saved-view bookmarks, additional chart types (scatter/heatmap/area), CSV export from within the editorial table (currently only in expander), copy-to-clipboard affordance for individual cells.

</deferred>

---

*Phase: 09-data-visualization*
*Context gathered: 2026-05-23*
