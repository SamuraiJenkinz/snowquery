---
phase: 07-splash-screen
plan: 02
type: execute
wave: 2
depends_on: ["07-01"]
files_modified:
  - "app.py"
autonomous: false
requirements:
  - SPL-02
  - SPL-04

must_haves:
  truths:
    - "On a fresh browser session, `app.py::main()` calls `render_splash()` exactly once (verified by `st.session_state['_splash_shown']` going from missing → True over the first rerun cycle)."
    - "On any rerun within the same browser session where `st.session_state['_splash_shown']` is already True, `render_splash()` is NOT called again — the app renders the sidebar + main content immediately."
    - "When `st.session_state['data_loaded']` AND `st.session_state['embeddings_ready']` are both True AND `_splash_dismiss_sent` is False, the lifecycle helper emits a `snowgrep-splash-dismiss` postMessage into every iframe via a tiny inline `<script>`, sets `_splash_dismiss_sent=True`, then sleeps 400ms (the locked fade duration from CONTEXT.md line 48) and clears the `st.empty()` placeholder so the iframe's fade-out has visibly completed before the placeholder is removed."
    - "The 4-second hard cap (SPL-02) is enforced ENTIRELY client-side inside the iframe (Plan 01 section D.2) — Python contains NO wall-clock check for the cap. Even if Streamlit never reruns after first mount, the splash fades on its own at 4s."
    - "Splash mounts at the TOP of `main()` BEFORE `init_session_state()` returns control to `render_sidebar()` / `render_main_content()` so it overlays everything else during the boot window."
    - "The locked v2.1 invariants are preserved: `page_title=\"SNOWGREP\"`, `page_icon=\"✦\"`, the `_render_provenance_caption` helper untouched, and `render_sidebar` runs BEFORE `render_main_content` (the `_llm_provider_blocked` order-load-bearing contract)."
  artifacts:
    - path: "app.py"
      provides: "Splash mount + session-gating + dismiss logic wired into `main()`."
      contains: "from src.ui.splash import render_splash"
      min_lines: 750
  key_links:
    - from: "app.py::main"
      to: "src.ui.splash.render_splash"
      via: "Import at top of app.py + call inside main() guarded by `_splash_shown` session flag."
      pattern: "from src\\.ui\\.splash import render_splash"
    - from: "app.py::main"
      to: "st.session_state['_splash_shown']"
      via: "Set to True after first render; checked on every subsequent rerun to short-circuit splash mount."
      pattern: "_splash_shown"
    - from: "app.py::main"
      to: "st.session_state['data_loaded'] AND st.session_state['embeddings_ready']"
      via: "Boolean AND checked on each rerun while splash is mounted; when both True (and dismiss-signal not yet sent), emit `postMessage({type:'snowgrep-splash-dismiss'})` into the iframe via a tiny inline `st.markdown` script, sleep 400ms (locked fade duration), then `placeholder.empty()`."
      pattern: "data_loaded.*embeddings_ready"
    - from: "app.py::_run_splash_lifecycle"
      to: "iframe `<script>` postMessage listener (Plan 01 section D.2)"
      via: "`window.postMessage({type:'snowgrep-splash-dismiss'}, '*')` sent into every iframe — the splash iframe's listener (Plan 01) consumes it, adds `.is-dismissing`, CSS fades opacity over 400ms."
      pattern: "snowgrep-splash-dismiss"
---

<objective>
Wire `render_splash()` (from Plan 01) into `app.py::main()` — mount the splash in an `st.empty()` placeholder at the top of `main()`, gate it behind the `_splash_shown` session flag (single-shot per browser session — SPL-04), and dismiss it the moment `data_loaded` AND `embeddings_ready` are both true OR 4 seconds have elapsed since first render (anti-flash cap — SPL-02).

