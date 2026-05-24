# Phase 10: Polish + Edge States - Research

**Researched:** 2026-05-23
**Domain:** Streamlit DOM emission, Python module structure, loading lifecycle
**Confidence:** HIGH (all findings sourced from installed source files and live code)

## Summary

All six focus areas investigated against installed source. The most important finding is that CONTEXT.md's proposed `stAlertContentSuccess/Error/Warning/Info` testid shape is CORRECT for Streamlit 1.52.1, but the CONTEXT.md name for the icon testid is slightly wrong: the installed version uses `stAlertDynamicIcon` (not `stAlertContentIcon`). The icon node only renders when `icon=` is passed to the alert call — none of the project's six callsites pass `icon=`, so the icon suppress CSS is a safety net only.

The `_render_empty_state` collision concern from CONTEXT.md is resolved: the existing function in `results.py` handles the 0-rows query case ("NO RESULTS"), not the no-CSV case. POL-01's empty card is a new, distinct surface with a new function name (`_render_empty_card`) and different CSS class (`.lp-empty-card`). No collision.

All three loading callsites complete within a single Streamlit rerun — local-scope `st.empty()` handles are sufficient; no `st.session_state` storage needed for Phase 10 loading indicators.

**Primary recommendation:** Proceed as CONTEXT.md specifies. Lock the correct icon testid (`stAlertDynamicIcon`) and confirm the icon suppress rule targets it rather than the non-existent `stAlertContentIcon`.

---

## 1. Streamlit Alert Testid Shape (CRITICAL)

### What I verified

Installed version: **Streamlit 1.52.1** (requirements.txt pins `>=1.40.0`; installed is 1.52.1).

Inspected the compiled frontend bundle at:
`C:\Python313\Lib\site-packages\streamlit\static\static\js\index.CqTPbV5Y.js`

Relevant `AlertElement` function verbatim from bundle:
```
function AlertElement({icon:n,body:o,kind:e}){
  ...
  return jsx$1("div",{className:"stAlert","data-testid":"stAlert",
    children:jsx$1(AlertContainer,{kind:e,
      children:jsxs(StyledAlertContent,{children:[
        n&&jsx$1(StyledAlertIcon,{
          children:jsx$1(DynamicIcon,{iconValue:n,size:"lg",testid:"stAlertDynamicIcon"})
        }),
        jsx$1(StreamlitMarkdown$1,{source:o,allowHTML:!1,style:c})
      ]})
    })
  })
}
```

`AlertContainer` sets `data-testid="stAlertContainer"` on the BaseWeb Notification body.

`StyledAlertContent$1` (inside `AlertContainer`) renders: `data-testid=\`stAlertContent${c}\`` where `c = n.charAt(0).toUpperCase() + n.slice(1)` and `n` is the kind string.

Kind string mapping (from bundle):
- `"error"` → `c = "Error"` → testid = `stAlertContentError`
- `"info"` → `c = "Info"` → testid = `stAlertContentInfo`
- `"success"` → `c = "Success"` → testid = `stAlertContentSuccess`
- `"warning"` → `c = "Warning"` → testid = `stAlertContentWarning`

Icon node: `data-testid="stAlertDynamicIcon"` — rendered **only** when `icon=` is passed to the Python call. None of the 6 project callsites pass `icon=` (verified in app.py lines 133, 138, 146, 194, 455, 461). The icon node is absent from the DOM at runtime for this project.

Full DOM hierarchy for a project alert call:
```
div.stAlert[data-testid="stAlert"]
  └─ [data-testid="stAlertContainer"]        ← BaseWeb Notification body
     └─ StyledAlertContent (no testid)        ← inner flex wrapper
        └─ [data-testid="stAlertContent{Kind}"]  ← text content wrapper
```

### Lock for planner

