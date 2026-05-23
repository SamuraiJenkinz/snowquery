---
phase: 06-foundation
plan: 02
type: execute
wave: 2
depends_on: ["01"]
files_modified:
  - "app.py"
autonomous: true

must_haves:
  truths:
    - "`app.py` imports `LORO_PIANA_CSS` from `src.ui.css` and injects it exactly once via a single `st.markdown(..., unsafe_allow_html=True)` call."
    - "No inline `<style>...</style>` string literal remains in `app.py` other than the single injection of `LORO_PIANA_CSS`."
    - "`st.set_page_config` uses `page_icon=\"✦\"` (U+2726 BLACK FOUR POINTED STAR); `page_title=\"SNOWGREP\"` is preserved unchanged."
    - "No `#0a0a0a` literal and no `font-family: 'JetBrains Mono', 'Courier New', monospace` rule on `.stApp` remain anywhere in `app.py`."
    - "`python -c \"import ast; ast.parse(open('app.py').read())\"` succeeds — file is syntactically valid Python after edits."
    - "The v2.1 locked UI strings (`\"LLM provider\"`, `\"Azure OpenAI\"`, `\"Anthropic Claude (MGTI)\"`, `\"QUERY DISABLED — see sidebar warning\"`) still appear in `app.py` unchanged."
  artifacts:
    - path: "app.py"
      provides: "Streamlit entry point — now wired to `src.ui.css` and refreshed page chrome."
      contains: "from src.ui.css import LORO_PIANA_CSS"
  key_links:
    - from: "app.py imports"
      to: "src/ui/css.py::LORO_PIANA_CSS"
      via: "`from src.ui.css import LORO_PIANA_CSS`"
      pattern: "from src\\.ui\\.css import LORO_PIANA_CSS"
    - from: "app.py CSS injection"
      to: "Streamlit `<head>` (rendered DOM)"
      via: "`st.markdown(f\"<style>{LORO_PIANA_CSS}</style>\", unsafe_allow_html=True)`"
      pattern: "st\\.markdown.*LORO_PIANA_CSS.*unsafe_allow_html"
    - from: "app.py `st.set_page_config`"
      to: "Browser tab favicon + title"
      via: "`page_icon=\"✦\", page_title=\"SNOWGREP\"`"
      pattern: "page_icon=\"✦\""
---

<objective>
Wire `app.py` to consume the Phase 6 CSS module created in Plan 01 and refresh page chrome. Delete the brutalist CSS block and the `▣` page icon outright (per CONTEXT.md: deletion preferred, no archive file).

Purpose: This plan makes the app actually look Loro Piana. Plan 01 created the module; Plan 02 makes the user's browser see it. After this plan, opening the app shows warm off-white background, Inter body font, and a `✦` favicon.

Output: A modified `app.py` with a 2-line CSS injection in place of the ~300-line brutalist `<style>` block, and `page_icon` flipped from `▣` to `✦`. No other behavior changes — every existing `st.button`, `st.chat_input`, `st.expander`, `st.dataframe` call site is left untouched.
</objective>

<execution_context>
@C:/Users/taylo/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/taylo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/06-foundation/06-CONTEXT.md
@.planning/phases/06-foundation/06-01-SUMMARY.md

# Target file
@app.py

# Source of truth (created in Plan 01)
@src/ui/css.py
</context>

<tasks>

<task type="auto" id="1">
  <name>Task 1: Replace brutalist CSS block in `app.py` with single-line module injection</name>
  <files>app.py</files>
  <action>
**Current state** (lines ~37-352 in `app.py`):
- Lines 37-43: A comment block starting `# ====...` titled `CLEANED CSS INJECTION (replaces the previous BRUTALIST block)`.
- Lines 44-352: A `st.markdown("""<style>...</style>""", unsafe_allow_html=True)` call containing the brutalist CSS (`#0a0a0a` background, `font-family: 'JetBrains Mono', 'Courier New', monospace` on `.stApp`, plus icon hack rules, sidebar pinning, buttons styled black, etc.).

**Required edits:**

1. Add the import. In the imports section near the top of `app.py` (where `from src.utils import ...` lives, around line 22), add a new import line. Pick the cleanest insertion point — after the existing `from src.utils import (...)` block:

   ```python
   from src.ui.css import LORO_PIANA_CSS
   ```

   Match the project's existing flat-import convention (`from src.x import y` form). Do not introduce a relative import.

2. Delete the entire brutalist comment + `st.markdown` block. That is: the comment block starting around line 37 (`# ====...CLEANED CSS INJECTION...`) and the full `st.markdown("""<style>...</style>""", unsafe_allow_html=True)` call from `st.markdown("""` through the closing `""", unsafe_allow_html=True)` (around line 352). Use multiple `Edit` calls if the block is too large for a single edit; the entire block is one contiguous slab between `st.set_page_config(...)` (which stays) and `# Mode mapping for UI` (which stays).

3. Replace the deleted block with this single injection:

   ```python
   # ============================================================
   # LORO PIANA CSS — single-injection from src/ui/css.py (v2.2 Phase 6)
   # ============================================================
   st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)
   ```

   That's it. Three lines of code plus a comment header. No inline `<style>` literal, no escaped braces, no other `st.markdown` style injections elsewhere in this section.