Purpose: Plan 01 ships the visual component in isolation. This plan wires the Python session lifecycle: when to show, when to skip, and when to tear down. The two locked v2.1 invariants in `main()` (sidebar-runs-before-main for `_llm_provider_blocked`, and the `_render_provenance_caption` no-session-state read) must remain intact.

Output: Edits to `app.py` only — new import for `render_splash`, new helper or inline block at the top of `main()` handling the splash lifecycle, no other behavioral changes.
</objective>

<execution_context>
@C:/Users/taylo/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/taylo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/07-splash-screen/07-CONTEXT.md
@.planning/phases/07-splash-screen/07-01-SUMMARY.md
@app.py
@src/ui/splash.py
</context>

<tasks>

<task type="auto" id="1">
  <name>Task 1: Add splash import + session flags + splash lifecycle helper to `app.py`</name>
  <files>app.py</files>
  <action>
Edit `app.py`. Two targeted insertions; nothing else changes in this task.

**A. Add the splash import.**

Locate the existing UI import line (currently `from src.ui.css import LORO_PIANA_CSS` at the top of the file, line ~29). Insert directly beneath it:

```python
from src.ui.splash import render_splash
```

Keep the import flat — do NOT re-export via `src/ui/__init__.py`. This matches the Phase 6 convention (`from src.ui.css import LORO_PIANA_CSS`).

**B. Extend `init_session_state()` with the splash state keys.**

Find the existing `init_session_state()` function (currently at line ~89). Add three new keys at the END of the function (after `upload_authenticated`):

```python
    # Phase 7 splash lifecycle. `_splash_shown` is the once-per-session gate
    # (SPL-04). `_splash_placeholder` holds the `st.empty()` handle returned
    # at first mount so subsequent reruns can clear it after data is ready.
    # `_splash_dismiss_sent` ensures the dismiss postMessage + 400ms-sleep
    # path runs exactly once per session.
    #
    # NOTE: There is no `_splash_start_ts` and no Python-side 4s cap. The
    # 4s hard cap (SPL-02) lives entirely in the iframe's <script> block
    # (Plan 01 section D.2) — adding a Python wall-clock check is pointless
    # because Streamlit does not rerun on a wall-clock timer, so any Python
    # cap would only fire on the next user interaction (too late).
    if "_splash_shown" not in st.session_state:
        st.session_state._splash_shown = False
    if "_splash_placeholder" not in st.session_state:
        st.session_state._splash_placeholder = None
    if "_splash_dismiss_sent" not in st.session_state:
        st.session_state._splash_dismiss_sent = False
```

**C. Add the splash lifecycle helper.**

Insert a new module-level function `_run_splash_lifecycle()` ABOVE `main()` (so the order in the file is: existing functions → `_run_splash_lifecycle` → `main`). Use this exact body:

