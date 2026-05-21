---
phase: 5
plan: 2
name: sidebar-selectbox-and-warning
type: execute
wave: 2
depends_on: [1]
files_modified:
  - app.py
autonomous: true

must_haves:
  truths:
    - "Sidebar contains st.selectbox with label exactly 'LLM provider' and options exactly ['Azure OpenAI', 'Anthropic Claude (MGTI)']"
    - "On first session, st.session_state['llm_provider'] is initialized from os.getenv('LLM_PROVIDER_DEFAULT') with clamp-to-known-value defense against typos / unknown values"
    - "Active model name is displayed read-only beneath the selectbox via st.caption with backticked model string"
    - "When the selected provider has missing required env vars, st.warning is rendered inline in the sidebar naming each missing variable, AND st.session_state['_llm_provider_blocked'] is set True"
    - "When blocked, st.chat_input is rendered with disabled=True and the placeholder swaps to 'QUERY DISABLED — see sidebar warning'"
    - "Selecting a known provider with all env vars set clears the blocked flag — chat_input becomes interactive again on the next rerun"
    - "main() preserves the load-bearing order: render_sidebar() runs BEFORE render_main_content() so the blocked flag is set before chat_input reads it"
    - "Existing sidebar blocks (DATA INGEST, DATA STATUS, EMBEDDINGS, CONFIG) and existing main-content widgets are untouched — pure additive change"
  artifacts:
    - path: "app.py"
      provides: "Sidebar LLM PROVIDER block + chat_input disable wiring"
      contains: "LLM PROVIDER"
  key_links:
    - from: "app.py render_sidebar"
      to: "src.llm.missing_vars"
      via: "imported and called per rerun to decide warning + blocked flag"
      pattern: "from src\\.llm import.*missing_vars|missing_vars\\("
    - from: "app.py render_sidebar"
      to: "st.session_state['_llm_provider_blocked']"
      via: "set True when missing list non-empty, False otherwise"
      pattern: "_llm_provider_blocked"
    - from: "app.py render_main_content"
      to: "st.session_state['_llm_provider_blocked']"
      via: "read at st.chat_input call site to set disabled="
      pattern: "disabled=.*_llm_provider_blocked|disabled=blocked"
    - from: "app.py PROVIDER_OPTIONS dict"
      to: "src.llm._REGISTRY keys"
      via: "internal values MUST be 'azure_openai' and 'anthropic_mgti' — match _REGISTRY"
      pattern: "azure_openai.*anthropic_mgti|anthropic_mgti.*azure_openai"
---

<objective>
Add the `LLM PROVIDER` block to `app.py`'s `render_sidebar()` function — `st.selectbox` with label `"LLM provider"`, the two locked options, session-state initialization from `LLM_PROVIDER_DEFAULT` (with clamp-to-known defense), active-model `st.caption` beneath, inline `st.warning` when env vars are missing, and `st.session_state["_llm_provider_blocked"]` flag — and wire `st.chat_input` in `render_main_content()` to honor that flag via `disabled=` + a swapped placeholder.

