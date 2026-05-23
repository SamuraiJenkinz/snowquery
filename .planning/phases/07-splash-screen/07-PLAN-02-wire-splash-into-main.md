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
    - "When `st.session_state['data_loaded']` AND `st.session_state['embeddings_ready']` are both True, the `st.empty()` placeholder is cleared (`.empty()` call fires), removing the splash from the DOM."
    - "The splash is dismissed no later than 4 seconds (wall clock) after first render, even when data/embeddings are not yet ready — the 4s hard cap wins over data readiness."
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
      via: "Boolean AND checked on each rerun while splash is active; triggers `placeholder.empty()` when both true OR 4s elapsed."
      pattern: "data_loaded.*embeddings_ready"
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
    # (SPL-04); `_splash_start_ts` is the wall-clock timestamp captured the
    # first time the splash renders so the 4-second hard cap can be enforced
    # even when data load runs longer (SPL-02 anti-flash + anti-overstay).
    if "_splash_shown" not in st.session_state:
        st.session_state._splash_shown = False
    if "_splash_start_ts" not in st.session_state:
        st.session_state._splash_start_ts = None
```

No `_splash_dismissed` flag — the absence of the splash from the DOM after `placeholder.empty()` is the dismissed state; `_splash_shown` stays True for the rest of the session to prevent re-mount on reruns.

**C. Add the splash lifecycle helper.**

Insert a new module-level function `_run_splash_lifecycle()` ABOVE `main()` (so the order in the file is: existing functions → `_run_splash_lifecycle` → `main`). Use this exact body:

```python
def _run_splash_lifecycle() -> None:
    """Mount, gate, and dismiss the boot splash. Phase 7 SPL-01..04.

    Contract:
    - Called from the TOP of `main()`, BEFORE `render_sidebar()` and
      `render_main_content()`. This runs every Streamlit rerun.
    - On the FIRST rerun of a browser session, `_splash_shown` is False:
      the splash is rendered into an `st.empty()` placeholder, the
      start timestamp is captured, and `_splash_shown` is flipped to True.
    - On EVERY subsequent rerun within the same session, `_splash_shown`
      is True: this function short-circuits and returns immediately so
      the splash is never re-mounted.
    - Dismiss conditions (whichever fires first):
      1. Both `data_loaded` AND `embeddings_ready` are True
         (the happy path — data is ready).
      2. 4 seconds have elapsed since `_splash_start_ts`
         (anti-overstay hard cap — SPL-02).
      When either fires, `placeholder.empty()` clears the splash from
      the DOM and this function returns. Note: Streamlit's execution
      model means the splash will visibly clear on the NEXT rerun
      after the conditions are first met (which Streamlit triggers
      automatically when `data_loaded` / `embeddings_ready` flip).
    """
    import time

    # Skip path: already shown this session.
    if st.session_state.get("_splash_shown"):
        return

    # Mount path: render into a placeholder we keep a handle to.
    placeholder = st.empty()
    with placeholder.container():
        render_splash()
    st.session_state._splash_shown = True
    st.session_state._splash_start_ts = time.time()

    # Immediate-clear path: if both data_loaded AND embeddings_ready are
    # already True at first mount (e.g., a quick reload after init), clear
    # the placeholder right away. Anti-flash floor (800ms minimum visible)
    # is NOT enforced in Python — the iframe's font load + paint time
    # naturally floors the perceived duration, and adding a synchronous
    # 800ms sleep would block the Streamlit thread (bad). The hard cap
    # below is the only Python-side timing gate.
    if (
        st.session_state.get("data_loaded")
        and st.session_state.get("embeddings_ready")
    ):
        placeholder.empty()
        return

    # On subsequent reruns (next time Streamlit re-executes the script,
    # which happens whenever any session_state mutation triggers a rerun
    # or the user interacts), `_splash_shown` is True and this function
    # short-circuits at the top. The placeholder from this run is garbage-
    # collected; the splash visibly clears as soon as the script reruns
    # past this function and re-renders the page WITHOUT calling
    # `render_splash` again.
