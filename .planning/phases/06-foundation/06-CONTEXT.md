# Phase 6: Foundation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

A single CSS module (`src/ui/css.py`) exposing the Loro Piana design tokens (fonts, palette, spacing, radii, shadows) and refreshed page chrome (`page_icon`, base `<body>` background, font-family reset). Every subsequent v2.2 phase consumes this foundation **read-only** — Phase 6 ships no feature surface beyond a tokens audit and a verified test-button render.

What it delivers:
- `src/ui/css.py` with `LORO_PIANA_CSS` (full CSS string) and `LORO_PIANA_TOKENS` (Python dict mirror of palette + spacing hex/values)
- Google Fonts import for EB Garamond (300, 400) + Inter (400, 500); JetBrains Mono retained
- Brutalist `#0a0a0a` background + JetBrains-Mono-on-body completely removed
- `page_icon` refreshed to a restrained editorial mark; `page_title="SNOWGREP"` preserved
- Three verifiable button instances proving cashmere `#8B7355` + 4px radius + uppercase 0.1em tracked label

What it does NOT deliver (downstream phases):
- Splash screen (Phase 7)
- Sidebar/main panel restyle (Phase 8)
- Editorial table / Altair theme (Phase 9)
- Empty state / loading / error / toast styling (Phase 10)
- USER_GUIDE / README / visual regression suite (Phase 11)

</domain>

<decisions>
## Implementation Decisions

All four gray areas were delegated to Claude's discretion based on the `loro-piana-aesthetic` skill (`C:\Users\taylo\.claude\skills\loro-piana-aesthetic\`) and the validated Stitch mockups (`.planning/design-mockups/00-splash-helix.png`, `01-main-chat.png`, `02-results-chart.png`). The decisions below are locked for downstream agents.

### Page icon mark

- **Decision: `"✦"` (U+2726 BLACK FOUR POINTED STAR)** as the `page_icon` value in `st.set_page_config(page_title="SNOWGREP", page_icon="✦", ...)`.
- **Why:** Single restrained editorial glyph — reads as a wax-seal / magazine-masthead mark, not a brutalist boxed `▣`. Renders cleanly across browser favicons without a custom SVG asset (no new build step, no path resolution at runtime). Matches the "subtle artisanal mark" energy of the Loro Piana wordmark which itself uses no logo glyph.
- **Rule out alternatives:** `◆` reads too heavy/geometric; `·` is too invisible at favicon scale; a custom SVG adds a deploy-time asset path concern with no aesthetic upside for the foundation phase. Phase 11 may upgrade to a custom favicon SVG if desired — noted but out of scope for Phase 6.

### Token export pattern

- **Decision: dual export — CSS custom properties (primary) + Python dict mirror (secondary).** Both live in `src/ui/css.py`, kept in sync as a single source of truth.
  ```python
  # src/ui/css.py
  LORO_PIANA_TOKENS = {
      "bg":              "#F5F0EB",
      "surface":         "#FFFFFF",
      "border":          "#E8E0D8",
      "text":            "#2C2420",
      "text_muted":      "#6B5E52",
      "text_subtle":     "#8A7A6B",
      "accent":          "#8B7355",  # cashmere primary
      "accent_hover":    "#A89680",
      "accent_pressed":  "#6D5A42",
      "gold_decorative": "#B8A88A",
      "success":         "#8A9A7D",  # sage
      "warning":         "#C4A76B",  # amber
      "danger":          "#A67866",  # terracotta
      "info":            "#9B8F7D",  # taupe
      # spacing (px ints)
      "space_1": 4, "space_2": 8, "space_3": 12, "space_4": 16,
      "space_6": 24, "space_8": 32, "space_12": 48, "space_16": 64,
      # radii
      "radius_md": 4, "radius_lg": 8, "radius_full": 9999,
  }
  LORO_PIANA_CSS = """...CSS using --lp-* custom properties..."""
  ```
- **Why:** Streamlit CSS overrides handle 90% of styling via the `LORO_PIANA_CSS` string injected once from `app.py`. But three downstream surfaces render inline HTML where CSS variables are awkward and brittle:
  1. **Phase 9 editorial table** (`_render_editorial_table` in `src/utils.py`) — builds HTML cell-by-cell; needs literal hex values or token lookups.
  2. **Phase 9 Altair theme** (`src/ui/altair_theme.py`) — Altair config is JSON/Python dict, not CSS.
  3. **Phase 11 visual regression tests** (`tests/test_phase6_visual.py`) — assert palette hex presence by importing the dict, no CSS parsing.
- Both exports live in the same module so they cannot drift. CSS uses `--lp-*` custom properties; Python uses `LORO_PIANA_TOKENS["accent"]`.

### Spacing scale

- **Decision: adopt the skill's full 4px-grid scale verbatim as CSS custom properties (`--lp-space-1` through `--lp-space-24`).** Editorial-generous defaults locked in:
  - Component padding default: **`--lp-space-8` (32px)**
  - Section padding: **`--lp-space-12` (48px)**
  - Section separation: **`--lp-space-16` (64px)**
  - Card max-widths and hero spacing per the skill's `--lp-space-20/24` (80/96px)
