---
phase: "12"
plan: "01"
subsystem: documentation
tags: [doc-accuracy, USER_GUIDE, README, expander-label, chart-palette, design-system-link]
requires: [11-02]
provides: [accurate-doc-prose-for-shipped-v2.2-strings]
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - USER_GUIDE.md
    - README.md
decisions:
  - "No code touched — only doc prose drifted; shipped code is correct."
  - "U+00B7 middot preserved as literal Unicode in both files."
metrics:
  duration: "2m 3s"
  completed: "2026-05-24"
---

# Phase 12 Plan 01: Doc Accuracy Cleanup Summary

**One-liner:** Synced USER_GUIDE.md:35-36 and README.md:18,27 to shipped strings — expander label, VIBRANT_PALETTE hex values, and broken design-system link all corrected.

## What Was Done

Three doc-drift gaps from `.planning/milestones/v2.2-MILESTONE-AUDIT.md` were closed by four targeted line-level edits to prose-only files. No code was modified.

### Edit 1 — USER_GUIDE.md line 35 (expander label)

**Before:**
```
- **Expandable interactive view** — Below the editorial table, an expander labelled "VIEW INTERACTIVE DATAFRAME" reveals Streamlit's native dataframe for sort/filter operations when an operator needs them.
```

**After:**
```
- **Expandable interactive view** — Below the editorial table, an expander labelled "EXPAND · INTERACTIVE VIEW" reveals Streamlit's native dataframe for sort/filter operations when an operator needs them.
```

The middot `·` is U+00B7 (UTF-8 `\xc2\xb7`), matching the literal string passed to `st.expander()` in `app.py:612`.

### Edit 2 — USER_GUIDE.md line 36 (chart palette description)

**Before:**
```
- **Restyled charts** — Altair charts use a registered `loro_piana` theme: charcoal axes on warm-beige background, palette colors `#8B7355` (muted gold) and `#A67866` (terracotta), with EB Garamond title type.
```

**After:**
```
- **Restyled charts** — Altair charts use a registered `loro_piana` theme: charcoal axes on warm-beige gridlines, vibrant categorical palette `#C0392B` / `#2E5BBA` / `#2E7D32` / `#E67E22` / `#F39C12` (crimson, royal blue, forest green, burnt orange, mustard yellow) for data marks, with EB Garamond title type.
```

The five hex values are the actual `VIBRANT_PALETTE` list defined in `src/ui/altair_theme.py:42-48`. The previous two-token description (`#8B7355` / `#A67866`) was stale from the v2.1-era palette; those colors no longer appear in the shipped theme.

### Edit 3 — README.md line 18 (loro-piana-aesthetic design-system link)

**Before:**
```
The v2.2 visual surface follows the in-house [`loro-piana-aesthetic`](https://github.com/) design system — EB Garamond + Inter typography, warm-beige page, charcoal body, muted-gold accents.
```

**After:**
```
The v2.2 visual surface follows the in-house `loro-piana-aesthetic` design system — EB Garamond + Inter typography, warm-beige page, charcoal body, muted-gold accents.
```

The `(https://github.com/)` placeholder hyperlink was removed. `loro-piana-aesthetic` is kept as inline code — the design system lives in the skills directory (`C:\Users\taylo\.claude\skills\loro-piana-aesthetic\`), not a public GitHub repo.

### Edit 4 — README.md line 27 (screenshot caption)

**Before:**
```
*Results + chart surface — editorial table with EB Garamond column heads, expandable "VIEW INTERACTIVE DATAFRAME" view, restyled chart with charcoal axes and muted-gold marks.*
```

**After:**
```
*Results + chart surface — editorial table with EB Garamond column heads, expandable "EXPAND · INTERACTIVE VIEW" view, restyled chart with charcoal axes and vibrant categorical marks.*
```

Caption aligned with the shipped expander label (U+00B7 middot) and accurate palette description ("vibrant categorical" in place of "muted-gold").

## Verification Results

| Block | Check | Result |
|-------|-------|--------|
| Block 1 | USER_GUIDE.md content accuracy + 15 TST-01 protected substrings | PASSED |
| Block 2 | README.md content accuracy + 6 required topics | PASSED |
| Block 3 | `PYTHONPATH=. python -m pytest tests/ -q` | 103 passed, 1 warning |
| Block 4 | `git status --porcelain` — only USER_GUIDE.md and README.md modified | PASSED |

## Pytest Baseline

Unchanged at **103/103 passed** (1 DeprecationWarning from jsonschema — pre-existing, not introduced by this plan).

## Unicode Contract

The middot character in "EXPAND · INTERACTIVE VIEW" is U+00B7 (UTF-8: `\xc2\xb7`). It was pasted as a literal Unicode character in both Edit tool invocations. Verified programmatically via Python `assert 'EXPAND · INTERACTIVE VIEW' in t` with the literal character in the assertion string.

## Deviations from Plan

None — plan executed exactly as written.

## Carry-Forward Notes

- **Reading source for future doc edits:** The expander label string is defined at `app.py:612` (search for `st.expander`). The VIBRANT_PALETTE hex values are defined at `src/ui/altair_theme.py:42-48`. Future doc edits touching these topics should read those lines directly before authoring prose.
- **TST-01 protected substrings:** The 22 protected substrings asserted by `tests/test_phase4_strict_tools.py` (and the 15-item subset verified here) remain verbatim in USER_GUIDE.md. Any future doc edit must re-run the Block 1 verification one-liner.
- **README.md loro-piana-aesthetic:** Now plain inline code with no hyperlink. If a public design-system URL is ever published, this is the line to update (README.md line 18 / the `loro-piana-aesthetic` reference).

## Commits

| Hash | Message |
|------|---------|
| ed407a0 | fix(12-01): Update USER_GUIDE.md lines 35-36 to match shipped strings |
| 68fa5d9 | fix(12-01): Update README.md lines 18 and 27 to match shipped strings + remove placeholder link |