**Constraints / non-goals:**
- Do NOT modify any `st.button(...)`, `st.chat_input(...)`, `st.selectbox(...)`, `st.expander(...)`, `st.dataframe(...)`, `st.write(...)`, or other downstream render calls — Phase 8+ restyles touch those. Plan 02 only swaps the CSS source.
- Do NOT change any UI string. Specifically, `"LLM provider"`, `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"QUERY DISABLED — see sidebar warning"` remain verbatim wherever they appear in `app.py`.
- Do NOT introduce a `legacy_brutalist_css.py` archive — CONTEXT.md explicitly says deletion preferred.
- Do NOT touch `tests/test_phase5_ui.py` or any test file — the AST-based regression on `_render_provenance_caption` must keep passing (Plan 02 does not touch that helper).
- After the edit, the only remaining `unsafe_allow_html=True` calls in `app.py` should be ones that are NOT injecting global CSS — Phase 6 leaves any `st.markdown("...", unsafe_allow_html=True)` calls that render content (e.g., per-message HTML, captions) alone. Run `grep -n "unsafe_allow_html" app.py` after the edit and visually confirm: exactly one occurrence should be the new `LORO_PIANA_CSS` injection; any others should be content-rendering, not `<style>` blocks.
  </action>
  <verify>
1. `python -c "import ast; ast.parse(open('app.py').read())"` — exits 0, no SyntaxError.

2. `grep -n "from src.ui.css import LORO_PIANA_CSS" app.py` — exactly one match.

3. `grep -n "st.markdown(f\"<style>{LORO_PIANA_CSS}</style>\"" app.py` — exactly one match.

4. `grep -nF "#0a0a0a" app.py` — zero matches.

5. `grep -nE "font-family: 'JetBrains Mono', 'Courier New', monospace" app.py` — zero matches (the rule on `.stApp` is gone).

6. `grep -nF "<style>" app.py | wc -l` — exactly one (the new injection). No leftover inline `<style>` strings.

7. `grep -nF '"LLM provider"' app.py` and `grep -nF '"Azure OpenAI"' app.py` and `grep -nF '"Anthropic Claude (MGTI)"' app.py` and `grep -nF '"QUERY DISABLED' app.py` — each returns at least one match (locked strings preserved).

8. `python -m py_compile app.py` — exits 0.
  </verify>
  <done>
`app.py` compiles. The brutalist CSS block is gone. Exactly one CSS injection remains, sourced from `src.ui.css.LORO_PIANA_CSS`. All v2.1 locked strings still present. Satisfies FND-03.
  </done>
</task>

<task type="auto" id="2">
  <name>Task 2: Refresh `st.set_page_config` — swap `page_icon` from `▣` to `✦`</name>
  <files>app.py</files>
  <action>
Locate the `st.set_page_config(...)` call near the top of `app.py` (around line 31):

```python
st.set_page_config(
    page_title="SNOWGREP",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

Change `page_icon="▣"` to `page_icon="✦"` (U+2726 BLACK FOUR POINTED STAR — single Unicode codepoint, no surrounding whitespace, no escape sequence).

**Constraints:**
- `page_title="SNOWGREP"` is locked — do NOT change it.
- `layout="wide"` and `initial_sidebar_state="expanded"` are unchanged.
- This is the ONLY `set_page_config` call in `app.py`; do not add a second one.
- Save the file as UTF-8 — `✦` is a 3-byte UTF-8 character. If your editor's default encoding is anything other than UTF-8, the character will corrupt; verify the file's encoding is UTF-8 after save.
  </action>
  <verify>
1. `grep -nF 'page_icon="✦"' app.py` — exactly one match.

2. `grep -nF 'page_icon="▣"' app.py` — zero matches.

3. `grep -nF 'page_title="SNOWGREP"' app.py` — exactly one match (unchanged).

4. `python -c "import ast, io; ast.parse(io.open('app.py', encoding='utf-8').read())"` — exits 0 (UTF-8 safe).

5. `python -c "src = open('app.py', encoding='utf-8').read(); assert '✦' in src, 'BLACK FOUR POINTED STAR missing'; print('OK')"` — prints `OK`.
  </verify>
  <done>
Browser tab favicon will render `✦` once the app launches; `page_title` unchanged. Satisfies FND-05.
  </done>
</task>

</tasks>

<verification>
After both tasks:

```
python -m py_compile app.py
grep -c "from src.ui.css import LORO_PIANA_CSS" app.py     # 1
grep -c "st.markdown(f\"<style>{LORO_PIANA_CSS}</style>\"" app.py  # 1
grep -c "#0a0a0a" app.py                                    # 0
grep -c '<style>' app.py                                    # 1 (the new one)
grep -c 'page_icon="✦"' app.py                              # 1
grep -c 'page_icon="▣"' app.py                              # 0
grep -c 'page_title="SNOWGREP"' app.py                      # 1
```

All counts must match the comments above.

Also confirm v2.1 locked strings still present:

```
grep -F '"LLM provider"' app.py
grep -F '"Azure OpenAI"' app.py
grep -F '"Anthropic Claude (MGTI)"' app.py
grep -F 'QUERY DISABLED — see sidebar warning' app.py
```

Each must return at least one match.

Phase 5 regression test still passes:

```
python -m pytest tests/test_phase5_ui.py -q
```

Exit code 0.
</verification>

<success_criteria>
- `app.py` compiles and imports `LORO_PIANA_CSS` from `src.ui.css`.
- The brutalist CSS block is fully deleted; exactly one CSS injection remains.
- `st.set_page_config(page_title="SNOWGREP", page_icon="✦", ...)`.
- `tests/test_phase5_ui.py` passes (v2.1 invariant preserved — Phase 6 does NOT touch `_render_provenance_caption`).
- v2.1 locked UI strings all still present.
- Satisfies: FND-03 (single-injection module pattern, no inline `<style>` strings remain), FND-05 (`page_icon="✦"`).
</success_criteria>

<output>
After completion, create `.planning/phases/06-foundation/06-02-SUMMARY.md` documenting:
- Line range deleted from `app.py` (before/after line counts).
- Confirmation of all 8 verification grep counts.
- Confirmation that `tests/test_phase5_ui.py` still passes.
- Confirmation that v2.1 locked strings still present.
</output>
