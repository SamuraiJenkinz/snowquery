# Phase 8: Screen restyle (sidebar + main panel + chat) - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Restyle every visible surface — sidebar AND main panel — to the editorial Loro Piana pattern in one phase. Sidebar gets small-caps tracked labels, MODE pill toggle, EMBEDDINGS status pill, bottom-border-only LLM PROVIDER dropdown, restyled provider warning. Main panel gets serif page header, warm-beige user message cards (right-aligned), white assistant cards with thin border (left-aligned), restyled per-message provenance caption, restyled chat input with cashmere ASK submit, and preserves the v2.1 blocked-state contract verbatim.

**Behavior is byte-identical to v2.1** across both regions (session_state keys, query_mode persistence, provider selection wiring, blocked chat_input placeholder). Only CSS + DOM structure changes.

Sidebar and main panel touch disjoint regions of `app.py` and consume the Phase 6 [[loro-piana-css-module]] read-only → the two natural waves inside this phase (Wave A: sidebar SBR-*, Wave B: main panel MAIN-*) can run in parallel under `/gsd:execute-phase 8`.

**Out of scope (defer to other phases):**
- Editorial HTML table + Altair theme → Phase 9 (DVZ-*)
- Empty-state-no-CSV editorial card + loading indicators + error rendering + toast styling → Phase 10 (POL-*)
- USER_GUIDE/README updates + visual regression suite + WCAG check → Phase 11 (DOC-*, TST-*)

</domain>

<decisions>
## Implementation Decisions

### Pill/button interaction states (MODE pill + cashmere buttons)

Three-button MODE pill row (AUTO / SQL / SEMANTIC):
- **Selected pill**: filled `#8B7355` cashmere bg + white text + no shadow + no border
- **Unselected pill**: transparent bg + charcoal `#2C2420` text + 1px `#E8E0D8` hairline border
- **Hover (unselected)**: bg shifts to warm-beige `#EDE6DD`, text stays charcoal, border stays hairline
- **Hover (selected)**: no change (already strong visual)
- **Focus (any)**: existing `--lp-shadow-focus` warm focus ring from `src/ui/css.py`
- **Blocked state** (when `st.session_state["_llm_provider_blocked"] == True`): all three pills go `opacity: 0.5` + `cursor: not-allowed` — mirrors the existing disabled cashmere button pattern in `css.py` lines 334-343, and matches the blocked `st.chat_input` contract

Cashmere buttons (UNLOCK UPLOAD, REPLACE, APPEND, LOCK UPLOAD, REBUILD, UPDATE, ASK submit, CLEAR HISTORY) inherit the existing `css.py` rules (lines 287-343) — no changes needed at this layer. Phase 8 only adds the pill-specific selectors.

