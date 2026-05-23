# Phase 7: Splash screen - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Single-shot boot splash rendered via `streamlit.components.v1.html` from `src/ui/splash.py::render_splash()`. Displays an EB Garamond "SNOWGREP" wordmark, an "INCIDENT INTELLIGENCE" tagline, and a "LOADING YOUR DATA" status label, layered over two sparse diagonal streams of synthetic INC IDs. Mounted in an `st.empty()` placeholder at the top of `main()`; clears when `data_loaded` AND `embeddings_ready` are both true in `st.session_state`. Hard cap 4s (anti-flash), soft floor 800ms (brand moment lands). Honors `prefers-reduced-motion`. Once per browser session (tracked via `_splash_shown`).

</domain>

<decisions>
## Implementation Decisions

### Splash text + labels

- **Wordmark:** `SNOWGREP` — EB Garamond, weight 300, ~64px, charcoal `#2C2420` (`--lp-text`), center-anchored both axes. Locked verbatim.
- **Tagline (beneath wordmark, ~12px gap):** `INCIDENT INTELLIGENCE` — Inter 500, 11px, `text-transform: uppercase`, `letter-spacing: 0.15em` (`--lp-tracking-widest`), muted gold `#B8A88A` (`--lp-neutral-400`). Locked verbatim.
- **Status label (near bottom, ~80% viewport height):** `LOADING YOUR DATA` — same type treatment as tagline (Inter 500, 11px, small-caps, widest tracking, muted gold). Locked verbatim.
- **Single static label — no dynamic stage swap.** No mid-load mutation to `BUILDING EMBEDDINGS…` or progress percentage. Editorial single label keeps the brand moment quiet; helix motion is the activity indicator.

### Helix stream content

- **Synthetic INC IDs.** Format: `INC` + 7 zero-padded digits (e.g., `INC0851470`). Reasons: data isn't loaded yet when splash renders; synthetic preserves privacy in screenshots/recordings; format is recognizable to operators.
- **Generation:** Built once at module load via a fixed random seed so the splash is reproducible across reruns inside a session.
- **Count: 16 IDs total — 8 per diagonal stream.** Sparse, not crowded.
- **Two diagonal axes** crossing near center (the "helix" feel):
  - Stream A: top-left → bottom-right, ~-20° from horizontal
  - Stream B: top-right → bottom-left, ~+20° from horizontal
- **Organic placement:** along each diagonal with randomized perpendicular offset (~±60px) so the IDs don't form rigid lines.
- **Center exclusion zone:** ~300px × ~140px rectangle around the wordmark/tagline cluster — IDs avoid this region (matches mockup whitespace).

### Stream visual treatment

- **Typography:** JetBrains Mono 11px — splash is the ONLY place outside `code/pre/kbd/samp` that uses mono, which is allowed because INC IDs are data identifiers (respects the Phase 6 mono boundary).
- **Color:** warm-gray `#8A7A6B` (`--lp-neutral-500` / `--lp-text-subtle`).
- **Per-ID opacity envelope:** `0 → 0.6 → 0` over a 6-8s loop, staggered start delays so the canvas always has motion but never feels crowded.
- **Motion:** each ID translates ~120px along its diagonal over its lifetime — subtle drift (~15-20px/sec), not a runner.
- **Easing:** `cubic-bezier(0.4, 0, 0.2, 1)` (matches `--lp-easing-smooth` from Phase 6).
- **Background:** solid `#F5F0EB` (`--lp-bg`) — no texture, no vignette, no gradient.

### Loading-state cues + transition

- **Single static "LOADING YOUR DATA" label** is the only loading cue. No progress bar, no row count, no spinner, no stage label swap.
- **Min duration floor: 800ms.** Even if data loads instantly, splash stays visible 800ms so the brand moment lands. Implemented via JS `setTimeout` inside the component that gates the clear-trigger ack; Python side respects this by checking elapsed time before tearing down `st.empty()`.
- **Hard cap: 4s** per SPL-02 — wins over the floor if data load also exceeds 4s.
- **Transition out:** fade entire splash to `opacity: 0` over 400ms (`--lp-transition-slow`), then `st.empty()` placeholder is cleared. No slide, no snap.

### Reduced-motion variant (SPL-03)

- `@media (prefers-reduced-motion: reduce)` block inside the splash's `<style>`:
  - INC IDs render at FIXED positions (no `translate` keyframes — only opacity).
  - Opacity loop slowed to 10-12s and max opacity capped at 0.4.
  - Wordmark, tagline, status label render identically to the motion variant.
  - 400ms fade-out on dismiss retained (low motion budget, doesn't trigger vestibular concerns).

### Claude's Discretion

- Exact 16 synthetic INC ID strings (any plausible 7-digit values from the fixed seed).
- Exact pixel coordinates for each ID along its diagonal.
- Per-ID stagger timing within the opacity loop.
- Implementation choice between CSS `@keyframes` and Web Animations API inside the component HTML — **CSS keyframes preferred** (fully self-contained, no JS animation lib needed, simpler reduced-motion override).
- z-index ordering within the splash overlay.
- Exact mechanism for `st.session_state['_splash_shown']` flag check vs render gate (early-return in `main()` vs guarded render call).
- How the Python side polls the `data_loaded` / `embeddings_ready` flags to know when to dismiss (likely a single boolean expression checked each Streamlit rerun).

</decisions>

<specifics>
## Specific Ideas

- **Mockup `.planning/design-mockups/00-splash-helix.png` is the visual contract.** Match the sparse, organic feel of scattered INC IDs over generous whitespace — NOT a Matrix-style dense data rain. The mockup is more "editorial interlude" than "loading dashboard."
- "Editorial moment, not loading screen" — the splash is a brand interlude. The helix is decoration, not a literal data-activity meter, which is why a single static `LOADING YOUR DATA` label suffices.
- Phase 6 mono boundary respected — JetBrains Mono is confined to the INC ID elements only; wordmark is EB Garamond, all labels are Inter. This is the third place mono appears (after `code/pre` and `[data-testid="stCodeBlock"]`) and is justified because INC IDs are data identifiers.
- All token values (`#F5F0EB`, `#2C2420`, `#B8A88A`, `#8A7A6B`, `--lp-tracking-widest`, `--lp-easing-smooth`) consumed from the Phase 6 `LORO_PIANA_CSS` / `LORO_PIANA_TOKENS` module. The splash component HTML may hardcode these values (because `streamlit.components.v1.html` runs in an iframe and cannot inherit the parent's CSS custom properties), but `src/ui/splash.py` should `import LORO_PIANA_TOKENS from src.ui.css` and string-interpolate the hex values — never type a brand hex literal.

</specifics>

<deferred>
## Deferred Ideas

- **Real INC IDs streamed from loaded data** — would require splash to render AFTER data loads, defeating its purpose. Synthetic IDs are the right call here.
- **Multi-stage loading labels** (`LOADING DATA…` → `BUILDING EMBEDDINGS…` → `READY`) — explicitly rejected, not deferred. Adds complexity for marginal info gain; editorial single label is the design choice.
- **Sound / audio cue on splash dismiss** — out of scope for v2.2 visual revamp.
- **Skip-splash hotkey or query-param override** — out of scope; once-per-session is sufficient. If operator pain emerges, revisit in v2.3.
- **Splash on hot-reload during dev** — out of scope; the `_splash_shown` session flag naturally suppresses it across reruns in the same browser session, which covers dev iteration.

</deferred>

---

*Phase: 07-splash-screen*
*Context gathered: 2026-05-22*
