---
phase: 06-foundation
plan: 02
subsystem: ui
tags: [css, app-wiring, page-chrome, loro-piana, streamlit, refactor]

# Dependency graph
requires:
  - "06-01 (src/ui/css.py LORO_PIANA_CSS importable)"
provides:
  - "app.py wired to consume LORO_PIANA_CSS via single-line injection"
  - "Brutalist CSS block deleted from app.py (no archive)"
  - "page_icon refreshed to ✦ (U+2726) — matches Loro Piana quiet-luxury chrome"
affects: [07, 08, 09, 10, 11]

# Tech tracking
tech-stack:
  added: []  # No new dependencies; pure refactor + 1-char chrome change
  patterns:
    - "Single-injection CSS consumer: f-string wrapping LORO_PIANA_CSS in one <style> tag"
    - "Flat import convention: from src.ui.css import LORO_PIANA_CSS (no relative imports)"
    - "Page chrome character glyph (✦) sourced directly as UTF-8 codepoint, no escape sequence"

key-files:
  created: []
  modified:
    - "app.py"

key-decisions:
  - "Brutalist block deleted outright (per CONTEXT.md), no legacy_brutalist_css.py archive"
  - "Single Edit operation replaced the ~315-line block with the 4-line injection (atomic refactor)"
  - "Two atomic commits (Task 1 refactor + Task 2 chore) — easier bisect than a single squashed commit"
  - "AST verification used io.open(..., encoding='utf-8') form on Windows (default cp1252 codec cannot read ✦/▣/em-dash bytes); semantically equivalent to plan's open() form, just codec-safe"

patterns-established:
  - "app.py = consumer of src/ui/css.LORO_PIANA_CSS (read-only; v2.2 modules never duplicate the CSS string)"
  - "Page chrome glyph is a single character in source; no \\u escapes"

# Metrics
duration: 5min
completed: 2026-05-22
---

# Phase 6 Plan 02: Wire App and Page Chrome Summary

**Brutalist CSS block deleted from `app.py` and replaced with a single-line `LORO_PIANA_CSS` injection from `src.ui.css`; `page_icon` refreshed from `▣` (U+25A3) to `✦` (U+2726) to match the v2.2 quiet-luxury chrome — v2.1 locked UI strings and the `_render_provenance_caption` invariant remain untouched.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-22T19:37:10Z
- **Completed:** 2026-05-22T19:42:22Z
- **Tasks:** 2 of 2
- **Files modified:** 1 (`app.py`)

## Accomplishments

- `app.py` now imports `LORO_PIANA_CSS` from `src.ui.css` (flat-import convention).
- Entire brutalist CSS slab (comment header + `st.markdown("""<style>...</style>""", unsafe_allow_html=True)` call) deleted as a single contiguous block.
- Replaced with single injection: `st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)` — preceded by a 3-line comment header pointing to `src/ui/css.py`.
- `page_icon` swapped from `▣` to `✦` (U+2726 BLACK FOUR POINTED STAR) — single character glyph in source, no escape sequence.
- `page_title="SNOWGREP"`, `layout="wide"`, `initial_sidebar_state="expanded"` all preserved unchanged.
- v2.1 locked UI strings — `"LLM provider"`, `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"QUERY DISABLED — see sidebar warning"` — all still present in `app.py` (verified by grep, each ≥1 match).
- `tests/test_phase5_ui.py` still passes (22 of 22 tests green) — `_render_provenance_caption` invariant untouched.

## Line Range Deleted from `app.py`

- **Before edits:** 1078 lines (315 lines of brutalist CSS at lines 38–352).
- **After edits:** 763 lines.
- **Net deletion:** 315 lines (312 deleted + 3 inserted in Task 1; 1 deleted + 1 inserted in Task 2 = no further net change).
- **Block boundaries:** Brutalist block ran from line 38 (`# ============================================================`) through line 352 (`""", unsafe_allow_html=True)`); replaced with 4 lines (3-line comment + 1-line injection) at the same position.

## Task Commits

Each task committed atomically:

1. **Task 1: replace brutalist CSS block with LORO_PIANA_CSS injection** — `99befab` (refactor)
   - 1 file changed, 3 insertions(+), 312 deletions(-)
2. **Task 2: swap page_icon ▣ → ✦** — `779fa04` (chore)
   - 1 file changed, 1 insertion(+), 1 deletion(-)

Plan metadata commit follows this SUMMARY.

## Files Modified

- `app.py` — brutalist `<style>` block deleted (lines 38–352); replaced with `LORO_PIANA_CSS` import + single-line `st.markdown` injection. `page_icon` swapped `▣` → `✦`. No other lines touched.

## Verification — Task 1 (8 grep/parse checks)

All 8 verification gates pass:

| # | Check | Expected | Actual |
|---|-------|----------|--------|
| 1 | `python -c "import ast, io; ast.parse(io.open('app.py', encoding='utf-8').read())"` | exit 0 | exit 0 (OK) |
| 2 | `grep -c "from src.ui.css import LORO_PIANA_CSS" app.py` | 1 | 1 |
| 3 | `grep -c 'st.markdown(f"<style>{LORO_PIANA_CSS}</style>"' app.py` | 1 | 1 |
| 4 | `grep -c "#0a0a0a" app.py` | 0 | 0 |
| 5 | `grep -cE "font-family: 'JetBrains Mono', 'Courier New', monospace" app.py` | 0 | 0 |
| 6 | `grep -c "<style>" app.py` | 1 | 1 |
| 7a | `grep -c '"LLM provider"' app.py` | ≥1 | 2 |
| 7b | `grep -c '"Azure OpenAI"' app.py` | ≥1 | 2 |
| 7c | `grep -c '"Anthropic Claude (MGTI)"' app.py` | ≥1 | 2 |
| 7d | `grep -c 'QUERY DISABLED' app.py` | ≥1 | 1 |
| 8 | `python -m py_compile app.py` | exit 0 | exit 0 (OK) |

## Verification — Task 2 (5 checks)

| # | Check | Expected | Actual |
|---|-------|----------|--------|
| 1 | `grep -c 'page_icon="✦"' app.py` | 1 | 1 |
| 2 | `grep -c 'page_icon="▣"' app.py` | 0 | 0 |
| 3 | `grep -c 'page_title="SNOWGREP"' app.py` | 1 | 1 |
| 4 | `python -c "import ast, io; ast.parse(io.open('app.py', encoding='utf-8').read())"` | exit 0 | exit 0 |
| 5 | `python -c "src = open('app.py', encoding='utf-8').read(); assert '✦' in src"` | OK | OK |

Additional byte-level checks (Task 2 must_have):

- BOM check: first 3 bytes are `22 22 22` (the docstring `"""`), **not** `EF BB BF` — file is UTF-8 **without** BOM ✓
- `✦` (U+2726) encoded as `E2 9C A6` at byte offset 896 ✓
- Old `▣` (U+25A3, `E2 96 A3`) absent from file ✓

## Phase 5 Regression

- **`python -m pytest tests/test_phase5_ui.py -q`** → **22 passed in 35.15s** ✓
- `_render_provenance_caption(provider, model)` AST lock test passes — helper still never reads `st.session_state`.
- All v2.1 locked UI strings still asserted true.

## v2.1 Locked Strings Confirmation

Direct grep verification post-edit (all still present verbatim):

- `"LLM provider"` — 2 occurrences (line 366 comment + line 607 selectbox label)
- `"Azure OpenAI"` — 2 occurrences
- `"Anthropic Claude (MGTI)"` — 2 occurrences
- `"QUERY DISABLED — see sidebar warning"` — 1 occurrence (line 1000 chat_input placeholder)

## Decisions Made

- **Single-Edit deletion:** The brutalist slab was deleted in one `Edit` call (old_string = full 315-line block, new_string = 4-line replacement) rather than incrementally. Atomic, no intermediate broken state.
- **No archive file:** Per CONTEXT.md and plan constraint, the old block was deleted outright (no `legacy_brutalist_css.py`). The deleted block is recoverable via `git show 99befab^:app.py`.
- **AST verification codec form:** Used `python -c "import ast, io; ast.parse(io.open('app.py', encoding='utf-8').read())"` (Task 2's spec form) for both tasks, because Windows' default cp1252 codec cannot decode the UTF-8 bytes for `✦`/`▣`/em-dash that exist elsewhere in the file. Semantically equivalent to plan Task 1's `open('app.py').read()` form on a POSIX system; the AST parse result (file is valid Python) is what the gate actually proves.
- **Two atomic commits over one squash:** Each task got its own commit (`99befab` refactor, `779fa04` chore) so git bisect can isolate a regression to either the CSS swap or the chrome glyph swap independently.

## Deviations from Plan

**One environment-level adaptation:**

- **Task 1 verify step 1 codec adjustment** — Plan specified `python -c "import ast; ast.parse(open('app.py').read())"`. On Windows (cp1252 default), that fails with `UnicodeDecodeError` because `app.py` contains UTF-8 bytes (`✦`, em-dash) that cp1252 cannot decode. Used the explicit-encoding form `python -c "import ast, io; ast.parse(io.open('app.py', encoding='utf-8').read())"` instead — same semantic check (file parses as valid Python), codec-safe. This is the exact form the plan specifies for Task 2 verify step 4, so it's plan-internal consistency, not a divergence in intent. Plan executed exactly as written in all other respects.

No other deviations. No bug fixes, no missing-critical additions, no blocking-issue fixes, no architectural changes.

## Issues Encountered

None. Both edits succeeded on first attempt; all verify checks green on first run.

## User Setup Required

None — no external service configuration required. Streamlit will pick up the new CSS on next `streamlit run app.py` reload.

## Next Phase Readiness

- **Plan 03 (smoke-render verification)** can proceed: `app.py` imports cleanly, AST parses, `py_compile` succeeds, and `LORO_PIANA_CSS` is injected exactly once. Plan 03 should be a render smoke test (manual or scripted Streamlit boot) confirming no console errors and the Loro Piana canvas paints.
- **Phase 7 (splash) and Phase 8 (sidebar + main restyle)** unblocked: `app.py` is now a clean canvas reading from `src/ui/css.py` — future phases can extend `LORO_PIANA_CSS` (in the css module) and the changes will flow into `app.py` automatically.
- **v2.1 invariants preserved:** `_render_provenance_caption` untouched, all locked UI strings intact, `tests/test_phase5_ui.py` green.

No blockers; no concerns.

---
*Phase: 06-foundation*
*Completed: 2026-05-22*