- Outer wrapper selector: `[data-testid="stAlert"]` — CONFIRMED
- Kind-specific content selector: `[data-testid="stAlertContentSuccess"]`, `[data-testid="stAlertContentError"]`, `[data-testid="stAlertContentWarning"]`, `[data-testid="stAlertContentInfo"]` — CONFIRMED (capital first letter)
- Container selector: `[data-testid="stAlertContainer"]` — exists, for structural overrides
- Icon testid: `stAlertDynamicIcon` (NOT `stAlertContentIcon` as CONTEXT.md states) — CORRECT THE CONTEXT.MD NAME
- Icon suppression selector: `[data-testid="stAlertDynamicIcon"]` — use this, not `[data-testid="stAlertContentIcon"]`
- Icon is absent from DOM in this project (no callsite passes `icon=`); the suppress rule is a safety net for future callers

### Open items

None. All testid strings confirmed from installed bundle source.

---

## 2. `_render_empty_state` Collision Check (HIGH)

### What I verified

Grepped `src/ui/results.py` and `app.py` for all occurrences.

**Existing `_render_empty_state()` in `src/ui/results.py` (lines 222–245):**
- Handles the **0-rows query result** case — a query ran and returned an empty DataFrame
- Returns HTML with class `.lp-et-empty`, label "NO RESULTS", body "No incidents matched your query. Try a different search or mode."
- Called at `app.py:551` inside `display_results()` when `df.empty`
- Imported at `app.py:31`: `from src.ui.results import _render_editorial_table, _render_empty_state, _render_chart_unavailable`

**POL-01 empty card (new):**
- Handles the **no CSV loaded** case — `not st.session_state.data_loaded`
- Called at `app.py:749–752` (currently just `return`; Phase 10 replaces with `st.markdown(EMPTY_CARD_HTML, unsafe_allow_html=True)`)
- CSS class: `.lp-empty-card` (new, not `.lp-et-empty`)
- HTML strings: "No data loaded" / "Upload incidents.csv from the sidebar to begin."
- Should be named `_render_empty_card()` to avoid name collision with existing function

**No collision exists** — they are entirely separate surfaces, separate callsites, separate CSS classes, different conditions.

### Lock for planner

- Existing `_render_empty_state()` — DO NOT MODIFY. It is the 0-rows Phase 9 renderer. Keep it.
- New function name: `_render_empty_card()` (distinct from `_render_empty_state`) — returns `.lp-empty-card` HTML
- POL-01 callsite: `app.py:749–752` — replace bare `return` with `st.markdown(_render_empty_card(), unsafe_allow_html=True); return`
- Import line to extend: `app.py:31` — add `_render_empty_card` to the import from `src.ui.results`
- CSS class namespace: `.lp-empty-card`, `.lp-empty-heading`, `.lp-empty-divider`, `.lp-empty-subtitle` — all new, no existing collisions

### Open items

None.

---

## 3. `_render_error_html` Home (MEDIUM)

### What I verified

`src/ui/results.py` current state:
- 276 lines total
- 3 public functions: `_render_editorial_table`, `_render_empty_state`, `_render_chart_unavailable`
- Module docstring explicitly declares its identity: "Editorial HTML renderers for SNOWGREP v2.2 results layer. Three pure-Python string builders. No Streamlit dependency — callers inject returned HTML via `st.markdown(html, unsafe_allow_html=True)`."
- All functions return strings; `st.markdown` lives at callsite. Consistent pattern.

`src/ui/` module inventory: `css.py`, `results.py`, `splash.py`, `altair_theme.py`. No `edge_states.py` exists.

Adding `_render_error_html` and `_render_empty_card` would bring results.py to ~340 lines with 5 functions. All five are editorial HTML renderers with no Streamlit dependency. Cohesion is maintained and improves (single module = single import line extension).

A new `src/ui/edge_states.py` would require a new import line in `app.py:31` and split what is a unified pattern for no added clarity gain.

### Lock for planner

- `_render_error_html(msg: str, label: str = "ERROR") -> str` lives in `src/ui/results.py`
- `_render_empty_card() -> str` lives in `src/ui/results.py`
- No new `src/ui/edge_states.py` — extend `results.py`
- Extend `app.py:31` import to: `from src.ui.results import _render_editorial_table, _render_empty_state, _render_chart_unavailable, _render_empty_card, _render_error_html`
- `results.py` module docstring should be updated to reflect 5 renderers (not 3)
- `__all__` at line 276 should be extended with the two new names

