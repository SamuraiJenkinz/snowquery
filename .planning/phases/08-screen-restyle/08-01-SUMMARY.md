# Plan 08-01 Summary — Sidebar editorial restyle (SBR-01..06)

**Phase:** 08-screen-restyle (Wave A)
**Completed:** 2026-05-23
**Status:** Complete — human-verify approved

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `419a155` | feat | append `/* === Sidebar (Phase 8 SBR-*) === */` to `src/ui/css.py` (174 lines, 11 selector groups) |
| `a8073f4` | feat | refactor `render_sidebar()` — editorial sections, MODE pill, EMBEDDINGS pill, warm-beige warning card |
| `0169723` | fix  | force sidebar always-visible — neutralize collapse transform (Phase 6 hides expand toggle) |
| `5a5907c` | fix  | swap MODE pill row for horizontal `st.radio` with sage dot indicator |
| `79b1601` | fix  | restyle Streamlit defaults bleeding through sidebar (icon font, checkboxes, slider, expander) |
| `4f569f2` | fix  | propagate UNLOCK UPLOAD typography to inner `<p>` |
| `0c9be47` | fix  | NO DATA LOADED uses `.lp-pill-warn` — match UNLOCK UPLOAD |

## Implementations vs SBR-01..06

| Req | Status | What renders |
|-----|--------|--------------|
| SBR-01 | ✓ | `<h1 class="lp-sidebar-wordmark">SNOWGREP</h1>` — EB Garamond 28px weight 300 charcoal; replaces brutalist `#00ff00` terminal-logo div |
| SBR-02 | ✓ | Five `<p class="lp-section-header">` (DATA, EMBEDDINGS, LLM PROVIDER, MODE, CONFIG) — Inter 500 11px small-caps tracked warm-gray; hairline `<hr class="lp-section-rule">` between |
| SBR-03 | ✓ | `st.radio(horizontal=True)` with sage dot on active label — writes `st.session_state["query_mode"]` to `"auto" / "structured" / "semantic"`; disabled when `_llm_provider_blocked=True`. **Deviation:** original plan used three `st.button` in `st.columns(3)` with sibling-div wrapping for active state; this fails in Streamlit because `st.markdown('<div>')` siblings the subsequent `st.button` and the CSS selector never resolves. Plus 320px / 3 cols squeezes "SEMANTIC" into per-character vertical wrap. Switched to `st.radio` per user preference (sage dot indicator vs cashmere-fill pill). |
| SBR-04 | ✓ | `<span class="lp-status-pill lp-status-pill--ready">READY · N DOCS</span>` (sage tint) / `<span class="lp-status-pill lp-status-pill--missing">MISSING</span>` (terracotta tint) — replaces brutalist green/amber dots |
| SBR-05 | ✓ | `<div class="lp-bb-select">` wraps `st.selectbox` — bottom-border-only via `[data-baseweb="select"]` override; locked label `"LLM provider"` verbatim; active model in `<p class="lp-active-model">` muted-gold |
| SBR-06 | ✓ | `<div class="lp-warn-card">` with 3px terracotta left border; `<p class="lp-warn-label">WARNING — PROVIDER NOT CONFIGURED</p>` (em-dash U+2014); env vars render in `<code>` (Mono via Phase 6 boundary); `st.session_state["_llm_provider_blocked"]` written `True` / `False` in matching branches |

## Live-verify Deviations (auto-fixed Rule 1 — bug)

Six fixes landed during human-verify against `.planning/design-mockups/01-main-chat.png`:

