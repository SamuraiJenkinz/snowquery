# Phase 12: Doc Accuracy Cleanup - Research

**Researched:** 2026-05-24
**Domain:** Documentation content accuracy (USER_GUIDE.md, README.md)
**Confidence:** HIGH — all findings sourced from live file reads; no training-data inference

---

## Summary

Phase 12 is a pure content-accuracy pass on two doc files. The shipped code is correct and must not be touched. Three lines in USER_GUIDE.md and README.md describe the app differently from what app.py and src/ui/altair_theme.py actually emit. The fix is to update those lines so operators reading the docs see the same strings and colors they will encounter at runtime.

The research below provides verbatim current text with confirmed line numbers, exact replacement strings drawn from the shipped source, the complete list of protected substrings that must be preserved, and a safe recommendation for the broken GitHub link.

**Primary recommendation:** Three targeted line edits — USER_GUIDE.md lines 35 and 36, README.md lines 18 and 27 — with a post-edit grep scan and a `PYTHONPATH=. python -m pytest tests/ -q` run to confirm 103/103 green.

---

## Current State of Drifted Lines

### USER_GUIDE.md — confirmed line numbers

```
Line 35: - **Expandable interactive view** — Below the editorial table, an expander labelled "VIEW INTERACTIVE DATAFRAME" reveals Streamlit's native dataframe for sort/filter operations when an operator needs them.

Line 36: - **Restyled charts** — Altair charts use a registered `loro_piana` theme: charcoal axes on warm-beige background, palette colors `#8B7355` (muted gold) and `#A67866` (terracotta), with EB Garamond title type.
```

Surrounding context (lines 28-37) for the planner's reference — this is the "Visual Refresh (v2.2) → What changed" bullet list:

```
Line 32:     - **Splash screen** — ...
Line 33:     - **Sidebar style** — ...
Line 34:     - **Editorial table** — ...
Line 35:     - **Expandable interactive view** — [DRIFTED]
Line 36:     - **Restyled charts** — [DRIFTED]
Line 37: (blank line, then "### What did NOT change" heading)
```

No heading numbers or section-order structure is affected by editing lines 35-36.

### README.md — confirmed line numbers

```
Line 18: The v2.2 visual surface follows the in-house [`loro-piana-aesthetic`](https://github.com/) design system — EB Garamond + Inter typography, warm-beige page, charcoal body, muted-gold accents.

Line 27: *Results + chart surface — editorial table with EB Garamond column heads, expandable "VIEW INTERACTIVE DATAFRAME" view, restyled chart with charcoal axes and muted-gold marks.*
```

Line 18 is in the "## Screenshots" section. Line 27 is the caption of the third screenshot block. Neither line is adjacent to a heading that would shift section order.

---

## Shipped Truth

### Expander label (app.py:612)

Exact string in production code:

```python
with st.expander("EXPAND · INTERACTIVE VIEW", expanded=False):
```

The middle character is U+00B7 (MIDDLE DOT / middot), encoded as `·`. It is NOT a bullet (•, U+2022), asterisk (*), or any other character. When copying this string into documentation, the middot must be the literal Unicode character, not an ASCII substitute.

Byte verification: `\xc2\xb7` in UTF-8.

### VIBRANT_PALETTE (src/ui/altair_theme.py:42-48)

```python
VIBRANT_PALETTE: list[str] = [
    "#C0392B",  # crimson       — primary / single-series line
    "#2E5BBA",  # royal blue
    "#2E7D32",  # forest green
    "#E67E22",  # burnt orange
    "#F39C12",  # mustard yellow
]
```

Five colors. No `#8B7355` (muted gold) and no `#A67866` (terracotta) in this list.

### Chart chrome colors (from altair_theme.py loro_piana_theme())

These are NOT chart data colors but are accurate to mention in context of the chart aesthetic:

| Property | Token | Hex | Label in docs |
|----------|-------|-----|---------------|
| Title font | EB Garamond | — | "EB Garamond title type" |
| Title color | charcoal | `#2C2420` | "charcoal" |
| Axis label color | warm-gray | `#6B5E52` | "warm-gray" |
| Grid color | warm-beige | `#E8E0D8` | "warm-beige gridlines" |
| Background | transparent | — | inherits card background |

The shipped module doc-string says: "Chrome properties use the cashmere palette (warm-beige gridlines, charcoal titles, warm-gray labels). Chart **data** uses the vibrant categorical palette so that bars, pies, and lines are visually distinct."

This is the correct framing for the updated doc line.

---

## Protected Substrings (TST-01)

These are the strings the tests assert on. ALL must be preserved verbatim after edits.

### From test_phase5_ui.py — test_sc5_user_guide_contains_locked_ui_strings_and_required_topics

Asserted against USER_GUIDE.md full text:

**locked_strings** (substring-in-text assertions):
- `"LLM provider"` — selectbox label
- `"Azure OpenAI"`
- `"Anthropic Claude (MGTI)"`
- `"LLM PROVIDER"` — sidebar section header (uppercase)
- `"QUERY DISABLED"` (note: full string in USER_GUIDE.md is `"QUERY DISABLED — see sidebar warning"` with U+2014 em-dash; the test checks substring `"QUERY DISABLED"`)
- `"hubble.mmc.com"`
- `"smoke_llm.py"`

**required_topics** (substring-in-text assertions):
- `"LLM Provider Selection"`
- `"MGTI"`
- `"First-Time"`
- `"Mid-Session"`

**env var assertions**:
- `"ANTHROPIC_BASE_URL"`
- `"ANTHROPIC_API_KEY"`
- `"ANTHROPIC_MODEL"`

### From test_phase5_ui.py — test_sc5_readme_contains_required_topics

Asserted against README.md full text:
- `"LLM Provider Selection"`
- `"Anthropic Claude"`
- `"smoke_llm.py"`
- `"USER_GUIDE.md"`
- `"MGTI"` (MGTI constraint reference)
- `"Hubble"` OR `"hubble.mmc.com"` (at least one must be present)

### From test_sc3_chat_input_disabled_when_blocked_flag_true

This asserts the runtime placeholder string, not the doc file:
- `"QUERY DISABLED — see sidebar warning"` — contains U+2014 em-dash. This is in app.py, NOT in the doc files being edited. Listed here so the planner does not confuse it with the U+2014 that also appears on USER_GUIDE.md line 357.

### Locked Unicode characters in USER_GUIDE.md (must not be corrupted by editors)

| Location | Character | Unicode | Appears in |
|----------|-----------|---------|-----------|
| Line 35 replacement | · | U+00B7 MIDDLE DOT | `"EXPAND · INTERACTIVE VIEW"` |
| Line 41 | — | U+2014 EM DASH | `"QUERY DISABLED — see sidebar warning"` |
| Various | … | U+2026 HORIZONTAL ELLIPSIS | `"Ask anything about your incidents…"` |

None of the three existing test-asserted strings (`"QUERY DISABLED"`, `"LLM provider"`, `"Azure OpenAI"`, etc.) are on lines 35 or 36, so editing those lines carries zero test-breakage risk.

---

## Recommended Edits

### USER_GUIDE.md

**Line 35 — Expander caption**

OLD (line 35, exact):
```
- **Expandable interactive view** — Below the editorial table, an expander labelled "VIEW INTERACTIVE DATAFRAME" reveals Streamlit's native dataframe for sort/filter operations when an operator needs them.
```

NEW:
```
- **Expandable interactive view** — Below the editorial table, an expander labelled "EXPAND · INTERACTIVE VIEW" reveals Streamlit's native dataframe for sort/filter operations when an operator needs them.
```

Change: replace `"VIEW INTERACTIVE DATAFRAME"` with `"EXPAND · INTERACTIVE VIEW"` (U+00B7 middot between EXPAND and INTERACTIVE). All other prose unchanged.

**Line 36 — Chart palette**

OLD (line 36, exact):
```
- **Restyled charts** — Altair charts use a registered `loro_piana` theme: charcoal axes on warm-beige background, palette colors `#8B7355` (muted gold) and `#A67866` (terracotta), with EB Garamond title type.
```

NEW:
```
- **Restyled charts** — Altair charts use a registered `loro_piana` theme: charcoal axes on warm-beige gridlines, vibrant categorical palette `#C0392B` / `#2E5BBA` / `#2E7D32` / `#E67E22` / `#F39C12` (crimson, royal blue, forest green, burnt orange, mustard yellow) for data marks, with EB Garamond title type.
```

Rationale: accurately reflects VIBRANT_PALETTE from altair_theme.py. Retains "charcoal axes" framing (charcoal is the title color `#2C2420`), updates "warm-beige background" to "warm-beige gridlines" (the actual property: `gridColor: #E8E0D8`), replaces the two wrong hex values with all five correct VIBRANT_PALETTE values, preserves "EB Garamond title type."

### README.md

**Line 18 — loro-piana-aesthetic link**

OLD (line 18, exact):
```
The v2.2 visual surface follows the in-house [`loro-piana-aesthetic`](https://github.com/) design system — EB Garamond + Inter typography, warm-beige page, charcoal body, muted-gold accents.
```

NEW:
```
The v2.2 visual surface follows the in-house `loro-piana-aesthetic` design system — EB Garamond + Inter typography, warm-beige page, charcoal body, muted-gold accents.
```

Change: remove the broken `[text](https://github.com/)` hyperlink, keep `loro-piana-aesthetic` as inline code. The skill lives locally at `~/.claude/skills/loro-piana-aesthetic/` — it is not a public repo. A broken link is worse than no link; an inline code reference is cleaner and honest.

No other prose on line 18 changes. `"Anthropic Claude"` and `"MGTI"` tokens (tested by test_sc5_readme_contains_required_topics) do not appear on line 18 and are unaffected.

**Line 27 — Expander caption in screenshot caption**

OLD (line 27, exact):
```
*Results + chart surface — editorial table with EB Garamond column heads, expandable "VIEW INTERACTIVE DATAFRAME" view, restyled chart with charcoal axes and muted-gold marks.*
```

NEW:
```
*Results + chart surface — editorial table with EB Garamond column heads, expandable "EXPAND · INTERACTIVE VIEW" view, restyled chart with charcoal axes and vibrant categorical marks.*
```

Changes:
1. `"VIEW INTERACTIVE DATAFRAME"` → `"EXPAND · INTERACTIVE VIEW"` (U+00B7 middot)
2. `muted-gold marks` → `vibrant categorical marks` (the marks are now the VIBRANT_PALETTE colors, not muted gold)

---

## Risks & Hidden Drift

### Risk 1: #8B7355 and #A67866 appear in other doc files

Searched all `*.md` files in the repo for `#8B7355` and `#A67866`.

**Occurrences requiring NO change** (these are legitimate references to the CSS token or terracotta sidebar/error-card CSS, not chart palette descriptions):
- `.planning/REQUIREMENTS.md` — FND-02, FND-06, SBR-03, SBR-04, SBR-06, DVZ-04, POL-03, TST-02 spec text. Planning docs, not user-facing.
- `.planning/ROADMAP.md` — spec text describing original cashmere palette intent. Planning docs.
- `.planning/phases/*/` — all planning artifacts. Not user-facing.
- `deploy/BUILD_PYTHON_FROM_SOURCE.md` — unrelated link to cpython repo, happens to match `github.com`.

**Only the two occurrences in USER_GUIDE.md line 36 require a change.** No other user-facing doc file contains the drifted palette.

### Risk 2: test_css_contains_palette_muted_gold asserts #8B7355 in LORO_PIANA_CSS

`tests/test_phase6_visual.py:84` asserts `"#8B7355" in LORO_PIANA_CSS`. This asserts against `src/ui/css.py`, NOT against `USER_GUIDE.md`. Removing `#8B7355` from USER_GUIDE.md does NOT touch `src/ui/css.py` and does NOT affect this test. Confirmed safe.

### Risk 3: No test asserts on line numbers or heading counts in doc files

Searched all test files for assertions on line numbers, section ordering, or line counts in USER_GUIDE.md / README.md. None found. Tests only do substring-in-full-text assertions (using `in` operator on the full file string). Editing lines 35, 36, 18, and 27 cannot break any passing test.

### Risk 4: "VIEW INTERACTIVE DATAFRAME" in test files

Searched all test files for `VIEW INTERACTIVE` and `EXPAND`. No occurrences. The expander label string is not asserted by any test — it is an app-runtime string locked by the Phase 9 acceptance pass, not by a doc-content test. Changing it in docs is safe.

### Risk 5: README.md "their-piana-aesthetic" link removal breaks "Hubble" or "MGTI" test assertion

`test_sc5_readme_contains_required_topics` checks for `"Hubble"` OR `"hubble.mmc.com"` and `"MGTI"`. Neither token is on line 18. Line 18 only mentions "loro-piana-aesthetic" and design tokens. Safe.

### Risk 6: middot U+00B7 encoding in editor

If the plan runs a `sed`-style replacement, the replacement string must include the literal U+00B7 character (not `\xb7`, not `&middot;`). The doc file is UTF-8 encoded. Python's `str.replace()` handles Unicode natively; PowerShell replacement with a literal-pasted middot also works. Recommend using a Python one-liner (see Verification Commands) to guarantee character identity.

---

## Verification Commands

### 1. Pre-edit baseline (optional but confirms starting state)

```bash
PYTHONPATH=. python -m pytest tests/ -q
# Expected: 103 passed, 1 warning
```

### 2. Post-edit: confirm updated strings are present in docs

```bash
# USER_GUIDE.md — confirm new expander caption
python -c "
t = open('USER_GUIDE.md', encoding='utf-8').read()
assert 'EXPAND · INTERACTIVE VIEW' in t, 'Missing: EXPAND · INTERACTIVE VIEW'
assert 'VIEW INTERACTIVE DATAFRAME' not in t, 'Old caption still present'
assert '#8B7355' not in t, 'Old muted gold hex still in USER_GUIDE'
assert '#A67866' not in t, 'Old terracotta hex still in USER_GUIDE'
assert '#C0392B' in t, 'Missing: VIBRANT_PALETTE crimson'
assert '#2E5BBA' in t, 'Missing: VIBRANT_PALETTE royal blue'
assert '#2E7D32' in t, 'Missing: VIBRANT_PALETTE forest green'
assert '#E67E22' in t, 'Missing: VIBRANT_PALETTE burnt orange'
assert '#F39C12' in t, 'Missing: VIBRANT_PALETTE mustard yellow'
print('USER_GUIDE.md: all checks passed')
"
```

```bash
# README.md — confirm new expander caption and link removal
python -c "
t = open('README.md', encoding='utf-8').read()
assert 'EXPAND · INTERACTIVE VIEW' in t, 'Missing: EXPAND · INTERACTIVE VIEW in README'
assert 'VIEW INTERACTIVE DATAFRAME' not in t, 'Old caption still in README'
assert 'https://github.com/)' not in t, 'Broken GitHub link still present'
# Protected tokens still present
assert 'LLM Provider Selection' in t, 'Missing LLM Provider Selection'
assert 'Anthropic Claude' in t, 'Missing Anthropic Claude'
assert 'smoke_llm.py' in t, 'Missing smoke_llm.py'
assert 'USER_GUIDE.md' in t, 'Missing USER_GUIDE.md'
assert 'MGTI' in t, 'Missing MGTI'
assert ('Hubble' in t or 'hubble.mmc.com' in t), 'Missing Hubble reference'
print('README.md: all checks passed')
"
```

```bash
# USER_GUIDE.md — confirm TST-01 protected substrings still present
python -c "
t = open('USER_GUIDE.md', encoding='utf-8').read()
protected = [
    'LLM provider', 'Azure OpenAI', 'Anthropic Claude (MGTI)',
    'LLM PROVIDER', 'QUERY DISABLED', 'hubble.mmc.com', 'smoke_llm.py',
    'LLM Provider Selection', 'MGTI', 'First-Time', 'Mid-Session',
    'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL',
]
for s in protected:
    assert s in t, f'PROTECTED SUBSTRING MISSING: {s!r}'
print('USER_GUIDE.md: all protected substrings preserved')
"
```

### 3. Full regression suite

```bash
PYTHONPATH=. python -m pytest tests/ -q
# Expected: 103 passed, 1 warning
```

Note: bare `pytest tests/` without `PYTHONPATH=.` will fail with `ModuleNotFoundError` because the repo has no `conftest.py` or `pyproject.toml`. Always prefix with `PYTHONPATH=. python -m pytest`.

---

## Recommendation for README.md:18 Link Resolution

**Recommendation: Option (a) — remove the hyperlink, keep the text as inline code.**

The skill at `~/.claude/skills/loro-piana-aesthetic/` is a local operator tool, not a public GitHub repository. The placeholder URL `https://github.com/` is a bare root with no path — clicking it navigates to GitHub's homepage, which is misleading and confusing.

Three options evaluated:

| Option | Verdict | Reason |
|--------|---------|--------|
| (a) `\`loro-piana-aesthetic\`` inline code, no link | **Recommended** | Honest, descriptive, no broken navigation |
| (b) Link to `~/.claude/skills/loro-piana-aesthetic/` local path | Rejected | Local filesystem paths are not valid in a public README; will not resolve in any browser or GitHub rendering |
| (c) Drop name entirely | Rejected | The design system name is useful context for future maintainers; dropping it loses information |

Option (a) preserves all information (the design system name, its relationship to the v2.2 aesthetic, and the typography/palette description) while removing the broken navigation target.

---

## Sources

### PRIMARY (HIGH confidence — all from live file reads)

- `C:\mbrunoapp\snow_query\USER_GUIDE.md` — lines 1-477 read in full; drift confirmed at lines 35-36
- `C:\mbrunoapp\snow_query\README.md` — lines 1-130 read in full; drift confirmed at lines 18 and 27
- `C:\mbrunoapp\snow_query\app.py` — lines 600-627 read; expander label at line 612 confirmed as `"EXPAND · INTERACTIVE VIEW"` with U+00B7
- `C:\mbrunoapp\snow_query\src\ui\altair_theme.py` — full file read; VIBRANT_PALETTE at lines 42-48 confirmed
- `C:\mbrunoapp\snow_query\tests\test_phase5_ui.py` — full file read; SC5 doc assertions extracted lines 683-758
- `C:\mbrunoapp\snow_query\tests\test_phase6_visual.py` — lines 1-260 read; #8B7355 assertion confirmed to target LORO_PIANA_CSS only
- `C:\mbrunoapp\snow_query\.planning\milestones\v2.2-MILESTONE-AUDIT.md` — full read; audit items confirmed
- Bash: `PYTHONPATH=. python -m pytest tests/ -q` — confirmed 103/103 green baseline

---

## RESEARCH COMPLETE

**Phase:** 12 - Doc accuracy cleanup
**Confidence:** HIGH

### Key Findings

- USER_GUIDE.md lines 35 and 36 are confirmed drifted. Line numbers are exact; file has not shifted.
- README.md lines 18 and 27 are confirmed drifted. Line 18 has the placeholder `https://github.com/` link; line 27 has the old expander caption.
- The middot in `"EXPAND · INTERACTIVE VIEW"` is U+00B7. Must be copied verbatim, not substituted.
- VIBRANT_PALETTE is exactly five hex values: `#C0392B`, `#2E5BBA`, `#2E7D32`, `#E67E22`, `#F39C12`.
- No test asserts on line numbers, heading counts, or section ordering — editing the four target lines cannot break the test suite structurally.
- The `#8B7355` palette token test in test_phase6_visual.py targets `LORO_PIANA_CSS` (the CSS module), not `USER_GUIDE.md`. Removing `#8B7355` from USER_GUIDE.md is safe.
- `loro-piana-aesthetic` is a local skill at `~/.claude/skills/loro-piana-aesthetic/`, confirmed present. Recommend replacing the broken `https://github.com/` link with plain inline code, no hyperlink.
- Baseline test suite: 103/103 green with `PYTHONPATH=. python -m pytest tests/ -q`.

### File Created

`C:\mbrunoapp\snow_query\.planning\phases\12-doc-accuracy-cleanup\12-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Current state of drifted lines | HIGH | Read directly from live files with line numbers |
| Shipped truth (expander label, VIBRANT_PALETTE) | HIGH | Read directly from app.py:612 and altair_theme.py:42-48 |
| Protected substrings (TST-01) | HIGH | Extracted from live test file source; no inference |
| Risk of editing lines 35/36/18/27 | HIGH | Grep confirmed no test asserts on those lines or line numbers |
| Link resolution recommendation | HIGH | Local skill path confirmed via ls; placeholder URL visually confirmed |

### Open Questions

None. All research questions from the brief are fully resolved.

### Ready for Planning

Research complete. Planner can now create a single-wave PLAN.md covering four file edits across two documents.