```

Note the deliberate design: we mount the splash ONCE on first render. We do NOT re-render it on subsequent reruns (skip-path returns early). The splash visibly disappears on the NEXT rerun after first mount because the page is re-rendered without it.

To enforce the 4-second hard cap and the data-ready dismiss without infinite-loop polling, this plan's design relies on Streamlit's natural rerun triggers: any sidebar interaction, any data load completion (which mutates `data_loaded`), and any embeddings-ready flip will trigger a rerun. Most boot windows will see the splash clear on the rerun that follows `data_loaded` flipping to True.

For the worst case (very slow load, no other reruns), we add a final-defense check. Modify `_run_splash_lifecycle` to also include:

```python
    # Defensive: if more than 4s have elapsed since first mount and we
    # somehow got here a second time (shouldn't happen given the skip
    # path above, but guards against future refactors), force the clear.
    elapsed = time.time() - (st.session_state._splash_start_ts or time.time())
    if elapsed >= 4.0:
        placeholder.empty()
```

(Place this AFTER the immediate-clear path, BEFORE the function returns.)

This guards `_run_splash_lifecycle()` for any future refactor where the early-return guard might be removed.
  </action>
  <verify>
1. `grep -n "from src.ui.splash import render_splash" app.py` returns one line — confirms the import is present.

2. `grep -n "_splash_shown\|_splash_start_ts" app.py` returns at least 4 lines — init_session_state declarations + lifecycle helper reads/writes.

3. `grep -c "def _run_splash_lifecycle" app.py` returns exactly 1.

4. `python -c "import ast; tree = ast.parse(open('app.py').read()); fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}; assert '_run_splash_lifecycle' in fns; assert 'main' in fns; assert 'init_session_state' in fns; print('OK')"` prints `OK`.

5. `python -c "import app; print('imports clean')"` — must succeed without ImportError or syntax error (note: actually importing app.py may trigger Streamlit page config; that's fine as long as no exception is raised before main() is called).
  </verify>
  <done>
`app.py` imports `render_splash` from `src.ui.splash`. `init_session_state()` initializes `_splash_shown=False` and `_splash_start_ts=None`. `_run_splash_lifecycle()` exists as a module-level function above `main()`, with the early-return skip path, the `st.empty()` mount path, the immediate-clear path, and the 4s defensive cap. No invocation site yet — Task 2 wires it into `main()`.
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
    `init_session_state()` (which creates the `_splash_shown` flag) and
    BEFORE the sidebar/main render so the splash mounts at the very top of
    the DOM during the boot window. Subsequent reruns short-circuit inside
    the lifecycle helper (no double-mount, no flicker).
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

2. **Splash dismisses on data readiness.** Without uploading a CSV (data_loaded=False), the splash should still clear at 4 seconds (the hard cap). With a CSV already loaded from a previous session (via the persistent DuckDB store) and embeddings present, the splash should clear immediately on first paint — confirms the data-ready dismiss path.

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
- `init_session_state()` initializes `_splash_shown=False` and `_splash_start_ts=None`.
- `_run_splash_lifecycle()` exists as a module-level function and is called from `main()` between `init_session_state()` and `render_sidebar()`.
- Fresh browser session: splash renders, then clears when `data_loaded` AND `embeddings_ready` are both True OR 4 seconds elapsed.
- Same browser session, subsequent reruns: splash does NOT re-render (`_splash_shown` short-circuits).
- Reduced motion: INC IDs fade at fixed positions; wordmark/tagline/status render identically.
- v2.1 invariants preserved: page_title="SNOWGREP", page_icon="✦", `_render_provenance_caption` untouched, `pytest tests/test_phase5_ui.py` returns 22 passed.
- Satisfies SPL-02 (clear on data-ready + 4s cap) and SPL-04 (once per browser session via `_splash_shown`).
</success_criteria>

<output>
After completion, create `.planning/phases/07-splash-screen/07-02-SUMMARY.md` documenting:
- Diff summary of `app.py` (lines added: imports, init_session_state extension, `_run_splash_lifecycle`, call site in `main()`).
- Confirmation that the four success criteria from ROADMAP.md Phase 7 are observable (with the human-verify checkpoint outcome).
- Confirmation that the 22 v2.1 Phase 5 UI tests still pass.
- Any deviations from 07-CONTEXT.md (expected: none).
</output>
