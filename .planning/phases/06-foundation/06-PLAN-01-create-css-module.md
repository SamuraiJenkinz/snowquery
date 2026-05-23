---
phase: 06-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - "src/ui/__init__.py"
  - "src/ui/css.py"
autonomous: true

must_haves:
  truths:
    - "Importing `LORO_PIANA_CSS` from `src.ui.css` returns a non-empty string containing the warm off-white background `#F5F0EB`."
    - "Importing `LORO_PIANA_TOKENS` from `src.ui.css` returns a dict whose `accent` key is `#8B7355` (cashmere brown)."
    - "The CSS string contains Google Fonts imports for EB Garamond (weights 300, 400) and Inter (weights 400, 500); JetBrains Mono is retained for code/data only."
    - "The CSS string defines `--lp-shadow-warm: 0 4px 12px rgba(139, 115, 85, 0.08)` and a focus ring `0 0 0 3px rgba(139, 115, 85, 0.2)` — no `rgba(0,0,0,...)` shadows anywhere in the file."
    - "The CSS string defines a `.lp-label` utility class with `font-family: var(--lp-font-body)`, `font-weight: 500`, `text-transform: uppercase`, `letter-spacing: 0.1em` (or `var(--lp-tracking-wider)`), `font-size: 11px` or 12px, and color `var(--lp-text-muted)` (`#6B5E52`)."
    - "Streamlit button selectors (`.stButton > button`, `[data-testid=\"stChatInputSubmitButton\"]`) get `background: #8B7355` (or `var(--lp-accent)`), white text, 4px border-radius, `text-transform: uppercase`, and `letter-spacing: 0.1em`."
  artifacts:
    - path: "src/ui/__init__.py"
      provides: "Marks `src/ui` as a Python package."
      contains: "(empty or single docstring)"
    - path: "src/ui/css.py"
      provides: "`LORO_PIANA_TOKENS` dict + `LORO_PIANA_CSS` string — single source of truth for Phase 6+ design tokens."
      contains: "LORO_PIANA_TOKENS"
      min_lines: 200
  key_links:
    - from: "src/ui/css.py::LORO_PIANA_TOKENS"
      to: "src/ui/css.py::LORO_PIANA_CSS"
      via: "Same hex values appear in both (no drift)."
      pattern: "#8B7355"
    - from: "src/ui/css.py::LORO_PIANA_CSS Streamlit overrides"
      to: "Streamlit DOM selectors (`.stApp`, `[data-testid=\"stSidebar\"]`, `.stButton > button`)"
      via: "Direct CSS selector rules inside the constant."
      pattern: "\\.stApp"
---

<objective>
Create the `src/ui/` package with a single CSS module (`src/ui/css.py`) that exports both `LORO_PIANA_TOKENS` (Python dict) and `LORO_PIANA_CSS` (string) — the canonical Loro Piana design tokens for v2.2.

Purpose: Phase 6 ships the foundation; every subsequent v2.2 phase (7-11) consumes this module read-only. The module is the contract — get the tokens, fonts, palette, spacing, shadows, focus ring, and Streamlit overrides right here once, and downstream phases never re-define them.

Output: Two files. `src/ui/__init__.py` (empty package marker) and `src/ui/css.py` (the full token + CSS export). No changes to `app.py` in this plan — Plan 02 wires the consumer.
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

# Canonical inputs for the CSS string (read-only reference)
@C:/Users/taylo/.claude/skills/loro-piana-aesthetic/templates/tokens.css
@C:/Users/taylo/.claude/skills/loro-piana-aesthetic/references/design-tokens.md
</context>

<tasks>

<task type="auto" id="1">
  <name>Task 1: Create `src/ui/__init__.py` package marker</name>
  <files>src/ui/__init__.py</files>
  <action>
Create `src/ui/__init__.py` as an essentially empty file with a single module docstring:

```python
"""SNOWGREP UI helpers — design tokens, CSS, components (v2.2+)."""
```

That's the whole file. Do NOT re-export anything from `css.py` here — downstream consumers do `from src.ui.css import LORO_PIANA_CSS, LORO_PIANA_TOKENS`, matching the project's existing flat-import convention (`from src.utils import ...`, `from src.llm import ...`).
  </action>
  <verify>
