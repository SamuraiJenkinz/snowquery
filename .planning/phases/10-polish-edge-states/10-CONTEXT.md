# Phase 10: Polish + edge states - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Restyle the four remaining brutalist-leaking surfaces in v2.2: empty state when no CSV is loaded, loading indicators around LLM/embedding/data work, error rendering for `QueryError` / `LLMError` and untrapped exceptions, and Streamlit alert calls (`st.success` / `st.error` / `st.warning`). After this phase, no browser-default colors or v2.1 brutalist copy leak through anywhere in the rendered tree.

Out of scope: new capabilities (retry, toast repositioning, error categorization UX). In scope: chrome + copy only.

</domain>

<decisions>
## Implementation Decisions

User delegated all implementation calls to Claude after seeing the four gray areas. The following are Claude's research-grounded decisions, locked for the researcher and planner.

### Empty state anatomy (POL-01)

- **Placement**: Top-of-panel, beneath the existing logo hero (`app.py:740-746`) and subtitle, generously spaced (`margin: var(--lp-space-8) auto`). NOT vertically centered — the hero is the anchor, the empty card is the follow-through.
- **Container**: White bg + 1px `var(--lp-border)` border + 4px radius. Reuses the `.lp-msg-assistant` visual language so the user is pre-trained on the card grammar from Phase 8.
- **Dimensions**: `max-width: 520px`, centered (`margin: ... auto`), padding `var(--lp-space-8)` (generous breathing room).
- **Hairline divider**: Inside the card, between heading and subtitle. 1px `var(--lp-border)` color, ~80px wide (NOT full-width), centered. Editorial accent only.
- **Typography**: EB Garamond 24px weight 300 charcoal `var(--lp-text)` heading "No data loaded"; Inter 15px weight 400 warm-gray `var(--lp-text-muted)` subtitle "Upload incidents.csv from the sidebar to begin." Both locked verbatim from POL-01 spec.
- **No icon, no illustration**: Pure type. Loro Piana restraint.
- **CSS class**: New `.lp-empty-card` with slots `.lp-empty-heading`, `.lp-empty-divider`, `.lp-empty-subtitle`.
- **Render site**: Replace the bare `return` at `app.py:749-752` with a `st.markdown(EMPTY_CARD_HTML, unsafe_allow_html=True)` call. The card is the entire body content when `not st.session_state.data_loaded`.

### Loading indicator behavior (POL-02)