```python
def _run_splash_lifecycle() -> None:
    """Mount + dismiss-signal the boot splash. Phase 7 SPL-01, SPL-02, SPL-04.

    Two-state machine (Python side only — all timing-critical behavior lives
    in the iframe; see Plan 01 section D.2):

    State 1 — FIRST rerun of a browser session (`_splash_shown` is False):
        Mount the splash into a fresh `st.empty()` placeholder, stash the
        placeholder handle in session_state, and flip `_splash_shown` to True.
        Return.

    State 2 — subsequent reruns (`_splash_shown` is True):
        If the placeholder has already been cleared and the dismiss signal
        already sent, return immediately (steady-state, post-dismiss).

        Otherwise, check `data_loaded AND embeddings_ready`. If both True
        AND we haven't yet sent the dismiss signal:
            (a) Render a tiny inline <script> via st.markdown that sends
                `postMessage({type:'snowgrep-splash-dismiss'}, '*')` into
                every iframe (the splash iframe's listener consumes it and
                adds `.is-dismissing`, triggering the 400ms CSS fade).
            (b) Set `_splash_dismiss_sent = True`.
            (c) `time.sleep(0.4)` so the iframe's fade visibly completes
                before we tear down its container.
            (d) `placeholder.empty()` clears the iframe from the DOM.

        If data is NOT yet ready, do nothing — the iframe is still on
        screen, its own 4s hard-cap timer (Plan 01 section D.2) will fade
        it out client-side if data never arrives. Next rerun re-checks.

    Why no Python 4s cap: Streamlit only reruns on user interaction or
    session_state mutation. A wall-clock cap in Python would only fire on
    the next rerun, which may be never. The cap MUST live in the iframe.
    """
    import time

    # Fast path: dismiss already sent + placeholder cleared — nothing to do.
    if st.session_state.get("_splash_shown") and st.session_state.get("_splash_dismiss_sent"):
        return

    # State 1: first mount of the session.
    if not st.session_state.get("_splash_shown"):
        placeholder = st.empty()
        with placeholder.container():
            render_splash()
        st.session_state._splash_shown = True
        st.session_state._splash_placeholder = placeholder
        return

    # State 2: splash is mounted, dismiss not yet sent. Check data readiness.
    if (
        st.session_state.get("data_loaded")
        and st.session_state.get("embeddings_ready")
    ):
        # (a) Send dismiss signal into every iframe. The splash iframe's
        #     postMessage listener (Plan 01 section D.2) consumes
        #     {type:'snowgrep-splash-dismiss'} and adds .is-dismissing.
        #     Loop over window.frames so this targets the splash iframe
        #     regardless of how many iframes Streamlit has spawned.
        st.markdown(
            """
            <script>
              (function() {
                var payload = {type: 'snowgrep-splash-dismiss'};
                for (var i = 0; i < window.frames.length; i++) {
                  try { window.frames[i].postMessage(payload, '*'); } catch (e) {}
                }
              })();
            </script>
            """,
            unsafe_allow_html=True,
        )
        # (b) Mark sent so we don't double-fire.
        st.session_state._splash_dismiss_sent = True
        # (c) Wait for the 400ms iframe fade to complete (CONTEXT.md line 48).
        time.sleep(0.4)
        # (d) Tear down the placeholder. The iframe is already fully faded.
        placeholder = st.session_state.get("_splash_placeholder")
        if placeholder is not None:
            placeholder.empty()
        st.session_state._splash_placeholder = None
        return

    # Data not ready yet. Iframe is still showing; its own 4s hard-cap
    # timer will fade it out if data never arrives. Next rerun re-checks.
    return
```

**Design notes:**

- **No dead defensive 4s block.** The previous revision had an unreachable `elapsed >= 4.0` block that was guarded above by the skip-path early return. Removed entirely — the 4s cap is the iframe's job (Plan 01 section D.2).
- **No `time.sleep(0.8)` floor in Python.** The 800ms soft floor (CONTEXT.md line 46) is also client-side — the iframe's listener defers any too-early dismiss signal until 800ms has elapsed since mount. Python can fire the dismiss signal whenever it wants; the iframe absorbs the race.
- **The 400ms `time.sleep(0.4)` IS in Python** because it gates the placeholder teardown. Without it, `placeholder.empty()` would yank the iframe from the DOM before the CSS fade completes, producing the locked-against "snap" behavior. 400ms is a one-shot block on a one-shot path (state 2 fires exactly once per session), so it does not meaningfully harm Streamlit responsiveness.
- **Placeholder handle survives across reruns** because we stash it in `st.session_state._splash_placeholder`. Streamlit's `st.empty()` containers are session-persistent objects — keeping the handle lets a later rerun clear what a previous rerun mounted.
  </action>
  <verify>
1. `grep -n "from src.ui.splash import render_splash" app.py` returns one line — confirms the import is present.

2. `grep -n "_splash_shown\|_splash_placeholder\|_splash_dismiss_sent" app.py` returns at least 6 lines — three init_session_state declarations + lifecycle helper reads/writes for each of the three keys.

3. `grep -c "def _run_splash_lifecycle" app.py` returns exactly 1.