The MODE pill is the load-bearing decision here: it replaces the existing `st.selectbox` in `app.py:690-697` AND must write `st.session_state["query_mode"]` to the same string values the legacy selectbox produced (per roadmap SC #1: "updates query_mode to the exact same value the legacy st.selectbox produced"). The MODE_OPTIONS dict at `app.py:46-51` is the source of truth — Phase 8 must preserve the same internal values (`auto`, `structured`, `semantic`, `hybrid`), though the visible labels can collapse to AUTO / SQL / SEMANTIC per roadmap SC #1 if HYBRID is dropped from sidebar pill (TBD by planner — pill shows 3 buttons per roadmap, but MODE_OPTIONS currently has 4 entries).

### Empty/initial main panel state

Header + subtitle render **always** (regardless of data_loaded / messages state):
- "Incident Intelligence" — EB Garamond 36px weight 300 charcoal
- "Ask in natural language. All data stays local." — Inter 15px warm-gray `#6B5E52`

When `len(st.session_state.messages) == 0`:
- 3-4 ghost-style example query lines appear under the subtitle
- Style: italic Inter 14px charcoal `#2C2420`, no boxes/borders, small `·` bullet prefix in warm-gray
- They are clickable — click-to-fill the chat input (existing example queries at `app.py:660-665` provide the strings: "Show all P1 incidents from last month", "Find incidents similar to Outlook crashes", "Top 5 assignment groups by volume", "How many incidents opened this week?")
- They disappear the moment the first user message is sent (gated by `len(messages) == 0`)

When `len(st.session_state.messages) > 0`:
- Example queries are gone, just header + subtitle + rendered chat history + chat input

**Phase 8 does NOT own** the no-data-CSV editorial empty card — that's Phase 10 (POL-01) which has locked copy ("No data loaded" + "Upload incidents.csv from the sidebar to begin."). Phase 8's empty state is about the no-messages-yet condition WHEN data IS loaded.

Existing brutalist `### EXAMPLE QUERIES` block at `app.py:659-665` and brutalist "READY FOR INPUT" panel at `app.py:651-657` and brutalist `terminal-header` at `app.py:641-649` and brutalist `status-bar` at `app.py:673-679` and brutalist `### QUERY INTERFACE` heading at `app.py:687` all get deleted / replaced in Phase 8.

### Sidebar section rhythm + dividers

**Vertical structure (top → bottom):**
1. Wordmark hero: "SNOWGREP" EB Garamond 28px weight 300 charcoal
2. Hairline rule (1px `--lp-border` / `#E8E0D8`, full-width)
3. **DATA** section header (small-caps Inter 500 11-12px warm-gray `#6B5E52` letter-spacing 0.1em) + content (upload lock + auth + file uploader + REPLACE/APPEND + status)
4. Hairline rule
5. **EMBEDDINGS** section header + content (sage/terracotta pill + REBUILD/UPDATE buttons)
6. Hairline rule
7. **LLM PROVIDER** section header + content (bottom-border-only selectbox + muted-gold model caption + restyled warning panel when blocked)
8. Hairline rule
9. **MODE** section header + content (three-button pill row AUTO / SQL / SEMANTIC)
10. Hairline rule
11. **CONFIG** section header + content (existing QUERY SETTINGS expander preserved — RESULTS LIMIT slider, SHOW SQL checkbox, EXEC SUMMARY checkbox)

**Spacing rule:** 24px padding above + 24px padding below each hairline rule. Section header sits directly after the rule (no extra gap before the header).

**Section order matches roadmap SC #1 verbatim:** DATA → EMBEDDINGS → LLM PROVIDER → MODE. CONFIG is preserved as a 5th section at the bottom (not in roadmap SC but exists in current `app.py:355-376` and the user did not ask to drop it — keeping per "behavior byte-identical to v2.1" invariant).

**Moves required:**
- DATA INGEST + DATA STATUS in current `app.py:162-260` consolidate into single DATA section
- MODE selector moves FROM main panel (`app.py:684-699`) TO sidebar (new MODE section as pill toggle)
- The existing main-panel `st.markdown("### QUERY INTERFACE")` heading + status bar + mode caption all get deleted (their function is absorbed by the sidebar MODE section and the editorial main-panel header)

### Provider warning panel content

When `missing_vars(provider)` returns a non-empty list, render a single warm-beige container with 3px terracotta `#A67866` left border, replacing the current `st.warning(..., icon=":material/warning:")` call at `app.py:342-346`:

**Container:**
- Background: warm-beige `#F5F0EB` (or `#EDE6DD` if needed for contrast against sidebar bg — planner picks based on visual contrast in DevTools)
- Left border: 3px solid terracotta `#A67866`
- No top/right/bottom border
- Padding: 16px
- 4px border-radius on right side only (left side is the terracotta border — sharp corner)

**Content stack (top to bottom):**
1. **Label** (locked verbatim per roadmap SC #2): `WARNING — PROVIDER NOT CONFIGURED` in small-caps Inter 500 11px terracotta `#A67866` letter-spacing 0.1em
2. **Body line**: `**<Provider Human Name>** is not configured. Missing: <code>VAR1</code>, <code>VAR2</code>.` — Inter 14px charcoal `#2C2420`, provider name bold, env vars in JetBrains Mono inside `<code>` tags (consumes the existing mono boundary in `css.py:347-356`)
3. **Fix line**: `Add them to .env and restart, or switch provider above.` — Inter 13px warm-gray `#6B5E52`

**Drop:** Streamlit's `icon=":material/warning:"` — the small-caps WARNING label replaces it visually. No emoji, no Material icon, no `:warning:` Slack-style shortcode.

**Preserve:** `st.session_state["_llm_provider_blocked"]` is still set to `True` when the warning shows (the chat_input depends on this flag — see Phase 5 SC #3 / Pitfall 5 invariant). The visual restyle does NOT change the session_state write order.

### Claude's Discretion

The planner has flexibility on:
- Exact pixel padding inside the warning container (16px is a recommendation, not locked)
- Whether the warm-beige warning container uses `#F5F0EB` or `#EDE6DD` for its bg — pick based on visual contrast against the sidebar bg `#EDE6DD` in DevTools
- Choice of CSS technique for the bottom-border-only selectbox (overriding `[data-baseweb="select"]` border to `border-bottom: 1px solid var(--lp-border)` and zeroing the other three sides is the obvious path, but planner may find a cleaner selector)
- Whether the MODE pill HYBRID label is shown as a 4th button or dropped to match the roadmap's 3-button SC (AUTO / SQL / SEMANTIC) — see "Open question for planner" below
- Exact icon glyph for the DATA file-indicator in the sidebar (mockup shows a small file icon next to "incidents.csv 12,047 rows" — planner picks a glyph that fits the editorial aesthetic, no emoji)
- Example query click-to-fill mechanism: `streamlit.components.v1.html` postMessage, query-param injection, or a small `st.button(use_container_width=True, label="...", key=f"example_{i}")` row — planner picks based on whether the chat_input can accept programmatic value injection in current Streamlit version

</decisions>

<specifics>
## Specific Ideas

- **Mockup as visual contract**: `.planning/design-mockups/01-main-chat.png` and `02-results-chart.png` are the binding visual reference for Phase 8. Wave A planner reads `01-main-chat.png` for sidebar; Wave B planner reads both for main panel.
- **Component patterns to reuse verbatim**: The sidebar, chat bubble, input field (thin bottom border style), divider, and status badge patterns in `C:\Users\taylo\.claude\skills\loro-piana-aesthetic\references\component-patterns.md` are the canonical implementations. Phase 8 ports them from the React/Tailwind examples to Streamlit CSS overrides without changing the visual outcome.
- **Pattern reuse for blocked state**: The opacity 0.5 + cursor not-allowed pattern for the blocked MODE pills mirrors the existing disabled cashmere button pattern in `src/ui/css.py:334-343`. Same approach, same selectors style — just scoped to the new pill class.
- **DOM bay for editorial table**: The white assistant card (MAIN-03) is the container Phase 9 (DVZ-01) will render the editorial HTML table INSIDE. Phase 8 must establish the card structure so Phase 9 can `<div class="lp-editorial-table">` into it without re-wrapping.
- **Mono boundary still load-bearing**: Phase 6 confined JetBrains Mono to `code, pre, kbd, samp, .lp-mono, [data-testid="stCodeBlock"], [data-testid="stCode"]`. Phase 8's restyled provider warning uses `<code>` tags for env var names so they automatically render in Mono — no new mono-allowing selector needed.
- **Locked v2.1 strings carry into Phase 8 verbatim**: `"LLM provider"` (selectbox label), `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"QUERY DISABLED — see sidebar warning"`. Plus Phase 8 introduces new locked verbatim string: `"WARNING — PROVIDER NOT CONFIGURED"` (sidebar warning label). Phase 11 TST-01 will pin all of these in the regression suite.
- **AST invariant still load-bearing**: `_render_provenance_caption(provider, model)` at `app.py:65-87` MUST NOT read `st.session_state`. The MAIN-04 restyle is CSS only — the helper's read sources are not touched. Test `tests/test_phase5_ui.py` AST check stays green.
- **Existing brutalist HTML to delete in Wave A (sidebar)**: `app.py:152-160` (terminal logo div with `#00ff00` border), `app.py:189-193` (red 🔒 LOCKED chip), `app.py:200-204` (green 🔓 UPLOAD UNLOCKED), `app.py:254-260` (red status dot div), `app.py:270-274` (green DOCS INDEXED div), `app.py:277-281` (amber NO EMBEDDINGS div). All replaced by editorial CSS-driven structure.
- **Existing brutalist HTML to delete in Wave B (main panel)**: `app.py:641-649` (terminal-header), `app.py:651-657` (READY FOR INPUT panel), `app.py:659-665` (EXAMPLE QUERIES brutalist boxes — content preserved as ghost lines, brutalist styling deleted), `app.py:673-679` (status-bar with green/yellow dots), `app.py:687` (QUERY INTERFACE heading — deleted, replaced by mode pill in sidebar). The `terminal-header`, `status-bar`, `example-query`, `route-badge`, `results-count`, `query-box` CSS classes referenced by these markdowns are already not in `css.py` (Phase 6 deleted them) — these brutalist `st.markdown` calls have been silently rendering raw HTML strings without their CSS since Phase 6, so removing them is a no-op visually beyond removing the unstyled junk.

</specifics>

<deferred>
## Deferred Ideas

- **Editorial HTML table + Altair theme** — Phase 9 (DVZ-01..05). Phase 8 establishes the white assistant card DOM bay; Phase 9 renders the editorial table inside it.
- **Editorial empty card for no-CSV-loaded state** — Phase 10 (POL-01). Locked copy: "No data loaded" + "Upload incidents.csv from the sidebar to begin." Phase 8 does NOT render this; Phase 8 only handles the no-messages-yet condition when data IS loaded.
- **Small-caps tracked loading indicators** ("ANALYZING…", "BUILDING EMBEDDINGS…", "QUERYING…") — Phase 10 (POL-02). Phase 8 keeps the existing `st.spinner("PROCESSING...")` and `st.spinner("LOADING CSV DATA...")` calls untouched.
- **Editorial error rendering with terracotta border + ERROR label** — Phase 10 (POL-03).
- **st.success / st.error / st.warning palette overrides** — Phase 10 (POL-04). Note: the Phase 8 sidebar warning panel is a CUSTOM container, not a styled `st.warning` — these are separate concerns.
- **HYBRID mode resurrection**: Current `MODE_OPTIONS` has 4 entries (AUTO, SQL, SEMANTIC, HYBRID); roadmap SC #1 specifies 3-button pill (AUTO / SQL / SEMANTIC). Wave A planner decides whether to drop HYBRID from the pill (and only expose 3 modes in v2.2) or render a 4-button pill — flagging as an open question, not a deferred capability. Either way the internal `query_mode` values stay intact for backward compat.
- **CSV upload password UX rework** — current "UNLOCK UPLOAD" + "LOCK UPLOAD" + password input pattern is preserved in Phase 8 (just restyled to consume cashmere buttons + bottom-border-only input). Any flow-level rework (e.g., session-token, expire-after-N-minutes, drop password entirely) is future work, not Phase 8.
- **Bottom-of-sidebar user identity** (mockup 01 shows "L.Piana / ADMIN" at sidebar bottom) — not in roadmap requirements, not in scope. Defer to future phase if multi-user auth is added.
- **Top-right notification bell / Admin User badge** (mockup 02 shows these in main panel top-right) — not in roadmap requirements, not in scope.
- **"+ NEW SEARCH" cashmere button at sidebar top** (mockup 02 shows this) — replaces current "CLEAR HISTORY" button conceptually but is not in roadmap requirements. Defer; Phase 8 keeps the existing "CLEAR HISTORY" button at the bottom of the main panel.
- **Left-rail nav items** ("Incident Search", "Knowledge Base", "Settings" shown in both mockups) — these are aspirational features not in the v2.2 milestone scope. Defer to a future milestone.
- **Reaction icons under assistant messages** (👍 👎 📋 shown in mockup 01) — not in roadmap requirements. Defer.
- **Per-message timestamp in provenance caption** (mockup 02 shows "· 14:32" suffix) — not in roadmap SC #4 (which locks the caption to `VIA <PROVIDER> · <model>`). Adding a timestamp would change the locked format. Defer.

</deferred>

---

*Phase: 08-screen-restyle*
*Context gathered: 2026-05-23*