### Open items

None.

---

## 4. `st.empty()` Placeholder Lifecycle for Loading Indicators (MEDIUM)

### What I verified

All three loading callsites analyzed:

**Callsite 1 — `app.py:126` (`_load_csv_data`):**
```python
def _load_csv_data(uploaded_file, append: bool = False):
    mode_text = "APPENDING" if append else "LOADING"
    with st.spinner(f"{mode_text} CSV DATA..."):
        try:
            schema = load_csv(uploaded_file, append=append)
            ...
            st.rerun()
        except Exception as e:
            st.error(format_error_message(e))
```
Pattern: single function call, all work inside `with st.spinner(...)` block, completes before rerun. **Single-rerun lifecycle.**

**Callsite 2 — `app.py:443,447` (`_build_embeddings_with_progress`):**
```python
def _build_embeddings_with_progress(force: bool = False):
    progress_bar = st.progress(0)
    status_text = st.empty()   # local variable, not session_state

    def progress_callback(progress: float, message: str):
        progress_bar.progress(progress)
        status_text.text(message.upper())

    try:
        stats = build_embeddings(force_rebuild=force, progress_callback=progress_callback)
        ...
        st.rerun()
    except Exception as e:
        st.error(format_error_message(e))
    finally:
        progress_bar.empty()
        status_text.empty()
```
Pattern: `status_text = st.empty()` is a **local variable** (not session_state). Cleared in `finally:`. Single-rerun lifecycle. Phase 10 replaces `status_text.text(message.upper())` with `status_text.markdown('<div class="lp-loading">BUILDING EMBEDDINGS…</div>', unsafe_allow_html=True)`.

**Callsite 3 — `app.py:811` (`render_main_content`):**
```python
with st.chat_message("assistant"):
    with st.spinner("PROCESSING..."):
        response = process_query(user_query, selected_mode)
    # response rendered after spinner exits
```
Pattern: `with st.spinner(...)` block wraps the entire `process_query` call. The spinner clears when the `with` block exits. **Single-rerun lifecycle.** Phase 10 replaces `with st.spinner(...)` with local `placeholder = st.empty()` → `placeholder.markdown(...)` → call `process_query` → `placeholder.empty()`.

**Comparison with Phase 7 splash (`_splash_placeholder`):**
The splash uses `st.session_state._splash_placeholder` because the placeholder must persist across multiple reruns — State 1 mounts it, State 2 (a different rerun) clears it. That is a cross-rerun lifecycle, which requires session_state storage.

None of the Phase 10 loading indicators need cross-rerun persistence. All three complete within the rerun they start.

### Lock for planner

- All three callsites: use **local-scope** `st.empty()` handles — NOT `st.session_state`
- Pattern for all three:
  ```python
  _loading = st.empty()
  _loading.markdown('<div class="lp-loading">ANALYZING…</div>', unsafe_allow_html=True)
  result = do_work()
  _loading.empty()
  ```
- `_build_embeddings_with_progress`: replace `status_text.text(message.upper())` with `status_text.markdown('<div class="lp-loading">BUILDING EMBEDDINGS…</div>', unsafe_allow_html=True)` — the local `status_text` variable IS the correct handle already; just change the render call. Do NOT add a session_state entry.
- `_load_csv_data`: create local `_loading = st.empty()` before `load_csv()`, clear after. Replace `with st.spinner(...)`.
- `app.py:811`: create local `_loading = st.empty()` in the `with st.chat_message("assistant"):` block, replace `with st.spinner("PROCESSING..."):`
- No new `st.session_state` keys needed for Phase 10 loading indicators

### Open items

None.

---

## 5. Streamlit Alert Default Icon Suppression and Phase 8 Material Symbols Safety (MEDIUM)

### What I verified

**Icon presence:** `stAlertDynamicIcon` only renders when `icon=` is passed to the Python call. All 6 project callsites (app.py:133, 138, 146, 194, 455, 461) omit `icon=`. The icon node **does not exist** in the DOM at runtime. Icon suppression CSS is a forward-compatibility safety net only.