- **Why:** The skill defines a canonical 4px grid (`design-tokens.md` §Spacing). Using named tokens (`var(--lp-space-8)`) instead of raw values means a single-file adjustment changes every consumer. Editorial-generous (32/48/64) was already validated by the Stitch mockups — the main-chat mockup shows abundant whitespace around the page header, between cards, and around the sidebar wordmark.
- **Python mirror:** spacing values exported as raw px ints in `LORO_PIANA_TOKENS` (e.g., `space_8: 32`) so HTML/Altair builders can `f"padding: {tokens['space_8']}px"`.

### JetBrains Mono boundary

- **Decision:** Rule of thumb — **"If it's a record identifier or raw code/data the user typed, it's mono. If it's UI chrome or human language, it's Inter."**

  **USE JetBrains Mono for:**
  - INC IDs everywhere they appear (Phase 7 splash streams, Phase 8 sidebar/main, Phase 9 table identifier column)
  - File paths and CSV names (e.g., `incidents.csv` in the sidebar DATA section per Stitch mockup 01)
  - `<code>` / `<pre>` blocks and `st.code(...)` output
  - Error tracebacks and stack frames
  - Raw SQL preview (the generated SQL string before execution)

  **DO NOT use JetBrains Mono for:**
  - Body `<body>` font (Inter is the body font — Phase 6 success criterion 1 enforces this)
  - Page headers, card titles, wordmark (EB Garamond)
  - Small-caps tracked labels (Inter 500)
  - Provenance captions like `VIA AZURE OPENAI · gpt-4o` (Inter 500 small-caps per Phase 8 MAIN-04)
  - Button labels, chat input placeholder (Inter)
  - Dataframe **numeric cells** in Phase 9 (Inter — numbers are content, not identifiers)
  - Dataframe **priority labels** like "P1 - Critical" (italic EB Garamond per Stitch mockup 01)

- **Why:** The Stitch mockups validate this split — main-chat shows `incidents.csv` in mono (filename = identifier), table numbers in Inter (data = content), priority labels in italic serif (editorial). The splash mockup shows floating INC IDs in mono (identifiers). This rule gives downstream phases a single yes/no test without re-asking.
- **CSS implementation:** body `font-family: var(--lp-font-body)` (Inter); explicit `.lp-mono { font-family: var(--lp-font-mono); }` utility class + selective `code, pre, .lp-mono { ... }` rules in `LORO_PIANA_CSS`.

### Claude's Discretion (within Phase 6)

- Exact ordering of CSS sections inside the `LORO_PIANA_CSS` string (tokens → base → utilities → Streamlit overrides is reasonable).
- Whether Google Fonts comes in via `<link rel="preconnect">` + `<link rel="stylesheet">` in the CSS string or via `@import` at the top of the CSS. Pick whichever is simpler given Streamlit's `st.markdown(..., unsafe_allow_html=True)` constraints — both are acceptable.
- Placement of the three verification button instances — a temporary `if st.session_state.get("_phase6_smoke"):` block, a small debug expander, or three real buttons that ship (e.g., the sidebar's existing primary actions). Pick the lowest-friction approach that satisfies the success criterion.
- Whether to fully delete the brutalist CSS source or move it to a `legacy_brutalist_css.py` archive file. No backward-compat requirement; deletion preferred.

</decisions>

<specifics>
## Specific Ideas

- The Stitch main-chat mockup (`01-main-chat.png`) is the visual contract for the foundation — note the warm off-white background (`#F5F0EB`) flooding the entire viewport, the editorial whitespace around the "Incident Intelligence" page header, and the cashmere "ASK" button in the bottom-right. Phase 6 must make this background + font baseline true for the bare app even before any other phase lands.
- The skill's `tokens.css` template (`C:\Users\taylo\.claude\skills\loro-piana-aesthetic\templates\tokens.css`) is the canonical reference for the `LORO_PIANA_CSS` content — start by porting it verbatim and then adding Streamlit-specific overrides (`.stApp`, `[data-testid="stSidebar"]`, etc.) on top.
- The skill's design-tokens reference defines `--lp-shadow-warm: 0 4px 12px rgba(139, 115, 85, 0.08)` — Phase 6 must register this so Phase 8's assistant cards can use it without re-defining; **no `rgba(0,0,0,...)` shadows allowed anywhere in v2.2** (rule from `design-tokens.md` §Shadows).
- Focus ring is `box-shadow: 0 0 0 3px rgba(139, 115, 85, 0.2)` — warm, never blue. Phase 6 ships this in `LORO_PIANA_CSS` so every focusable element across v2.2 inherits it.

</specifics>

<deferred>
## Deferred Ideas

- **Custom favicon SVG** — replace the `✦` glyph with a dedicated SVG asset (could be a stylized "S" or a subtle helix mark echoing the splash motion). Noted for the v2.2 polish phase or a v2.3 brand refinement; out of scope for Phase 6 to keep the foundation asset-free.
- **Dark mode token variant** — the Loro Piana aesthetic is light-mode-first by design; a dark variant would require a parallel token set and a media query. Out of scope for v2.2; revisit if/when a "dim/night reading" mode is requested.
- **CSS-in-JS / runtime theme switching** — if a future phase wants user-selectable themes, the `LORO_PIANA_TOKENS` dict provides the seam. For v2.2 the theme is fixed Loro Piana.

</deferred>

---

*Phase: 06-foundation*
*Context gathered: 2026-05-22*