4. `grep -c "snowgrep-splash-dismiss" app.py` returns exactly 1 — the postMessage payload string is present and matches the iframe-side contract from Plan 01 section D.2.

5. `grep -c "time.sleep(0.4)" app.py` returns exactly 1 — the 400ms fade-window block before placeholder teardown is present.

6. `grep -c "_splash_start_ts\|elapsed >= 4.0\|elapsed >= 4 " app.py` returns 0 — the Python-side 4s cap (and any wall-clock start timestamp) must NOT exist; the cap lives in the iframe.

7. `python -c "import ast; tree = ast.parse(open('app.py').read()); fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}; assert '_run_splash_lifecycle' in fns; assert 'main' in fns; assert 'init_session_state' in fns; print('OK')"` prints `OK`.

8. `python -c "import app; print('imports clean')"` — must succeed without ImportError or syntax error (note: actually importing app.py may trigger Streamlit page config; that's fine as long as no exception is raised before main() is called).
  </verify>
  <done>
`app.py` imports `render_splash` from `src.ui.splash`. `init_session_state()` initializes `_splash_shown=False`, `_splash_placeholder=None`, `_splash_dismiss_sent=False`. `_run_splash_lifecycle()` exists as a module-level function above `main()`, implementing the two-state machine: (state 1) first-rerun mount + placeholder stash; (state 2) subsequent-rerun dismiss-signal send + 400ms sleep + placeholder teardown when data is ready. No Python-side 4s cap, no `_splash_start_ts`, no dead defensive blocks. No invocation site yet — Task 2 wires it into `main()`.
  </done>
</task>

<task type="auto" id="2">
  <name>Task 2: Call `_run_splash_lifecycle()` from `main()` + human-verify the four success criteria</name>
  <files>app.py</files>
  <action>
**A. Wire the lifecycle into `main()`.**

Locate the existing `main()` function (currently at line ~749). The current body is:

```python
def main():
    """Main application entry point.
    ...
    """
    init_session_state()
    render_sidebar()
    render_main_content()
```

Insert `_run_splash_lifecycle()` between `init_session_state()` and `render_sidebar()`. The order must be:

```python
def main():
    """Main application entry point.

    ORDER IS LOAD-BEARING: render_sidebar() must run BEFORE render_main_content()
    because the sidebar writes st.session_state["_llm_provider_blocked"] which
    render_main_content() reads at the st.chat_input call site. Reversing the
    order would leak stale blocked state across reruns (Phase 5 SC #3 + RESEARCH
    Pitfall 5).

    Phase 7 (SPL-02, SPL-04): `_run_splash_lifecycle()` runs AFTER
    `init_session_state()` (which creates `_splash_shown` /
    `_splash_placeholder` / `_splash_dismiss_sent`) and BEFORE the
    sidebar/main render so the splash mounts at the very top of the DOM
    during the boot window. First rerun mounts the splash; subsequent
    reruns either (a) do nothing if dismiss already sent, or (b) send the
    `snowgrep-splash-dismiss` postMessage into the iframe and tear down
    the placeholder once data is ready. The 4s hard cap (SPL-02) is
    enforced entirely client-side inside the iframe.
    """
    init_session_state()
    _run_splash_lifecycle()  # Phase 7: mount + gate + dismiss boot splash
    render_sidebar()
    render_main_content()
```

The v2.1 invariant — `render_sidebar()` must run before `render_main_content()` — is preserved. The new line sits BEFORE the sidebar so the splash overlays everything during boot, then yields cleanly.

**B. Confirm no other invariants are broken.**

Read the full `main()` and surrounding code one more time. Verify:

- `st.set_page_config(page_title="SNOWGREP", page_icon="✦", ...)` is unchanged.
- `st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)` is still at module level (so the parent app's CSS injects on every rerun; the splash iframe has its own CSS).
- `_render_provenance_caption` is unchanged (still does not read `st.session_state`).
- No other call site touches `_splash_shown` or `_splash_start_ts`.

**C. Then halt for human-verify checkpoint** (Task 3 below).
  </action>
  <verify>
1. `grep -A 6 "def main():" app.py | grep -c "_run_splash_lifecycle"` returns exactly 1 — confirms the call site exists in `main()`.

2. `grep -B 2 -A 2 "_run_splash_lifecycle()" app.py | grep -c "init_session_state\|render_sidebar"` returns at least 2 — confirms the new call sits between `init_session_state` and `render_sidebar` (call-order intact).

3. `python -c "import ast; src = open('app.py').read(); tree = ast.parse(src); main_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'main'); call_names = [c.func.id for c in ast.walk(main_fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]; assert call_names == ['init_session_state', '_run_splash_lifecycle', 'render_sidebar', 'render_main_content'], call_names; print('OK call order:', call_names)"` prints the exact call sequence.

4. `grep -n "page_title=\"SNOWGREP\"\|page_icon=\"✦\"" app.py` returns 2 hits — page chrome invariants intact.

5. `grep -c "def _render_provenance_caption" app.py` returns exactly 1, and the function body is unchanged from pre-edit (verify by reading the function manually).

6. Run the existing v2.1 test suite to confirm no regressions:
```
pytest tests/test_phase5_ui.py -q
```
Expected: all 22 tests pass.
  </verify>
  <done>
`main()` calls `_run_splash_lifecycle()` between `init_session_state()` and `render_sidebar()`. Page chrome, CSS injection, and `_render_provenance_caption` invariants intact. `pytest tests/test_phase5_ui.py` returns 22 passed.
  </done>
</task>

<task type="checkpoint:human-verify" id="3" gate="blocking">
  <what-built>
The complete Phase 7 splash flow: `_run_splash_lifecycle()` mounts the helix splash at the top of `main()` on the FIRST render of a browser session, then clears it when `data_loaded` AND `embeddings_ready` are both True OR 4 seconds have elapsed. The splash is skipped on subsequent reruns within the same browser session.
  </what-built>
  <how-to-verify>
1. **Fresh browser session — splash appears.** Open an Incognito / Private window and navigate to the running Streamlit app (`streamlit run app.py` first if not already running). Expected: the splash renders for several seconds — warm off-white background, "SNOWGREP" wordmark center in EB Garamond serif, "INCIDENT INTELLIGENCE" tagline in small-caps gold beneath, "LOADING YOUR DATA" near the bottom, 16 INC IDs (8 per diagonal stream) sparsely scattered and slowly drifting along two crossed diagonals. The mockup `.planning/design-mockups/00-splash-helix.png` is the visual contract.

2. **Splash dismisses on data readiness (with 400ms fade).** Without uploading a CSV (data_loaded=False), the splash should still fade out at 4 seconds (the iframe's client-side hard cap — observe a visible 400ms opacity fade, NOT a snap-clear). With a CSV already loaded from a previous session (via the persistent DuckDB store) and embeddings present, the splash should still display for at least 800ms (soft floor), THEN fade out over 400ms — confirms both the data-ready dismiss path AND the 400ms fade. If you observe a snap-clear (no fade), the iframe `<script>` block from Plan 01 section D.2 is broken.

3. **Single-shot per session.** With the splash already shown in the same browser window, click any sidebar control (e.g., the QUERY SETTINGS expander) or trigger any rerun. Expected: the splash does NOT re-appear; the app renders straight into the main view. The `_splash_shown` flag is doing its job.

4. **Reduced motion.** Open browser DevTools → Rendering tab → "Emulate CSS media feature `prefers-reduced-motion`" set to `reduce`. Open a new Incognito window (so `_splash_shown` resets). Reload. Expected: the splash still appears with wordmark/tagline/status label rendering IDENTICALLY to the motion version, but the INC IDs now fade in and out at FIXED positions with no horizontal drift, and the loop is visibly slower (10-12s instead of 6-8s).

5. **Locked strings.** Confirm verbatim: the wordmark reads `SNOWGREP` (not `Snowgrep` or `SNOW GREP`), the tagline reads `INCIDENT INTELLIGENCE` (not `Incident intelligence` or `INCIDENTS INTELLIGENCE`), the status label reads `LOADING YOUR DATA` (not `LOADING DATA` or `LOADING…`).

6. **v2.1 invariants intact.** After the splash clears, confirm the sidebar still shows "LLM provider" verbatim (lowercase 'p'), the chat_input placeholder still reads "QUERY DISABLED — see sidebar warning" when env vars are missing, and the page tab still shows the ✦ favicon with title "SNOWGREP".
  </how-to-verify>
  <resume-signal>
Type "approved" if all six checks pass. If anything is off — splash didn't appear, didn't dismiss, re-appeared on rerun, wrong text, reduced motion didn't kick in, or a v2.1 invariant regressed — describe the symptom and which check failed.
  </resume-signal>
</task>

</tasks>

<verification>
Run from project root after Task 2:

```
pytest tests/test_phase5_ui.py -q
```

Expected: 22 passed.

```
python -c "import ast; src = open('app.py').read(); tree = ast.parse(src); main_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'main'); call_names = [c.func.id for c in ast.walk(main_fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]; print(call_names)"
```

Expected: `['init_session_state', '_run_splash_lifecycle', 'render_sidebar', 'render_main_content']`.

Visual checkpoint (Task 3) confirms the runtime behavior matches the four success criteria.
</verification>

<success_criteria>
- `app.py` imports `render_splash` from `src.ui.splash`.
- `init_session_state()` initializes `_splash_shown=False`, `_splash_placeholder=None`, `_splash_dismiss_sent=False`.
- `_run_splash_lifecycle()` exists as a module-level function and is called from `main()` between `init_session_state()` and `render_sidebar()`.
- `app.py` contains NO `_splash_start_ts`, no Python-side wall-clock 4s cap, and no dead defensive `elapsed >= 4.0` block — the 4s cap is the iframe's responsibility (Plan 01 section D.2).
- `app.py` contains the postMessage payload string `snowgrep-splash-dismiss` exactly once (the dismiss-signal `st.markdown` script inside `_run_splash_lifecycle`).
- `app.py` contains exactly one `time.sleep(0.4)` (the 400ms fade-window block before placeholder teardown).
- Fresh browser session: splash renders, displays at least 800ms, then fades over 400ms when `data_loaded` AND `embeddings_ready` are both True. If data never readies, the iframe's own 4s hard-cap fade triggers regardless.
- Same browser session, subsequent reruns: splash does NOT re-render (`_splash_shown` short-circuits).
- Reduced motion: INC IDs fade at fixed positions; wordmark/tagline/status render identically; the 400ms dismiss fade is retained (CONTEXT.md line 56).
- v2.1 invariants preserved: page_title="SNOWGREP", page_icon="✦", `_render_provenance_caption` untouched, `pytest tests/test_phase5_ui.py` returns 22 passed.
- Satisfies SPL-04 (once per browser session via `_splash_shown`). Co-satisfies SPL-02 with Plan 01 (Python side sends the data-ready dismiss signal; iframe enforces the 4s hard cap and the 400ms fade).
</success_criteria>

<output>
After completion, create `.planning/phases/07-splash-screen/07-02-SUMMARY.md` documenting:
- Diff summary of `app.py` (lines added: imports, init_session_state extension, `_run_splash_lifecycle`, call site in `main()`).
- Confirmation that the four success criteria from ROADMAP.md Phase 7 are observable (with the human-verify checkpoint outcome).
- Confirmation that the 22 v2.1 Phase 5 UI tests still pass.
- Any deviations from 07-CONTEXT.md (expected: none).
</output>