**Phase 8 Material Symbols restoration scope:** The fix at `src/ui/css.py:280–289` is scoped to `[data-testid="stSidebar"] [class*="material-symbols"]` and similar. This is a **sidebar-only** rule.

**Main panel font override:** The main panel has no `[data-testid="stAppViewContainer"] *` universal wildcard rule — only element-targeted rules (`.stApp`, `.block-container`, etc.). There is NO universal `*` font-family override on the main panel that would clobber Material Symbols in main-panel alerts.

**Conclusion:** The Phase 8 SBR fix cannot interfere with POL-04 alert icon suppression because:
1. The SBR fix is sidebar-only
2. Main-panel alerts are not inside `[data-testid="stSidebar"]`
3. The icon node doesn't exist in the DOM anyway (no `icon=` callsites)

**Safe suppression selector for `stAlertDynamicIcon`:**
```css
[data-testid="stAlert"] [data-testid="stAlertDynamicIcon"] { display: none; }
```
This is safe — it only targets the icon node inside an alert wrapper, not Material Symbols elsewhere.

### Lock for planner

- Icon suppress selector: `[data-testid="stAlert"] [data-testid="stAlertDynamicIcon"] { display: none; }` — SAFE, no Phase 8 regression risk
- Do NOT use `[data-testid="stAlertContentIcon"]` — this testid does NOT EXIST in Streamlit 1.52.1 (CONTEXT.md had it wrong; the correct testid is `stAlertDynamicIcon`)
- Do NOT add `[class*="material-symbols"]` to the icon suppression CSS — unnecessary and risks sidebar regression if scope logic changes
- No additional Material Symbols restoration rule needed for Phase 10
- Alert palette override selectors in order of specificity (verified correct for 1.52.1):
  - Global override: `[data-testid="stAlert"]` — border-radius, padding
  - Kind-specific: `[data-testid="stAlertContentSuccess"]`, `[data-testid="stAlertContentError"]`, `[data-testid="stAlertContentWarning"]`, `[data-testid="stAlertContentInfo"]` — left border color + label simulation
  - Container override: `[data-testid="stAlertContainer"]` — background fill, border resets

### Open items

None — confirmed safe.

---

## 6. `@keyframes lp-pulse` Placement (TRIVIAL)

### What I verified

Searched `src/ui/css.py` for any existing `@keyframes`, `pulse`, or `animation` declarations:
- **Result:** Only one comment "no animation" (line 987, a hover comment). No `@keyframes` exists anywhere in `LORO_PIANA_CSS`.

Searched all of `src/` and `app.py` for `lp-pulse`, `pulse`, `@keyframes`:
- **Result:** `@keyframes` exists only in `src/ui/splash.py` (helix animations for the boot splash — `helix-drift-a`, `helix-drift-b`, `helix-fade`). These are inline in the splash HTML string, not in `LORO_PIANA_CSS`.

No existing pulse animation anywhere. No name collision risk.

`LORO_PIANA_CSS` in `src/ui/css.py` is the established single source of truth for all design token CSS (confirmed by Phase 6 principle, and every phase since has extended this string only). Adding `@keyframes lp-pulse` to `LORO_PIANA_CSS` is the correct placement.

`LORO_PIANA_CSS` ends at line 1079 (the closing `"""`). The `.lp-loading` class and `@keyframes lp-pulse` should be appended before the closing delimiter, in a `/* Phase 10 POL-02 */` block to match the annotation pattern used for Phase 9 blocks (e.g., `/* Phase 9 DVZ-01 */` at line 948).

### Lock for planner

- `@keyframes lp-pulse` goes in `src/ui/css.py` inside `LORO_PIANA_CSS` string — append before closing `"""`
- Name is `lp-pulse` — no collision
- Annotation header: `/* Phase 10 POL-02 — Loading indicator */`
- `.lp-error-card` / `.lp-empty-card` CSS also goes in `LORO_PIANA_CSS` with phase annotation headers
- Do NOT create a separate CSS slab or new file for Phase 10 additions
- Exact keyframe (opacity curve is visual-tuning; planner can use 0.5→1.0→0.5 as the default):
  ```css
  @keyframes lp-pulse {
    0%, 100% { opacity: 0.5; }
    50%       { opacity: 1.0; }
  }
  ```

