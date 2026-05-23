---
phase: 07-splash-screen
plan: 02
subsystem: ui
tags: [streamlit, splash, session-state, postmessage, iframe, python]

# Dependency graph
requires:
  - phase: 07-01
    provides: render_splash() component in src/ui/splash.py — the iframe-hosted helix splash HTML/CSS/JS
  - phase: 06-foundation
    provides: LORO_PIANA_CSS token system; page_icon/page_title invariants; app.py import conventions
provides:
  - Splash mount + session-gating + dismiss lifecycle wired into app.py::main()
  - _run_splash_lifecycle() helper (two-state machine: mount-on-first-rerun, dismiss-when-data-ready)
  - Session state keys: _splash_shown, _splash_placeholder, _splash_dismiss_sent
  - postMessage dismiss signal (snowgrep-splash-dismiss) injected into every iframe via st.markdown inline script
affects: [08-screen-restyle, 09-data-viz, 10-polish, 11-docs-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Splash lifecycle owns its own 4s hard cap client-side inside the iframe; Python only emits dismiss postMessage + sleeps 400ms for fade — pattern reusable for future iframe-based overlays"
    - "st.empty() placeholder handle stored in session_state across reruns so a later rerun can clear what a previous rerun mounted"
    - "Single-shot session gating via _splash_shown bool — set once on first mount, never reset within session"

key-files:
  created: []
  modified:
    - app.py

key-decisions:
  - "4s hard cap is entirely client-side (iframe script, Plan 01 section D.2). No Python wall-clock check — Streamlit does not rerun on a timer, so Python cap would only fire on next user interaction."
  - "400ms time.sleep(0.4) IS in Python because it gates placeholder teardown after the dismiss postMessage. Without it, placeholder.empty() yanks the iframe before the CSS fade completes."
  - "Dismiss postMessage loops over window.frames[] so it targets the splash iframe regardless of how many iframes Streamlit has spawned."
  - "_run_splash_lifecycle() is inserted between init_session_state() and render_sidebar() in main() so splash mounts at the top of the DOM before any sidebar or main content renders."

patterns-established:
  - "iframe overlay pattern: mount in st.empty() at top of main(), stash handle in session_state, send postMessage dismiss signal when condition met, sleep for fade duration, then placeholder.empty()"
  - "Session-gated once-per-session UI: check _splash_shown before mounting; set True after first mount; skip on all subsequent reruns"

# Metrics
duration: ~15min
completed: 2026-05-22
---

# Phase 7 Plan 02: Wire Splash Into Main Summary

**Splash lifecycle wired into app.py::main() — two-state Python machine mounts helix splash on first rerun, sends snowgrep-splash-dismiss postMessage + 400ms sleep + placeholder teardown when data_loaded AND embeddings_ready are both True**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-22
- **Completed:** 2026-05-22
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint, approved)
- **Files modified:** 1 (app.py)

## Accomplishments

- `_run_splash_lifecycle()` implemented as a module-level two-state machine above `main()` — state 1 mounts the splash into an `st.empty()` placeholder on the first rerun of a browser session; state 2 sends the dismiss postMessage and tears down the placeholder once `data_loaded` and `embeddings_ready` are both True
- `init_session_state()` extended with three new session-state keys: `_splash_shown=False`, `_splash_placeholder=None`, `_splash_dismiss_sent=False`
- `main()` call order updated to `init_session_state() → _run_splash_lifecycle() → render_sidebar() → render_main_content()` — the load-bearing `render_sidebar`-before-`render_main_content` order (Phase 5 `_llm_provider_blocked` contract) is preserved
- All six live-browser human-verify checks passed (see Verification section)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add splash import, session-state keys, and lifecycle helper** — `338a649` (feat)
2. **Task 2: Wire _run_splash_lifecycle() into main()** — `d32705c` (feat)
3. **Task 3: Human-verify checkpoint** — no commit; user approved all six checks

**Plan metadata:** pending this metadata commit (docs(07-02))

## Files Created/Modified

- `app.py` — Added `from src.ui.splash import render_splash` import; extended `init_session_state()` with three splash session keys; added `_run_splash_lifecycle()` helper (~85 lines) above `main()`; inserted `_run_splash_lifecycle()` call in `main()` between `init_session_state()` and `render_sidebar()`

## Verification Passed (Human-Verify Checkpoint — Task 3)

User confirmed all six live-browser checks in an Incognito window:

1. **Fresh session — splash appears**: helix motif, EB Garamond wordmark `SNOWGREP`, gold tagline `INCIDENT INTELLIGENCE`, status label `LOADING YOUR DATA` all rendered correctly
2. **400ms fade-out at 4s client-side cap**: observable opacity fade (not snap-clear) at the 4-second mark — iframe hard cap working
3. **Single-shot per session**: triggering a rerun after splash shown did not re-render the splash — `_splash_shown` gating working
4. **Reduced motion variant**: INC IDs fade at fixed positions (no drift), slower opacity loop (~10-12s) — `prefers-reduced-motion: reduce` media query active
5. **Locked strings verbatim**: `SNOWGREP`, `INCIDENT INTELLIGENCE`, `LOADING YOUR DATA` all confirmed exact
6. **v2.1 invariants intact**: `LLM provider` sidebar label, `QUERY DISABLED — see sidebar warning` chat_input placeholder, ✦ favicon, `SNOWGREP` page title — all unchanged

## Decisions Made

- **No Python-side 4s cap**: Streamlit does not rerun on a wall-clock timer, so any Python `elapsed >= 4.0` check would only fire on the next user interaction — too late. The 4s hard cap lives entirely in the iframe script (Plan 01 section D.2). This is a reusable pattern: any future iframe-based overlay should enforce timing constraints client-side.
- **400ms sleep IS in Python**: `time.sleep(0.4)` gates the `placeholder.empty()` teardown. Without it, the placeholder is yanked before the CSS fade completes, producing a snap-clear. The sleep is on a one-shot path (fires exactly once per session) so it does not meaningfully harm Streamlit responsiveness.
- **window.frames[] loop for postMessage**: the dismiss script iterates `window.frames` so the message reaches the splash iframe regardless of how many total iframes Streamlit has spawned (Streamlit's component count varies by version/config).

## Deviations from Plan

None — plan executed exactly as written. The lifecycle helper body from the plan spec was implemented verbatim.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 7 is COMPLETE: both plans done, all four SPL requirements satisfied
  - SPL-01: helix splash component (Plan 01)
  - SPL-02: 4s hard cap (Plan 01 iframe script + Plan 02 postMessage + 400ms teardown)
  - SPL-03: brand-accurate visual (Plan 01 + human-verify confirmed)
  - SPL-04: once-per-session via `_splash_shown` (Plan 02)
- Phase 8 (screen restyle: sidebar SBR-* + main panel MAIN-*) is unblocked — depends on Phase 6 only
- Carry-forward pattern: iframe overlay lifecycle (mount in `st.empty()`, store handle in session_state, postMessage dismiss, sleep for fade duration, `placeholder.empty()`) is reusable for any future iframe-based overlay in this app

---
*Phase: 07-splash-screen*
*Completed: 2026-05-22*
