# Plan 08-02 Summary — Main panel editorial restyle (MAIN-01..06)

**Phase:** 08-screen-restyle (Wave B)
**Completed:** 2026-05-23
**Status:** Complete — human-verify approved

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `4515480` | feat | append `/* === Main panel (Phase 8 MAIN-*) === */` to `src/ui/css.py` (MAIN-01..06 selectors) |
| `ba8eee2` | feat | refactor `render_main_content()` + `render_chat_history()` to editorial pattern |
| `88d814a` | feat | add bold display SNOWGREP wordmark above main page header (text-based, Anton) |
| `5de510d` | fix  | center SNOWGREP main-panel wordmark horizontally |
| `6410ae6` | fix  | land main-panel logo where the splash wordmark was (60vh flex header block) |
| `7e1ef9c` | fix  | shrink header block to 35vh to avoid `st.chat_input` auto-scroll push-off |
| `dca55ca` | fix  | SNOWGREP as fixed-position background watermark, not inline |
| `73dfcec` | fix  | SNOWGREP inline hero — prominent logo + header below |
| `332ab9d` | feat | use branded SNOWGREP logo PNG instead of Anton text wordmark |
| `af78da0` | fix  | patch logo PNG — SNOWGRP → SNOWGREP (typo fix) |
| `5cf4ea7` | feat | replace sidebar SNOWGREP wordmark with branded logo image |

## Implementations vs MAIN-01..06

| Req | Status | What renders |
|-----|--------|--------------|
| MAIN-01 | ✓ (re-spec) | Original spec: EB Garamond 36px "Incident Intelligence" + Inter 15px subtitle, always visible. Final: branded PNG hero (copper SNOWGRP box + blue INCIDENT INTELLIGENCE tagline) wraps the Intelligence concept; subtitle "Ask in natural language. All data stays local." sits below centered. **Deviation:** the user iterated to a branded logo image instead of the spec'd plain h1 text. The `<img>` carries `alt="SNOWGREP — Incident Intelligence"` so the text remains in the markup for screen readers and any future Phase 11 string-pin tests. |
| MAIN-02 | ✓ | User messages wrapped in `<div class="lp-msg-user">` — warm-beige `#F5F0EB` background, right-aligned (`margin-left: auto`), max-width 70%, 4px radius, no avatar / role label |
| MAIN-03 | ✓ | Assistant messages wrapped in `<div class="lp-msg-assistant">` — white background, 1px `#E8E0D8` border, left-aligned, max-width 85%, soft warm shadow. Establishes the DOM bay Phase 9 (DVZ-01) will render the editorial table into |
| MAIN-04 | ✓ | Provenance caption wrapped in `<div class="lp-provenance">` — muted-gold `#B8A88A` small-caps Inter 500 11px, 0.1em tracking. Helper body at `app.py:65-87` UNTOUCHED — AST invariant locked by `tests/test_phase5_ui.py` |
| MAIN-05 | ✓ | Chat input wrapped via `[data-testid="stChatInput"]` selector — bottom-border-only style; placeholder `"Ask anything about your incidents…"` (single U+2026 ellipsis); cashmere ASK submit inherited from Phase 6 |
| MAIN-06 | ✓ | Blocked-state placeholder `"QUERY DISABLED — see sidebar warning"` preserved verbatim (em-dash U+2014); `disabled=True` wiring intact; row opacity 0.5 via `[data-testid="stChatInput"]:has(textarea[disabled])` |

## Live-verify Deviations (iterated with user)

The simple "Incident Intelligence + subtitle" header from the original spec went through six iterations during human-verify before landing on the final branded-logo hero:

1. **Add bold display wordmark** (`88d814a`) — User asked for a SNOWGREP logo above Incident Intelligence in the DaBrokeCollector wordmark style. Added Anton font + 64px display text + hairline rule between logo and h1.
2. **Center horizontally** (`5de510d`) — Logo defaulted to left-align; user asked for centered.
3. **Land at splash wordmark position** (`6410ae6`) — User wanted the splash-to-app transition to feel like the logo "takes the place" of the splash wordmark. Added `.lp-main-header-block` flex wrapper at `min-height: 60vh` with `justify-content: center` to land the logo at viewport center.
4. **Shrink to 35vh** (`7e1ef9c`) — At 60vh the page was taller than the viewport and `st.chat_input` auto-scrolled into view, pushing the logo above the top edge. User had to scroll up to see it. Reduced to 35vh — better but still slight scroll.
5. **Fixed-position background watermark** (`dca55ca`) — User's clever idea: make the logo `position: fixed` at viewport center (same coords as splash wordmark), opacity 0.15, behind everything (z-index 0). The splash iframe overlays it during boot; when splash dismisses, the watermark is revealed at the exact same spot — no positioning fight at all.
6. **Inline hero — prominent + header below** (`73dfcec`) — User wanted the Incident Intelligence header VISUALLY ATTACHED to the logo (below it). Fixed-position background separates them. Switched back to inline rendering: Anton 112px centered, h1 + subtitle directly beneath, all in a `.lp-main-hero` centered wrapper.