### Open items

None.

---

## Planner Quick-Reference

### Installed version
- Streamlit: `1.52.1`

### Alert testid literals (Streamlit 1.52.1, CONFIRMED from bundle)
- `[data-testid="stAlert"]` — outer wrapper div
- `[data-testid="stAlertContainer"]` — BaseWeb notification body
- `[data-testid="stAlertContentSuccess"]` — success text wrapper
- `[data-testid="stAlertContentError"]` — error text wrapper
- `[data-testid="stAlertContentWarning"]` — warning text wrapper
- `[data-testid="stAlertContentInfo"]` — info text wrapper
- `[data-testid="stAlertDynamicIcon"]` — icon node (absent unless `icon=` passed; NOT `stAlertContentIcon`)

### CONTEXT.md correction
- WRONG: `[data-testid="stAlertContentIcon"]` — this testid does not exist in 1.52.1
- CORRECT: `[data-testid="stAlertDynamicIcon"]` — use this for icon suppression

### Function names
- `_render_empty_state() -> str` — EXISTING (Phase 9, 0-rows NO RESULTS) — DO NOT MODIFY
- `_render_empty_card() -> str` — NEW (Phase 10 POL-01, no-CSV state)
- `_render_error_html(msg: str, label: str = "ERROR") -> str` — NEW (Phase 10 POL-03)
- `_render_chart_unavailable(feedback: str) -> str` — EXISTING (Phase 9) — DO NOT MODIFY
- `_render_editorial_table(df: pd.DataFrame) -> str` — EXISTING (Phase 9) — DO NOT MODIFY

### File paths
- CSS: `src/ui/css.py` — extend `LORO_PIANA_CSS` string only
- Renderers: `src/ui/results.py` — add `_render_empty_card` and `_render_error_html`
- No new files to create in `src/ui/`
- Callsite: `app.py`

### CSS class names (new in Phase 10)
- `.lp-empty-card` — POL-01 empty state card container
- `.lp-empty-heading` — POL-01 "No data loaded" text
- `.lp-empty-divider` — POL-01 hairline divider (80px, centered)
- `.lp-empty-subtitle` — POL-01 "Upload incidents.csv…" text
- `.lp-loading` — POL-02 loading indicator
- `.lp-error-card` — POL-03 error card container
- `.lp-error-label` — POL-03 "ERROR" label
- `.lp-error-body` — POL-03 error message body
- `@keyframes lp-pulse` — POL-02 animation

### CSS class names (existing, no changes)
- `.lp-et-empty`, `.lp-et-empty-label`, `.lp-et-empty-body` — Phase 9 0-rows state (distinct from POL-01)
- `.lp-warn-card`, `.lp-warn-label`, `.lp-warn-body`, `.lp-warn-fix` — Phase 8 sidebar warning (template for `.lp-error-card`)

### Callsite mappings (Phase 10 loading indicators)
- `app.py:126` — `_load_csv_data`: replace `with st.spinner(f"{mode_text} CSV DATA..."):` with local `st.empty()` placeholder showing "LOADING DATA…"
- `app.py:443` — `_build_embeddings_with_progress`: `status_text = st.empty()` is already local; replace `status_text.text(message.upper())` with `status_text.markdown('<div class="lp-loading">BUILDING EMBEDDINGS…</div>', unsafe_allow_html=True)`
- `app.py:811` — `render_main_content`: replace `with st.spinner("PROCESSING..."):` with local placeholder showing "ANALYZING…"
- "QUERYING…" — NO callsite in Phase 10. Document as reserved string for future discrete SQL phase.