`ls src/ui/__init__.py` succeeds. File is 1-2 lines.
  </verify>
  <done>
`src/ui/` exists as a Python package; `python -c "import src.ui"` succeeds with no errors.
  </done>
</task>

<task type="auto" id="2">
  <name>Task 2: Create `src/ui/css.py` with `LORO_PIANA_TOKENS` dict + `LORO_PIANA_CSS` constant</name>
  <files>src/ui/css.py</files>
  <action>
Create `src/ui/css.py`. The module exports exactly two top-level names: `LORO_PIANA_TOKENS` (dict) and `LORO_PIANA_CSS` (str). Both kept in sync as a single source of truth.

**Module structure (in order):**

1. Module docstring:
   ```python
   """Loro Piana design tokens + global CSS for SNOWGREP v2.2.

   This module is the single source of truth for the Loro Piana quiet-luxury
   aesthetic. Phase 6+ downstream surfaces consume it read-only:
       from src.ui.css import LORO_PIANA_CSS, LORO_PIANA_TOKENS

   LORO_PIANA_TOKENS — Python dict mirror of palette + spacing for use in
                       inline HTML / Altair theming (where CSS vars are awkward).
   LORO_PIANA_CSS    — Full CSS string injected once from app.py via
                       st.markdown(f"<style>{LORO_PIANA_CSS}</style>",
                                   unsafe_allow_html=True).

   No rgba(0, 0, 0, ...) shadows anywhere. Focus rings are warm cashmere,
   never blue. JetBrains Mono is for record identifiers / code / raw data
   only — Inter is the body font, EB Garamond is for headlines.
   """
   ```

2. `from __future__ import annotations` (matches project convention — see `src/utils.py`, `src/llm/__init__.py`).

3. `LORO_PIANA_TOKENS: dict[str, str | int]` — Python dict mirror. Use the exact values from `.planning/phases/06-foundation/06-CONTEXT.md` §Token export pattern (do not invent new keys, do not omit any). All palette values are str (hex), spacing values are int (px), radii are int (px). Keys (exact):

   ```python
   LORO_PIANA_TOKENS: dict[str, str | int] = {
       # palette
       "bg":              "#F5F0EB",
       "surface":         "#FFFFFF",
       "border":          "#E8E0D8",
       "text":            "#2C2420",
       "text_muted":      "#6B5E52",
       "text_subtle":     "#8A7A6B",
       "accent":          "#8B7355",  # cashmere primary
       "accent_hover":    "#A89680",
       "accent_pressed":  "#6D5A42",
       "gold_decorative": "#B8A88A",
       "success":         "#8A9A7D",  # sage
       "warning":         "#C4A76B",  # amber
       "danger":          "#A67866",  # terracotta
       "info":            "#9B8F7D",  # taupe
       # spacing (px ints)
       "space_1": 4, "space_2": 8, "space_3": 12, "space_4": 16,
       "space_6": 24, "space_8": 32, "space_12": 48, "space_16": 64,
       # radii
       "radius_md": 4, "radius_lg": 8, "radius_full": 9999,
   }
   ```