Final logo evolution:

7. **Branded PNG instead of Anton text** (`332ab9d`) — User provided a branded logo PNG (copper SNOWGRP wordmark in a rectangular outline + blue INCIDENT INTELLIGENCE tagline on dark backdrop). Set up `.streamlit/config.toml` with `enableStaticServing = true`, moved logo to `static/snowgrep-logo.png`, replaced Anton text + h1 with `<img src="app/static/snowgrep-logo.png">` at max-width 480px centered.
8. **Patch PNG typo** (`af78da0`) — Original PNG read "SNOWGRP" (missing E). Used Pillow to cover the existing text region with the dark background color `(10, 10, 10)` and re-render "SNOWGREP" in matching copper `(170, 115, 70)` using Impact font. Box outline and blue INCIDENT INTELLIGENCE tagline untouched. Note: the original wordmark had a stenciled grunge texture that couldn't be replicated without the source PSD — patched SNOWGREP uses clean Impact rendering instead.
9. **Sidebar uses the same logo** (`5cf4ea7`) — User asked for visual continuity between sidebar and main panel. Replaced `<h1 class="lp-sidebar-wordmark">SNOWGREP</h1>` with same `<img src="app/static/snowgrep-logo.png">` at max-width 240px (fits 320px sidebar with 24px padding each side).

## Test Status

`PYTHONPATH=. pytest tests/test_phase5_ui.py -q` → **22/22 passed** through every commit.

Updated test (committed in Plan 02 Task 2): `test_chat_input_blocked_state_placeholder` assertion adjusted from old brutalist `"ENTER QUERY..."` placeholder to new editorial `"Ask anything about your incidents…"`. Business contract (blocked-state placeholder is verbatim `"QUERY DISABLED — see sidebar warning"`) preserved.

## Locked Strings Preserved Verbatim

- `"QUERY DISABLED — see sidebar warning"` (em-dash U+2014) — chat_input placeholder when blocked
- `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`
- NEW Plan 02 locked strings:
  - `"Ask anything about your incidents…"` (chat_input placeholder, ellipsis U+2026)
  - `"Ask in natural language. All data stays local."` (subtitle, trailing period)
  - The `Incident Intelligence` phrase lives inside the logo image alt-text (`alt="SNOWGREP — Incident Intelligence"`) for accessibility / future text-search tests

## Untouched (per Plan 02 contract)

- `_render_provenance_caption` body at `app.py:65-87` — AST invariant — `git diff` confirms zero lines changed in that range
- `_PROVIDER_OPTIONS` / `_PROVIDER_LABELS` / `_PROVIDER_KEYS` at `app.py:57-62`
- `MODE_OPTIONS` dict at `app.py:46-51` — internal values intact
- Function call order in `main()` — sidebar still runs before main content
- The Phase 5 AST test in `tests/test_phase5_ui.py` (helper body has zero `session_state` references)

## Carry-forward Decisions

- **Branded logo PNG is the v2.2 visual anchor** — used in both sidebar (`max-width: 240px`) and main panel (`max-width: 480px`). Single source of truth at `static/snowgrep-logo.png`. The dark backdrop of the PNG is intentional — provides high contrast against the warm-beige page bg, frames the logo as a deliberate brand mark.
- **Streamlit static serving is enabled** via `.streamlit/config.toml` (`enableStaticServing = true`). Future asset additions should drop into `static/` and reference via `app/static/<filename>`.
- **Ghost-query click-to-fill mechanism is `st.session_state["_pending_ghost_query"]` + `st.rerun()`** — no `streamlit.components.v1.html` postMessage fallback. Top-of-render drain handler pops the pending value; downstream submit path is identical to `st.chat_input.submit`.
- **Phase 9 (DVZ-01) DOM bay** — the editorial HTML table renders INSIDE `<div class="lp-msg-assistant">`. Phase 9 should NOT re-wrap; just inject the table markup at the appropriate position inside the assistant card.
- **Logo PNG texture is non-recoverable** — the original grunge stencil texture was lost when patching SNOWGRP → SNOWGREP. If the user wants the texture back, they'd need to provide a source PSD or a corrected PNG. Current Impact rendering is clean but consistent in color/weight.

## Phase-Level Notes

This plan went through significantly more user-driven iteration than typical — 11 commits across Wave 2 vs. the spec'd 2-3. Most iteration came from the SNOWGREP main-panel hero treatment (8 of the 9 visual deviations). The final shape — branded PNG hero centered in `.lp-main-hero`, same PNG in sidebar — is documented as the v2.2 brand contract and should not need further iteration unless the user provides a new asset.