### Callsite mappings (Phase 10 error cards)
- `app.py:608` — replace `"content": "[ERR] NO DATA LOADED — UPLOAD CSV FIRST"` with `"content": _render_error_html("NO DATA LOADED — UPLOAD CSV FIRST")`
- `app.py:616` — replace `"content": "[ERR] NO EMBEDDINGS — BUILD VIA SIDEBAR"` with `"content": _render_error_html("NO EMBEDDINGS — BUILD VIA SIDEBAR")`
- `app.py:631` — replace `"content": f"[ERR] {result['error']}"` with `"content": _render_error_html(result['error'])`
- `app.py:718` — replace `"content": f"[ERR] {str(e)}"` with `"content": _render_error_html(f"Unexpected error: {e}")`
- Add outer try/except at `app.py:812` (wrapping `response = process_query(...)`) per CONTEXT.md — catches `QueryError` and `LLMError` before they reach generic handler

### Callsite mappings (Phase 10 empty card)
- `app.py:749` — `if not st.session_state.data_loaded:` block: replace bare `return` (line 752) with `st.markdown(_render_empty_card(), unsafe_allow_html=True); return`

### Import additions needed (app.py:31)
```python
from src.ui.results import (
    _render_editorial_table,
    _render_empty_state,
    _render_chart_unavailable,
    _render_empty_card,        # NEW Phase 10 POL-01
    _render_error_html,        # NEW Phase 10 POL-03
)
```

### Import additions needed (app.py — error classes for outer try/except)
```python
from src.utils import QueryError, ...  # QueryError already imported indirectly via query_router
from src.llm.errors import LLMError   # NEW import needed
```

### Locked strings (verbatim from CONTEXT.md, confirmed not to alter)
- POL-01 heading: `"No data loaded"` (EB Garamond 24px weight 300)
- POL-01 subtitle: `"Upload incidents.csv from the sidebar to begin."` (Inter 15px weight 400)
- POL-02 analyze: `"ANALYZING…"` (U+2026 ellipsis)
- POL-02 embeddings: `"BUILDING EMBEDDINGS…"` (U+2026 ellipsis)
- POL-02 data: `"LOADING DATA…"` (U+2026 ellipsis — 4th phrase, needed for parity)
- POL-02 reserved: `"QUERYING…"` (documented, no callsite in Phase 10)
- POL-03 label: `"ERROR"` (default)

### Placeholder lifecycle rule
- Use **local** `st.empty()` for all three Phase 10 loading indicators — NOT session_state
- Session_state placeholder is ONLY for cross-rerun lifecycle (Phase 7 splash pattern)
- All three Phase 10 indicators complete within their own rerun — local handles sufficient

### Phase annotations for css.py additions
- `/* Phase 10 POL-01 — Empty state (no CSV loaded) */`
- `/* Phase 10 POL-02 — Loading indicator */`
- `/* Phase 10 POL-03 — Error card */`
- `/* Phase 10 POL-04 — Alert palette overrides */`

### LLMError import path
- `from src.llm.errors import LLMError` — verified at `/c/mbrunoapp/snow_query/src/llm/errors.py:13`

### QueryError import path
- `from src.utils import QueryError` — verified at `/c/mbrunoapp/snow_query/src/utils.py:46`

---

## Sources

### PRIMARY (HIGH confidence — installed source files)
- `/c/Python313/Lib/site-packages/streamlit/static/static/js/index.CqTPbV5Y.js` — alert DOM structure, all testid strings
- `/c/Python313/Lib/site-packages/streamlit/elements/alert.py` — Python alert API, icon param behavior
- `/c/mbrunoapp/snow_query/src/ui/results.py` — existing renderer functions
- `/c/mbrunoapp/snow_query/src/ui/css.py` — existing CSS, Phase 8 Material Symbols rule scope
- `/c/mbrunoapp/snow_query/app.py` — all callsite line numbers and lifecycle patterns

### Metadata
- **Research date:** 2026-05-23
- **Valid until:** 2026-06-23 (Streamlit 1.52.1 pinned; alert DOM stable across patch versions)
- **Standard stack confidence:** HIGH — sourced from installed bundle, not documentation
- **Architecture confidence:** HIGH — sourced from live code
- **Pitfalls confidence:** HIGH — all verified from actual installed state