4. `LORO_PIANA_CSS: str` — triple-quoted CSS string. Build it by:

   **a. Port `C:\Users\taylo\.claude\skills\loro-piana-aesthetic\templates\tokens.css` verbatim** — all `:root` custom properties (`--lp-primary-50` through `--lp-primary-700`, `--lp-neutral-0` through `--lp-neutral-900`, semantic colors, aliases, typography, spacing scale `--lp-space-0` through `--lp-space-24`, radii, shadows including `--lp-shadow-warm` and `--lp-shadow-focus`, transitions, z-index). The `:root` block plus base styles (`html, body`, `h1..h3`, `h4..h6`, `p`, `a`, `*:focus-visible`, `.lp-label`, `.lp-divider`) are all included as-is.

   **b. Adjust the Google Fonts `@import` at the very top of the CSS string** to match v2.2's exact font weight set:

   ```css
   @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@300;400&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');
   ```

   Place this `@import` as the FIRST line inside the CSS string (the skill template's font load was a `<link>` HTML comment — replace with this single `@import` so a `<style>` injection works). Do NOT keep the skill template's leading `/** ... */` comment block referencing the `<link>` approach; replace it with a short inline comment: `/* Loro Piana tokens — see src/ui/css.py module docstring */`.

   **c. Append Streamlit-specific overrides** AFTER the base styles. These override Streamlit's brutalist-replacement defaults so the warm off-white background floods the viewport and Inter wins on the body. Required selectors and rules (use CSS custom properties from step a — DO NOT hard-code hex values in this section except where noted):

   ```css
   /* ============ STREAMLIT BASE OVERRIDES ============ */

   /* Flood the warm off-white background across the entire app shell */
   .stApp,
   [data-testid="stAppViewContainer"],
   [data-testid="stHeader"],
   .main,
   .block-container {
       background: var(--lp-bg);
       color: var(--lp-text);
       font-family: var(--lp-font-body);
   }

   /* Streamlit sometimes injects monospace on .stApp — clobber it */
   .stApp {
       font-family: var(--lp-font-body) !important;
   }

   /* Sidebar surface — alt warm tone */
   [data-testid="stSidebar"] {
       background: var(--lp-neutral-100);
       border-right: 1px solid var(--lp-border);
   }
   [data-testid="stSidebar"] * {
       font-family: var(--lp-font-body);
       color: var(--lp-text);
   }

   /* Hide Streamlit chrome we don't want (carry forward from brutalist CSS) */
   #MainMenu { visibility: hidden; }
   footer { visibility: hidden; }
   header { visibility: hidden; }
   .stDeployButton { display: none; }

   /* ============ BUTTONS — cashmere primary, all instances ============ */

   .stButton > button,
   [data-testid="stChatInputSubmitButton"],
   [data-testid="baseButton-primary"],
   [data-testid="baseButton-secondary"] {
       background: var(--lp-accent);
       color: var(--lp-neutral-0);
       border: 1px solid var(--lp-accent);
       border-radius: var(--lp-radius-md);
       font-family: var(--lp-font-body);
       font-weight: 500;
       font-size: var(--lp-text-small);
       text-transform: uppercase;
       letter-spacing: var(--lp-tracking-wider);
       padding: var(--lp-space-3) var(--lp-space-6);
       transition: background var(--lp-transition-base),
                   border-color var(--lp-transition-base);
       box-shadow: none;
   }

   .stButton > button:hover,
   [data-testid="stChatInputSubmitButton"]:hover,
   [data-testid="baseButton-primary"]:hover,
   [data-testid="baseButton-secondary"]:hover {
       background: var(--lp-primary-400);
       border-color: var(--lp-primary-400);
       color: var(--lp-neutral-0);
   }

   .stButton > button:active,
   [data-testid="stChatInputSubmitButton"]:active {
       background: var(--lp-primary-600);
       border-color: var(--lp-primary-600);
   }

   .stButton > button:disabled,
   [data-testid="stChatInputSubmitButton"]:disabled {
       background: var(--lp-neutral-300);
       border-color: var(--lp-neutral-300);
       color: var(--lp-neutral-500);
       cursor: not-allowed;
   }

   /* ============ MONO BOUNDARY — code/data only ============ */

   code, pre, kbd, samp, .lp-mono,
   [data-testid="stCodeBlock"],
   [data-testid="stCode"] {
       font-family: var(--lp-font-mono);
       font-size: var(--lp-text-small);
   }

   /* ============ INPUTS — restrained editorial ============ */

   .stTextInput input,
   .stTextArea textarea,
   .stSelectbox [data-baseweb="select"],
   [data-testid="stChatInput"] textarea {
       background: var(--lp-surface);
       color: var(--lp-text);
       border: 1px solid var(--lp-border);
       border-radius: var(--lp-radius-md);
       font-family: var(--lp-font-body);
   }
   ```

   **d. Important:** Do NOT include any `rgba(0, 0, 0, ...)` shadow. Do NOT include any `background: #0a0a0a` rule. Do NOT include `font-family: 'JetBrains Mono', 'Courier New', monospace` on `.stApp` or any global body-level selector. Verify by reading the file before saving.

5. Module-level `__all__` for explicitness:
   ```python
   __all__ = ["LORO_PIANA_TOKENS", "LORO_PIANA_CSS"]
   ```

**Constraints / non-goals:**
- Do NOT add functions, classes, or runtime logic. Two module-level constants only.
- Do NOT inject CSS from this module — `LORO_PIANA_CSS` is just a string. Injection is Plan 02's job in `app.py`.
- Do NOT touch `app.py` in this plan.
- Do NOT create a `legacy_brutalist_css.py` archive — CONTEXT.md says deletion preferred (Plan 02 deletes).
  </action>
  <verify>
1. `python -c "from src.ui.css import LORO_PIANA_CSS, LORO_PIANA_TOKENS; assert LORO_PIANA_TOKENS['accent'] == '#8B7355'; assert LORO_PIANA_TOKENS['bg'] == '#F5F0EB'; assert '#F5F0EB' in LORO_PIANA_CSS; assert 'EB+Garamond' in LORO_PIANA_CSS; assert 'Inter:wght@400;500' in LORO_PIANA_CSS; assert 'JetBrains+Mono' in LORO_PIANA_CSS; assert '0 0 0 3px rgba(139, 115, 85, 0.2)' in LORO_PIANA_CSS; assert 'rgba(0, 0, 0' not in LORO_PIANA_CSS and 'rgba(0,0,0' not in LORO_PIANA_CSS; assert '#0a0a0a' not in LORO_PIANA_CSS; print('OK')"` prints `OK`.

2. `grep -n "JetBrains Mono.*Courier New.*monospace" src/ui/css.py` — should NOT match on a global `.stApp` selector. (May match in `--lp-font-mono` fallback list; that's fine.)

3. `grep -c '\.lp-label' src/ui/css.py` returns at least 1.

4. `grep -c 'letter-spacing.*var(--lp-tracking-wider)' src/ui/css.py` returns at least 2 (used by `.lp-label` and button rules).
  </verify>
  <done>
`src/ui/css.py` exists. The import smoke (verify step 1) passes. The file contains all four sections (token `:root` block, base styles, Streamlit overrides, mono boundary rules). No `#0a0a0a`, no `rgba(0,0,0,...)` shadows.
  </done>
</task>

</tasks>

<verification>
Run from project root:

```
python -c "from src.ui.css import LORO_PIANA_CSS, LORO_PIANA_TOKENS; print(len(LORO_PIANA_CSS), len(LORO_PIANA_TOKENS))"
```

Expected: prints two integers; CSS length > 4000 chars, tokens dict length >= 22 keys.

`ls src/ui/` → `__init__.py`, `css.py`.
</verification>

<success_criteria>
- `src/ui/__init__.py` exists.
- `src/ui/css.py` exists, importable, exports `LORO_PIANA_TOKENS` (dict) and `LORO_PIANA_CSS` (str).
- `LORO_PIANA_CSS` contains: `#F5F0EB`, `#8B7355`, `#2C2420`, `#6B5E52`, Google Fonts import for EB Garamond + Inter + JetBrains Mono with the exact weight sets above, `.lp-label` class, `.stButton > button` selector with cashmere + uppercase + 0.1em tracking + 4px radius, `--lp-shadow-warm`, `--lp-shadow-focus`.
- `LORO_PIANA_CSS` does NOT contain: `#0a0a0a`, `rgba(0, 0, 0,`, `rgba(0,0,0,`, or `font-family: 'JetBrains Mono', 'Courier New', monospace` on `.stApp`.
- Satisfies: FND-01 (font imports), FND-02 (`:root` color variable overrides), FND-04 (`.lp-label` class definition), partial FND-06 (button base CSS rules — verified visually in Plan 03).
</success_criteria>

<output>
After completion, create `.planning/phases/06-foundation/06-01-SUMMARY.md` documenting:
- Final file paths and line counts.
- Confirmation that the four section headers exist in `LORO_PIANA_CSS` (tokens, base styles, Streamlit overrides, mono boundary).
- Confirmation that the verification asserts pass.
- Token dict key count.
- Any deviations from CONTEXT.md (expected: none).
</output>