- **Motion**: Subtle opacity pulse on the small-caps text (`@keyframes lp-pulse` cycling opacity 0.5 → 1.0 → 0.5 over 1.5s ease-in-out infinite). NO animated ellipsis dots — visually noisy, breaks editorial restraint. Single ellipsis character U+2026 in every locked string.
- **Mechanism**: Custom HTML inside `st.empty()` placeholder, NOT `st.spinner()`. Streamlit's spinner injects a circular icon container that is hard to fully suppress; explicit markdown gives pixel control. Pattern: `placeholder = st.empty(); placeholder.markdown('<div class="lp-loading">ANALYZING…</div>', unsafe_allow_html=True); ...; placeholder.empty()`.
- **Callsite mapping**:
  - `app.py:811` `st.spinner("PROCESSING...")` → "ANALYZING…" via `lp-loading` placeholder inside the assistant `st.chat_message` block. Single indicator for the full `process_query` call (covers both classify + LLM + SQL exec phases — they fuse from the operator's POV).
  - `app.py:447` `status_text.text(message.upper())` in `_build_embeddings_with_progress` → "BUILDING EMBEDDINGS…" via `lp-loading` markdown above the `st.progress` bar. Phase-step copy (e.g. embedding row 5000/12000) is suppressed in favor of the single locked phrase; if the planner finds the per-step text load-bearing, restore it below the `lp-loading` line as Inter 12px warm-gray sub-line.
  - `app.py:126` `st.spinner(f"{mode_text} CSV DATA...")` → "LOADING DATA…" via `lp-loading` placeholder. Extends POL-02 with a fourth locked phrase that the spec doesn't enumerate but is needed for parity (CSV ingest is also an LLM-adjacent wait the operator sees).
- **"QUERYING…"** string is documented in CSS / locked-string catalog for future use if a discrete SQL-exec phase is ever split out of `process_query` — currently has NO callsite. Document this in the SUMMARY so future Claudes don't grep-fail it.
- **Color**: Muted gold `var(--lp-neutral-400)` (#B8A88A), Inter weight 500, 11px, `letter-spacing: 0.1em`. Matches the provenance caption aesthetic — the operator already reads this color as "wait / status / metadata."
- **CSS class**: New `.lp-loading` with `@keyframes lp-pulse`.

### Error card anatomy (POL-03)

- **Unified treatment**: `QueryError` and `LLMError` use the SAME visual — `.lp-error-card`. No visual distinction. The error message body carries the differentiation. Distinguishing chrome adds complexity without operator value.
- **Container**: White bg + 3px `var(--lp-danger)` (#A67866) left border + 1px `var(--lp-border)` top/right/bottom + 4px radius (matches `.lp-msg-assistant` body geometry, swaps left border for terracotta). Main-panel-scoped — NOT reusing the sidebar `.lp-warn-card` selector (which is scoped to `[data-testid="stSidebar"]`).
- **Anatomy**:
  - "ERROR" label on its own line at top — Inter weight 500 11px `letter-spacing: 0.1em` terracotta `var(--lp-danger)`. Locked string.
  - Error message body — Inter weight 400 charcoal `var(--lp-text)` (#2C2420), line-height 1.5.
  - NO retry CTA in this phase (deferred — needs retryability classification).
- **Provenance caption above**: Keep current graceful-skip behavior (`app.py:822` — only renders when `response.get("provider")` is truthy). Most error paths in `process_query` (lines 607, 615, 630) don't set provider, so provenance is silently omitted. If a provider-attached error happens (LLM call returned a Bedrock guardrail intervention or Anthropic API error), the provenance DOES render — that's useful debugging metadata above the error card. Don't add suppression logic.
- **Render path**: New helper `_render_error_html(msg, label="ERROR") -> str` returns the editorial card HTML. Replaces every `[ERR] {msg}` string interpolation in `process_query` return dicts (lines 608, 616, 631) with `_render_error_html(...)`. The existing `st.markdown(response["content"], unsafe_allow_html=True)` at `app.py:829` renders it.
- **Missing try/except — IN SCOPE**: There is no `try/except` around `process_query` at the callsite (`app.py:812`). Untrapped exceptions crash the whole rerun. Phase 10 adds:
  ```python
  try:
      response = process_query(user_query, selected_mode)
  except (QueryError, LLMError) as e:
      response = {"content": _render_error_html(str(e)), "results": None, "sql": None}
  except Exception as e:
      logger.exception("Unexpected error in process_query")
      response = {"content": _render_error_html(f"Unexpected error: {e}", label="ERROR"), "results": None, "sql": None}
  ```
- **CSS class**: New `.lp-error-card` with slots `.lp-error-label`, `.lp-error-body`.

### Toast palette + sweep scope (POL-04)

- **Mechanism**: Pure CSS overrides targeting Streamlit's alert wrappers — `[data-testid="stAlert"]`, `[data-testid="stAlertContentSuccess|Error|Warning|Info"]`. NO call-site changes. Researcher should confirm the exact Streamlit testid emission shape for the current version (1.36+) before locking selectors.
- **Palette mapping**:
  - `st.success` → sage `var(--lp-success)` (#8A9A7D) 3px left border + warm-beige fill `var(--lp-bg)` + sage small-caps "SUCCESS" label + charcoal body
  - `st.error` → terracotta `var(--lp-danger)` (#A67866) 3px left border + warm-beige fill + terracotta small-caps "ERROR" label + charcoal body (visually consistent with `.lp-error-card`)
  - `st.warning` → amber `var(--lp-warning)` (#C4A76B) 3px left border + warm-beige fill + amber small-caps "WARNING" label + charcoal body
  - `st.info` → muted gold `var(--lp-neutral-400)` 3px left border + warm-beige fill + muted-gold small-caps "INFO" label + charcoal body
  - All four: hide Streamlit's default icon (`[data-testid="stAlertContentIcon"], svg`), border-radius `var(--lp-radius-md)`, padding `var(--lp-space-4)`.
- **Call sites covered**: `st.success` at `app.py:133, 138, 455`; `st.error` at `app.py:146, 194, 461`. All are sidebar-scoped or fire after CSV upload / embeddings build. CSS-only sweep covers all six callsites with zero call-site edits.
- **Position / duration**: NO changes. Streamlit's default position (top of column, persists until next rerun) is preserved. Repositioning is a separate UX phase.

### Claude's Discretion

All four areas above were Claude's discretion (user delegated). Areas remaining flexible for the planner during task decomposition:

- Whether to split POL-02 CSS / POL-04 CSS into separate plans or bundle both into one CSS-extension plan
- Whether `_render_error_html` lives in `src/ui/results.py` (already houses other editorial renderers from Phase 9) or in a new `src/ui/edge_states.py`. **Recommended**: extend `src/ui/results.py` — keeps editorial HTML renderers in one module. Will validate with researcher.
- Exact `lp-pulse` keyframe curve (0.4 → 1.0 vs 0.5 → 1.0) — visual tuning during execution
- Embeddings build per-step copy (e.g. "Row 5000 / 12000") — keep below `BUILDING EMBEDDINGS…` as Inter 12px sub-line, or suppress entirely. Researcher to weigh.

</decisions>

<specifics>
## Specific Ideas

- **Reuse `.lp-warn-card` pattern from Phase 8** (`src/ui/css.py:578-616`) — the sidebar warning card is essentially the visual template for `.lp-error-card`. Same anatomy (terracotta left border + warm-beige bg + small-caps label + body + optional fix sub-line). Phase 10 lifts the pattern out of the sidebar selector scope into a main-panel variant. Don't re-derive from scratch.
- **Token reuse**: `--lp-success` (#8A9A7D sage), `--lp-warning` (#C4A76B amber), `--lp-danger` (terracotta) already exist in `src/ui/css.py:88-89`. Phase 10 adds zero new color tokens — entirely a CSS-class extension exercise.
- **`st.empty()` placeholder pattern** is already established by Phase 7 splash (`_splash_placeholder` in session_state) — same lifecycle for loading indicators. No new infrastructure.
- **"Pure-HTML-string renderer" pattern from Phase 9** (`src/ui/results.py` returns strings, `st.markdown(html, unsafe_allow_html=True)` lives at the callsite) — extend the same pattern to `_render_error_html` and `_render_empty_card` (if not already shipped — Phase 9 shipped `_render_empty_state` per STATE.md; planner to disambiguate and avoid duplicates).
- **Streamlit alert testid shape**: verify against current 1.36+ DOM emission during research — the kind-specific selector names have shifted between versions. Lock the exact attribute strings in RESEARCH.md.

</specifics>

<deferred>
## Deferred Ideas

These came up during decision-making but are out of scope for Phase 10:

- **Retry CTA on error cards**: needs error categorization (retryable network errors vs unrecoverable schema mismatches). Phase 11+ or v2.3 feature.
- **"QUERYING…" as a discrete callsite**: requires refactoring `process_query` to split classify / LLM-call / SQL-exec phases with separate indicators. Refactor scope, not polish scope.
- **Toast repositioning** (centered banner, inline-card instead of overlay): separate UX phase. v2.2 inherits Streamlit's positional contract.
- **Empty state icon / illustration**: pure type was the editorial decision. Reopen as a design refresh if needed later.
- **Per-error-type chrome variants** (e.g. red border for network failures, amber for soft warnings): unified `.lp-error-card` was the call. Reopen when categorization exists.

</deferred>

---

*Phase: 10-polish-edge-states*
*Context gathered: 2026-05-23*