Purpose: This is the user-visible half of Phase 5 (SC #1, SC #2, SC #3, SC #4-partial). The block lives between EMBEDDINGS and CONFIG per RESEARCH.md Recommendation 1 (top-level, visible without expander click — the missing-creds warning must be inline per SC #3). The blocked-flag pattern decouples the sidebar render from the main-content render so they communicate through session_state alone — no parameter ripple, no function-signature changes.

Output: One file modified (`app.py`); three contributions — (1) a new sidebar section between lines ~547 and ~550, (2) a chat_input modification at line ~876, (3) a load-bearing comment in `main()` flagging the sidebar-before-main order.
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-CONTEXT.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-RESEARCH.md

# This plan depends on Plan 05-01's outputs
@.planning/phases/05-sidebar-ui-toggle-documentation/05-01-SUMMARY.md

# Files modified
@app.py

# Reference: existing sidebar patterns in render_sidebar() at app.py:402-571
# Reference: existing chat_input call at app.py:876
# Reference: main() entry point at app.py:921
</context>

<decisions>
## Decisions locked for this plan

1. **Locked UI strings (NON-DISCRETIONARY — from ROADMAP SC #1 and CONTEXT.md):**
   - Selectbox label: `"LLM provider"` — EXACT spelling, lowercase "provider", single space.
   - Option 1 label: `"Azure OpenAI"` — exact spelling.
   - Option 2 label: `"Anthropic Claude (MGTI)"` — exact spelling, parens around MGTI.
   - Internal keys: `"azure_openai"`, `"anthropic_mgti"` — MUST match `_REGISTRY` in `src/llm/__init__.py`.

2. **Position in sidebar: between EMBEDDINGS and CONFIG.** Resolves RESEARCH Open Question #2. Concrete insertion point: AFTER `st.divider()` at `app.py:547` and BEFORE `st.markdown("### CONFIG")` at `app.py:550`. The block is `st.markdown("### LLM PROVIDER")` + the selectbox + caption + warning + blocked-flag set, followed by ONE `st.divider()` (so the divider count above `### CONFIG` becomes the new divider this block adds). NET: one extra `st.divider()` is added between LLM PROVIDER and CONFIG; the existing `st.divider()` at line 547 stays in place as the EMBEDDINGS-vs-LLM-PROVIDER separator.

3. **Module-level constants for the option mapping:**
   ```python
   _PROVIDER_OPTIONS = {
       "Azure OpenAI": "azure_openai",
       "Anthropic Claude (MGTI)": "anthropic_mgti",
   }
   _PROVIDER_LABELS = {v: k for k, v in _PROVIDER_OPTIONS.items()}
   _PROVIDER_KEYS = tuple(_PROVIDER_OPTIONS.values())  # ("azure_openai", "anthropic_mgti")
   ```
   Place these at module scope NEAR the existing `MODE_OPTIONS` dict (around `app.py:355`) so all UI option mappings live together. Underscore prefix marks them internal to `app.py`. **The dict insertion order matters** — Azure first so the default selectbox index points at it.

4. **Session-state initialization with clamp-to-known defense** (RESEARCH.md Pitfall 2): the FIRST thing the LLM PROVIDER block does is initialize `st.session_state["llm_provider"]` if absent. The init reads `os.getenv("LLM_PROVIDER_DEFAULT", "azure_openai")`, strips whitespace, and clamps to `_PROVIDER_KEYS` (falling back to `"azure_openai"` on any mismatch, with a `logger.warning` to surface the typo). The selectbox's `index=...` calculation is therefore guaranteed safe (no `ValueError`).

5. **Selectbox `key=` is intentionally omitted.** Streamlit's `st.selectbox` allows a `key=` for direct session_state binding, but using `index=...` + manual write-back is more readable here and consistent with the existing `MODE` selectbox pattern at `app.py:862-869`. Pattern locked.

6. **Active-model caption format:** `st.caption(f"MODEL: \`{active_model or 'NOT CONFIGURED'}\`")` — matches the brutalist uppercase-label convention. The model is read via `load_settings()` for the currently selected provider (NOT via `get_llm()` — calling `get_llm()` in the sidebar would resolve a fresh adapter on every rerun, side-effecting startup logs; reading `load_settings()` is pure I/O). When the provider is unconfigured (`missing` non-empty), the model may be `""` — show `NOT CONFIGURED`.

7. **`missing_vars()` is called every rerun.** RESEARCH.md Pitfall 10 confirms `os.getenv` is O(1) — acceptable cost. Do NOT cache `missing_vars()` with `@st.cache_data` — that would defeat the purpose of detecting credential additions between runs (user populates `.env`, hits Ctrl-R, expects the warning to vanish).

8. **Warning rendering (RESEARCH Recommendation 2 verbatim):**
   ```python
   missing = missing_vars(st.session_state["llm_provider"])
   if missing:
       human_name = _PROVIDER_LABELS[st.session_state["llm_provider"]]
       missing_str = ", ".join(f"`{v}`" for v in missing)
       st.warning(
           f"**{human_name}** is not configured. Missing env vars: {missing_str}.\n\n"
           f"Add them to your `.env` and restart the app, or switch back to Azure OpenAI above.",
           icon=":material/warning:",
       )
       st.session_state["_llm_provider_blocked"] = True
   else:
       st.session_state["_llm_provider_blocked"] = False
   ```
   - `st.warning` (NOT `st.error` / `st.info`) — matches existing usage at `app.py:664` (chart feedback). Severity rationale in RESEARCH.md §2.
   - The warning text MUST name each missing variable with backticks (RESEARCH.md: "Naming env-var-specific warnings ... lets the user copy-paste the missing variable name").
   - The warning text MUST include the two recovery paths: add to `.env`+restart, OR switch back.
   - `icon=":material/warning:"` is the Streamlit Material-icon syntax (verified in Streamlit 1.40+). If for any reason this renders poorly in the deployed version, an emoji fallback `icon="⚠️"` is acceptable.

9. **`st.chat_input` disable pattern (RESEARCH.md §2 + Pitfall 3):**
   ```python
   blocked = st.session_state.get("_llm_provider_blocked", False)
   placeholder = "ENTER QUERY..." if not blocked else "QUERY DISABLED — see sidebar warning"
   if user_query := st.chat_input(placeholder, disabled=blocked):
       ...
   ```
   - `disabled=` is the documented Streamlit primitive (verified in Streamlit 1.52.1).
   - Placeholder swap is mandatory (Pitfall 3) — otherwise users don't realize they're blocked.
   - `st.session_state.get("_llm_provider_blocked", False)` defaults to `False` if the key is missing — defensive against first-render-before-sidebar-ran. (Cannot happen under normal flow since `main()` calls `render_sidebar()` first, but the `.get(..., False)` is cheap insurance.)

10. **Load-bearing order comment in `main()`** (RESEARCH.md Pitfall 5): add a one-line comment above `render_sidebar()` in `main()` flagging that the sidebar MUST render before main content. Concretely:
    ```python
    def main():
        """Main application entry point."""
        init_session_state()
        # ORDER IS LOAD-BEARING: render_sidebar() writes
        # st.session_state["_llm_provider_blocked"] which render_main_content()
        # reads at the st.chat_input call site. Reversing this order would
        # leak stale "blocked" state across reruns (Phase 5 RESEARCH.md Pitfall 5).
        render_sidebar()
        render_main_content()
    ```

11. **NO `get_llm()` calls in `render_sidebar`.** The sidebar reads provider metadata via `load_settings()` only. Calling `get_llm()` would (a) trigger `@st.cache_resource` resolution unnecessarily, (b) write a startup log line on every rerun if the cache invalidated for some reason, (c) couple sidebar render to provider construction. The first `get_llm()` call still happens at the existing `query_router` / `sql_generator` call sites — Phase 2 contract preserved.

12. **NO new dependencies.** `os`, `logging` are already imported in `app.py`. Pull `missing_vars` from `src.llm` (Plan 05-01 re-exported it).

13. **Imports to add to `app.py`:**
    - `from src.llm import missing_vars, load_settings` — `load_settings` is needed for the active-model display.
    - Existing `import os` is already at the top; verify.
    - **Note for Plan 05-03:** This module-level `from src.llm import ...` line is the ONLY src.llm import line in `app.py`. Plan 05-03 (Wave 3) will EXTEND this same line to add `get_llm` (per Plan 05-03 decision §14, Option B). Do NOT create a second `from src.llm import ...` line and do NOT add `get_llm` here — Plan 05-03 owns that extension.

14. **Test plan integration:** Plan 05-05 (acceptance gate) will test this with `unittest.mock.patch('streamlit.selectbox', ...)`, `patch('streamlit.warning', ...)`, etc. The render functions are NOT refactored to take dependency-injected arguments — testing happens via `patch` against the `streamlit` module. Code under test is the function bodies of `render_sidebar` and `render_main_content`.

15. **`render_main_content` is NOT renamed/restructured.** Only TWO lines change in it (`app.py:875-876` area): the `st.chat_input` call with `disabled=` and the placeholder swap. All other render_main_content logic is untouched.

16. **No deletion of any existing widget.** Pure additive.
</decisions>

<tasks>

<task type="auto">
  <name>Task 2.1: Add module-level provider option dicts + imports + LLM PROVIDER sidebar block</name>
  <files>app.py</files>
  <action>
**Goal:** Add the new sidebar block — selectbox, model caption, warning, blocked-flag. Initialize session_state with clamp-to-known defense.

**Step 1 — Imports:** Add to the existing `from src.llm import ...` block (or add a new import line if none exists). Confirm the final import line includes both names:

```python
from src.llm import missing_vars, load_settings
```

(If `app.py` already imports from `src.llm`, append the names; if not, add the line near the other `from src...` imports. Per locked decision §13, do NOT include `get_llm` here — Plan 05-03 owns that extension.)

**Step 2 — Module-level constants** near the existing `MODE_OPTIONS` dict at `app.py:354-358`. Insert AFTER `MODE_OPTIONS` and BEFORE the next function definition:

```python
# Phase 5: LLM provider selectbox option mapping.
# Display labels (left) → internal _REGISTRY keys (right). MUST match the keys
# in src/llm/__init__.py::_REGISTRY exactly. Insertion order = selectbox order:
# Azure first so the default-selected option is the existing behavior.
_PROVIDER_OPTIONS: dict[str, str] = {
    "Azure OpenAI": "azure_openai",
    "Anthropic Claude (MGTI)": "anthropic_mgti",
}
_PROVIDER_LABELS: dict[str, str] = {v: k for k, v in _PROVIDER_OPTIONS.items()}
_PROVIDER_KEYS: tuple[str, ...] = tuple(_PROVIDER_OPTIONS.values())  # ("azure_openai", "anthropic_mgti")
```

**Step 3 — Insert the LLM PROVIDER block** in `render_sidebar()` AFTER the EMBEDDINGS-block-closing `st.divider()` (currently `app.py:547`) and BEFORE `st.markdown("### CONFIG")` (currently `app.py:550`). Insert this verbatim:

```python
        # ---------- LLM PROVIDER (Phase 5) ----------
        st.markdown("### LLM PROVIDER")

        # Initialize session_state on first render. Clamp unknown values to
        # azure_openai (defense against typos in LLM_PROVIDER_DEFAULT — RESEARCH.md
        # Pitfall 2). The .strip() handles trailing whitespace.
        if "llm_provider" not in st.session_state:
            default = os.getenv("LLM_PROVIDER_DEFAULT", "azure_openai").strip()
            if default not in _PROVIDER_KEYS:
                logger.warning(
                    f"LLM_PROVIDER_DEFAULT={default!r} not in {_PROVIDER_KEYS}; "
                    f"falling back to 'azure_openai'"
                )
                default = "azure_openai"
            st.session_state["llm_provider"] = default

        # Selectbox: locked label "LLM provider"; options exactly ["Azure OpenAI",
        # "Anthropic Claude (MGTI)"]; index resolved from current session_state so
        # reruns preserve the selection. Help text matches the one-sentence
        # convention used elsewhere in render_sidebar().
        selected_label = st.selectbox(
            "LLM provider",
            options=list(_PROVIDER_OPTIONS.keys()),
            index=_PROVIDER_KEYS.index(st.session_state["llm_provider"]),
            help="Which LLM serves classification, SQL generation, and executive summaries. Default is Azure OpenAI.",
        )
        st.session_state["llm_provider"] = _PROVIDER_OPTIONS[selected_label]

        # Read-only active-model caption beneath the selector. Use load_settings()
        # NOT get_llm() — sidebar render must not side-effect adapter construction
        # or startup logs (Plan 05-02 decision §11).
        _settings = load_settings()
        if st.session_state["llm_provider"] == "azure_openai":
            # Azure: extract deployment from endpoint URL the same way the adapter does.
            from src.llm.azure_openai import _extract_model_from_endpoint
            _active_model = _extract_model_from_endpoint(_settings.azure_endpoint) if _settings.azure_endpoint else ""
        else:
            _active_model = _settings.anthropic_model
        st.caption(f"MODEL: `{_active_model or 'NOT CONFIGURED'}`")

        # Missing-creds warning + blocked-flag set. Called every rerun — cheap
        # (os.getenv is O(1)). Do NOT @st.cache_data this — adding env vars
        # between runs must invalidate immediately (RESEARCH.md Pitfall 10).
        _missing = missing_vars(st.session_state["llm_provider"])
        if _missing:
            _human_name = _PROVIDER_LABELS[st.session_state["llm_provider"]]
            _missing_str = ", ".join(f"`{v}`" for v in _missing)
            st.warning(
                f"**{_human_name}** is not configured. Missing env vars: {_missing_str}.\n\n"
                f"Add them to your `.env` and restart the app, or switch back to Azure OpenAI above.",
                icon=":material/warning:",
            )
            st.session_state["_llm_provider_blocked"] = True
        else:
            st.session_state["_llm_provider_blocked"] = False

        st.divider()

        # ---------- CONFIG (existing) ----------
```

The closing `st.divider()` is added by THIS block (separating LLM PROVIDER from CONFIG). The existing `st.divider()` at line 547 stays in place (separating EMBEDDINGS from LLM PROVIDER).

**Step 4 — verify `logger` is in scope.** Search `app.py` for `logger =` or `import logging`. The existing pattern (e.g. `app.py:388-394` uses `logger.info(...)`) confirms it. Use that same `logger`.

**Step 5 — do NOT modify any other sidebar code.** EMBEDDINGS block, CONFIG block, DATA INGEST block all stay exactly as they are.
  </action>
  <verify>
```bash
# Module-level dicts present
grep -nE "_PROVIDER_OPTIONS|_PROVIDER_LABELS|_PROVIDER_KEYS" app.py
# Expected: 6+ matches (3 def lines + use sites in render_sidebar)

# Locked label and options present verbatim
grep -nE '"LLM provider"' app.py
# Expected: ≥1 match
grep -nE '"Azure OpenAI"' app.py
# Expected: ≥1 match (the _PROVIDER_OPTIONS dict)
grep -nE '"Anthropic Claude \(MGTI\)"' app.py
# Expected: ≥1 match

# session_state initialization with clamp
grep -nE 'st\.session_state\["llm_provider"\] = default' app.py
grep -nE 'LLM_PROVIDER_DEFAULT' app.py
# Expected: both present

# Caption with backticked model
grep -nE 'MODEL: `' app.py
# Expected: ≥1 match

# Warning with missing vars and recovery paths
grep -nE 'st\.warning\(' app.py | grep -iE 'not configured|missing'
# Expected: ≥1 match

# Blocked flag set
grep -nE '_llm_provider_blocked' app.py
# Expected: ≥2 matches (True branch, False branch)

# Imports added
grep -nE 'from src\.llm import' app.py | grep -E 'missing_vars|load_settings'
# Expected: both names imported
# (get_llm is NOT in this line yet — Plan 05-03 will extend it)

# Streamlit syntax check via Python import (catches typos that would crash render_sidebar)
python -c "
import ast, sys
with open('app.py') as f:
    src = f.read()
ast.parse(src)
print('app.py parses cleanly')
"
# Expected: app.py parses cleanly

# Existing chat_input call still PRESENT (Task 2.2 will modify it):
grep -nE 'st\.chat_input\("ENTER QUERY' app.py
# Expected: 1 match — Task 2.2 modifies this; this verification confirms Task 2.1
# did NOT accidentally delete it.

# Suite still green
pytest tests/ -v --tb=short
# Expected: 69 passed (no behavior change for non-UI tests; render_sidebar is
# only exercised by Plan 05-05's mocks)
```
  </verify>
  <done>
`app.py` has module-level `_PROVIDER_OPTIONS`, `_PROVIDER_LABELS`, `_PROVIDER_KEYS` near the existing `MODE_OPTIONS`. `render_sidebar()` contains a new `### LLM PROVIDER` block between EMBEDDINGS and CONFIG with the locked label, options, session-state init (clamp-to-known), index-driven selectbox, model caption, missing-vars warning naming each missing variable, and `_llm_provider_blocked` flag. Imports for `missing_vars` and `load_settings` are present (single `from src.llm import ...` line — Plan 05-03 will extend it to add `get_llm`). `app.py` parses cleanly. All 69 prior tests still pass.
  </done>
</task>

<task type="auto">
  <name>Task 2.2: Wire st.chat_input to honor _llm_provider_blocked + load-bearing comment in main()</name>
  <files>app.py</files>
  <action>
**Goal:** Honor the sidebar's blocked-flag in the chat input. Swap placeholder text when blocked. Add a comment to `main()` documenting the load-bearing sidebar-before-main-content order.

**Step 1 — Modify `render_main_content` around `app.py:876`.** The current line is approximately:

```python
    # Query input
    if user_query := st.chat_input("ENTER QUERY..."):
```

Replace these two lines with:

```python
    # Query input
    # Phase 5: honor sidebar's missing-creds blocked flag — disable chat input
    # and swap placeholder so users see WHY they can't submit. The blocked flag
    # is set by render_sidebar() on every rerun (Phase 5 RESEARCH.md Pitfall 5
    # — order is load-bearing; see main()).
    _blocked = st.session_state.get("_llm_provider_blocked", False)
    _placeholder = "ENTER QUERY..." if not _blocked else "QUERY DISABLED — see sidebar warning"
    if user_query := st.chat_input(_placeholder, disabled=_blocked):
```

The `_blocked` underscore prefix marks it as a local variable (consistent with `_settings`, `_active_model` etc. from Task 2.1). The `.get(..., False)` defaults safely if the key is absent (first run, edge cases) — chat_input remains interactive in that case.

**Step 2 — Add load-bearing comment to `main()`** (currently at `app.py:921-925`). Replace the existing function:

```python
def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main_content()
```

With:

```python
def main():
    """Main application entry point.

    ORDER IS LOAD-BEARING: render_sidebar() must run BEFORE render_main_content()
    because the sidebar writes st.session_state["_llm_provider_blocked"] which
    render_main_content() reads at the st.chat_input call site. Reversing the
    order would leak stale blocked state across reruns (Phase 5 SC #3 + RESEARCH
    Pitfall 5).
    """
    init_session_state()
    render_sidebar()
    render_main_content()
```

The docstring is the right place for this — easy to find via tooling and stable across diffs.

**Step 3 — verify no other `st.chat_input` calls exist.** Grep:

```bash
grep -nE "st\.chat_input" app.py
```

Expected: ONE match — the one we just modified. If there are others (alternate code paths, e.g. an early-return path that also calls `st.chat_input`), they MUST also honor `_blocked` — but RESEARCH.md confirmed only one call site exists.

**Step 4 — do NOT modify the user-message append, the assistant `with st.chat_message("assistant"):` block, the `process_query()` call, or any other rendering logic.** Those are Plan 05-03 territory.

**Step 5 — Streamlit signature check.** Plan 05-01 already confirmed `st.chat_input(placeholder, disabled=...)` is valid in Streamlit 1.40+ (live env 1.52.1 — RESEARCH.md §Codebase Context). No version pin change needed.
  </action>
  <verify>
```bash
# Chat input now uses disabled= and the placeholder var
grep -nE 'st\.chat_input\(_placeholder, disabled=_blocked\)' app.py
# Expected: 1 match

# Old chat_input pattern is GONE (no orphan call without disabled=)
grep -nE 'st\.chat_input\("ENTER QUERY\.\.\."\)' app.py
# Expected: 0 matches

# Only ONE chat_input call site exists (no alternate paths missed)
grep -cE 'st\.chat_input\(' app.py
# Expected: 1

# main() comment present and order preserved
grep -nE "ORDER IS LOAD-BEARING" app.py
# Expected: 1 match

# Order check: render_sidebar before render_main_content in main()
python -c "
import re
with open('app.py') as f:
    src = f.read()
m = re.search(r'def main\(\):.*?if __name__', src, re.DOTALL)
body = m.group(0)
i1 = body.find('render_sidebar()')
i2 = body.find('render_main_content()')
assert i1 != -1 and i2 != -1, 'both calls must be present'
assert i1 < i2, 'render_sidebar must precede render_main_content (Pitfall 5)'
print('order OK')
"
# Expected: order OK

# Full parse still clean
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
# Expected: OK

# Suite still green
pytest tests/ -v --tb=short
# Expected: 69 passed
```
  </verify>
  <done>
`st.chat_input` is called with `(_placeholder, disabled=_blocked)`; `_blocked` reads `st.session_state.get("_llm_provider_blocked", False)`; `_placeholder` swaps between `"ENTER QUERY..."` (unblocked) and `"QUERY DISABLED — see sidebar warning"` (blocked). The old `st.chat_input("ENTER QUERY...")` line is gone — no orphan call without disabled. `main()` has a docstring noting the load-bearing render_sidebar-before-render_main_content order. Only ONE chat_input call site exists in `app.py`. `app.py` parses cleanly. All 69 prior tests still pass.
  </done>
</task>

</tasks>

<verification>
Plan-level verification:

1. **Only `app.py` is modified:**
   ```bash
   git diff --stat HEAD -- .
   # Expected: ONLY app.py
   ```

2. **Locked UI strings present verbatim:**
   ```bash
   grep -nE '"LLM provider"' app.py
   grep -nE '"Azure OpenAI"' app.py
   grep -nE '"Anthropic Claude \(MGTI\)"' app.py
   # All three: ≥1 match
   ```

3. **session_state["llm_provider"] init from env with clamp:**
   ```bash
   grep -nE 'os\.getenv\("LLM_PROVIDER_DEFAULT"' app.py
   grep -nE 'if default not in _PROVIDER_KEYS' app.py
   # Both: 1 match
   ```

4. **Caption + warning + blocked flag wired:**
   ```bash
   grep -cE 'st\.caption\(f"MODEL:' app.py
   grep -cE 'st\.warning\(' app.py
   grep -cE '_llm_provider_blocked' app.py
   # Caption: ≥1; warning: ≥2 (Task 2.1 + existing usage at line ~664); blocked: ≥3
   ```

5. **chat_input uses disabled=:**
   ```bash
   grep -nE 'disabled=_blocked' app.py
   # Expected: 1 match
   ```

6. **main() order load-bearing comment:**
   ```bash
   grep -nE "ORDER IS LOAD-BEARING" app.py
   # Expected: 1 match
   ```

7. **No other src/ or doc files touched:**
   ```bash
   git diff --stat HEAD -- src/ scripts/ tests/ README.md USER_GUIDE.md .env.example
   # Expected: ZERO output (this plan touches only app.py)
   ```

8. **Test suite still green:**
   ```bash
   pytest tests/ -v --tb=short
   # Expected: 69 passed
   ```

9. **Manual smoke (operator-runnable):**
   ```bash
   # In a Streamlit run, navigate to the sidebar. Verify:
   # - "### LLM PROVIDER" header is visible between EMBEDDINGS and CONFIG
   # - The selectbox has label "LLM provider" and the two options
   # - "MODEL: `..." caption is visible under the selector
   # - With one Anthropic var unset, the orange warning appears naming that var
   # - The chat input is greyed out and shows "QUERY DISABLED — see sidebar warning"
   # - Switching back to Azure OpenAI clears the warning and re-enables chat_input
   # This manual verification is the Phase 5 verification PR's responsibility — not
   # a blocker for Plan 05-02 done, but Plan 05-05 (acceptance gate) covers it via mocks.
   ```
</verification>

<success_criteria>
- [ ] Module-level `_PROVIDER_OPTIONS`, `_PROVIDER_LABELS`, `_PROVIDER_KEYS` exist near `MODE_OPTIONS`
- [ ] `render_sidebar()` has an `### LLM PROVIDER` block between EMBEDDINGS and CONFIG
- [ ] Block initializes `st.session_state["llm_provider"]` from `LLM_PROVIDER_DEFAULT` with `.strip()` + clamp-to-`_PROVIDER_KEYS` + `logger.warning` on unknown value
- [ ] `st.selectbox` uses label exactly `"LLM provider"`, options `["Azure OpenAI", "Anthropic Claude (MGTI)"]`, index-driven from session_state
- [ ] Active model displayed via `st.caption(f"MODEL: \`{...}\`")`; sources value from `load_settings()` (NOT `get_llm()`)
- [ ] `missing_vars()` called every rerun; on non-empty list, `st.warning` names each missing variable with backticks AND mentions both recovery paths (add to `.env` / switch back); `_llm_provider_blocked=True` set
- [ ] `_llm_provider_blocked=False` set when `missing_vars()` returns `[]`
- [ ] `st.chat_input` reads `_blocked` from session_state, passes `disabled=_blocked`, swaps placeholder to `"QUERY DISABLED — see sidebar warning"` when blocked
- [ ] `main()` docstring documents load-bearing sidebar-before-main-content order
- [ ] Module-level `from src.llm import ...` line includes exactly `missing_vars` and `load_settings` (Plan 05-03 will extend it to add `get_llm`)
- [ ] No deletions of existing sidebar blocks or main-content widgets
- [ ] Only `app.py` modified — no src/, no tests/, no docs touched in this plan
- [ ] Full 69-test suite still green
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-02-SUMMARY.md` documenting:
- Lines modified in `app.py` (block insertion line, chat_input line, main() docstring)
- The exact strings now present (label, options, warning template, placeholder texts)
- Confirmation: only `app.py` modified; `_REGISTRY` keys match selectbox internal values
- The module-level `from src.llm import ...` line as written (so Plan 05-03 knows what to extend)
- 69-test suite still green
- Unblocks: Plan 05-03 (will extend the import line + read `_PROVIDER_LABELS`), Plan 05-05 (acceptance gate can now test the sidebar behavior via mocks)
</output>
</output>