1. **Sidebar not visible** (`0169723`) — Phase 6's universal `header { visibility: hidden }` rule also hid Streamlit's sidebar expand toggle. Once collapsed, no in-UI recovery. Force sidebar always-visible via `transform: none !important; margin-left: 0 !important; visibility: visible !important` on `[data-testid="stSidebar"]` regardless of `aria-expanded` state. Hidden the in-sidebar collapse buttons to prevent user-strand. Sidebar is mission-critical (only place to upload data + configure LLM).
2. **MODE per-character wrap + no active distinction** (`5a5907c`) — see SBR-03 row above. Switched to `st.radio(horizontal=True)` with `:has(input:checked)` driving the sage dot. User-approved.
3. **`keyboard_arrow_down` icon name leaks as text** (`79b1601`) — Phase 6's universal `[data-testid="stSidebar"] *` font-family override clobbered Material Symbols. Restored Material Symbols font on `[class*="material-symbols"]`, `[class*="material-icons"]`, `[data-testid*="Icon"]` inside sidebar.
4. **Red checkboxes / red slider** (`79b1601`) — Streamlit's default red accent bleeds through Phase 6 CSS. Overrode `[data-baseweb="checkbox"]`, `[data-testid="stSlider"]` selectors to cashmere `--lp-accent`. Expander summary header restyled to small-caps editorial (was Streamlit bold default).
5. **UNLOCK UPLOAD / USING DEFAULT PASSWORD inconsistent with pill aesthetic** (`79b1601`, `4f569f2`) — User asked both match the `EMBEDDINGS MISSING` pill (warm-beige tint bg + terracotta text + rounded). Added `.lp-pill-warn` class; UNLOCK UPLOAD button gets per-key override via `.st-key-unlock_upload` (Streamlit 1.36+ key-based wrapper class); typography rules propagated to inner `<p>` so font matches the pill exactly.
6. **NO DATA LOADED inconsistent with sibling pills** (`0c9be47`) — Same `lp-label` + inline color pattern as the password warning, but visually didn't match. Swapped to `<span class="lp-pill-warn">` so all three DATA-section warning indicators (UNLOCK UPLOAD, USING DEFAULT PASSWORD, NO DATA LOADED) share one visual contract.

**Phase 10 territory note:** Items 3-5 (checkbox/slider/expander Streamlit-default red bleed) are technically POL-04 (toast/notification palette overrides) by-spec. User explicitly asked them addressed during Wave A live-verify. Captured here vs deferring to Phase 10.

## Test Status

`pytest tests/test_phase5_ui.py -q` → **22/22 passed** through every commit.

Updated test: `test_sc3_sidebar_renders_warning_with_missing_vars_named` — assertion changed from `st.warning()` call check to scanning `st.markdown` call_args for `lp-warn-card` HTML containing all 3 Anthropic env-var names. Business contract identical.

## Locked Strings Preserved Verbatim

- `"LLM provider"` (sidebar selectbox label)
- `"Azure OpenAI"` / `"Anthropic Claude (MGTI)"` (provider option labels)
- `"WARNING — PROVIDER NOT CONFIGURED"` (new Phase 8 locked string — em-dash U+2014)
- `"QUERY DISABLED — see sidebar warning"` (not touched here; Plan 02 owns the chat_input)

## Untouched (per Plan 01 contract)

- `_render_provenance_caption` body at `app.py:65-87` — AST invariant locked by `tests/test_phase5_ui.py`
- `MODE_OPTIONS` dict at `app.py:46-51` — internal `auto/structured/semantic/hybrid` values intact for backward compat (HYBRID dropped from visible radio per CONTEXT decisions)
- `_PROVIDER_OPTIONS` / `_PROVIDER_LABELS` / `_PROVIDER_KEYS` at `app.py:57-62`
- Function call order in `main()` — `render_sidebar()` still runs before `render_main_content()` so `_llm_provider_blocked` and `query_mode` are set before the chat_input reads them
- The legacy main-panel `MODE` selectbox at `app.py:684-699` — Plan 02 (Wave B) deletes it; Plan 01 only ADDED the sidebar MODE selector

## Carry-forward Decisions

- **Sidebar bg = `#F5F0EB` (--lp-bg)** chosen over `#EDE6DD` (--lp-neutral-100) — matches mockup `.planning/design-mockups/01-main-chat.png`. Warning card uses `--lp-bg` too for consistency.
- **Sidebar is non-collapsible** in v2.2 — Phase 6 hid the expand toggle and this app's sidebar is the only data-upload + LLM-config surface. Hide collapse buttons via CSS.
- **`.lp-pill-warn` is the v2.2 soft-warning pill primitive** — used for USING DEFAULT PASSWORD, NO DATA LOADED. Phase 9-10 should reuse this class for sibling indicators rather than re-rolling.
- **`.st-key-{key}` is the per-button override pattern** for Streamlit 1.36+ — used here to make UNLOCK UPLOAD a soft pill that overrides Phase 6's global cashmere fill. Future phases needing per-button visual variants should use this pattern.
- **MODE selector is `st.radio` not three buttons** — the radio's native `input:checked` state survives Streamlit reruns reliably; the `:has(input:checked)` selector drives the sage dot without needing manual session_state class-name juggling.
