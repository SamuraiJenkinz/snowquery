---
phase: quick-260621-aj0
plan: 01
subsystem: export
tags: [html-export, xss, regression-test, loro-piana]
dependency_graph:
  requires: []
  provides: [html-export-helpers, regression-test-lock]
  affects: [app.py, src/utils.py, tests/test_html_export.py]
tech_stack:
  added: []
  patterns: [self-contained-html, html.escape-first, pandas-to_html-escape]
key_files:
  created:
    - tests/test_html_export.py
  modified:
    - app.py
    - src/utils.py
decisions:
  - "_summary_to_html escapes BEFORE bold-promotion: html.escape() runs first so injected <script> in summary survives as &lt;script&gt;; then **bold** -> <strong>"
  - "generate_export_filename default extension stays 'csv' for backward compat; callers pass 'html' explicitly"
  - "XSS test asserts absence of '<script>' tag (injected-tag-specific), not blanket absence of '<'; the HTML doc legitimately uses '<' in its own CSS/markup"
metrics:
  duration: "~4 minutes"
  completed: "2026-06-21"
  tasks_completed: 1
  files_changed: 3
---

# Quick Task 260621-AJ0: HTML Export Query Report — Summary

**One-liner:** Self-contained Loro Piana HTML report with XSS-safe escaping and bold promotion, locked by five regression tests.

## What Was Done

This was a CAPTURE task. The feature implementation pre-existed as uncommitted changes in `app.py` and `src/utils.py`. The task added the missing regression test (`tests/test_html_export.py`) and committed all three files atomically.

### Feature (pre-existing, now committed)

**`src/utils.py`** gained:
- `build_html_report(question, df, executive_summary, *, sql, provider, model, route) -> str` — self-contained Loro Piana-styled HTML document; all dynamic values escaped via `html.escape`; empty/None DataFrame renders a no-results sentinel; inlines all CSS so the file opens offline.
- `_summary_to_html(executive_summary) -> str` — escapes first, then promotes `**bold**` to `<strong>`, splits blank lines into `<p>` blocks.
- `html_report_to_bytes(html) -> bytes` — `html.encode("utf-8")` for `st.download_button`.
- `generate_export_filename(prefix, extension="csv") -> str` — generalized from the prior CSV-only form; default extension preserved for backward compat.

**`app.py`** gained:
- EXPORT HTML download button beside EXPORT CSV in a `st.columns(2)` layout.
- `question`, `provider`, `model`, `route` threaded through `display_results` and both call sites.
- `"question"` and `"route"` keys added to the assistant message dict and `process_query` return dict.

### Regression Test (new)

**`tests/test_html_export.py`** — 5 test functions:

| Test | Behavior locked |
|------|----------------|
| `test_xss_escaping_in_question_cells_and_summary` | `<script>`, `<img>`, `<b>` injected in question/cells/summary produce no raw tags; `&lt;script&gt;` form IS present |
| `test_bold_promotion_in_executive_summary` | `**Key Findings**` → `<strong>Key Findings</strong>`; raw `**` form absent |
| `test_empty_dataframe_path_returns_no_results_message` | Empty `pd.DataFrame()` → no exception; "No matching incidents were found." present |
| `test_generate_export_filename_html_extension` | `extension='html'` → `.html` suffix; default call → `.csv` suffix (compat lock) |
| `test_html_report_to_bytes_returns_bytes_and_round_trips` | Returns `bytes`; `decode('utf-8')` round-trips to input |

## Verification

```
PYTHONPATH=. python -m pytest tests/test_html_export.py -q
# 5 passed in 0.36s

PYTHONPATH=. python -m pytest tests/ -q
# 108 passed, 1 warning in 29.93s  (103 prior + 5 new — no regressions)
```

## Commit

`befe0f9` — `feat(export): add self-contained Loro Piana HTML report export + regression test`

Files: `app.py`, `src/utils.py`, `tests/test_html_export.py` — committed atomically.

## Deviations from Plan

None. Plan executed exactly as written. Implementation pre-existed; only the test was added.

## Known Stubs

None. The HTML export is fully wired: `build_html_report` → `html_report_to_bytes` → `st.download_button` in `app.py`.

## Self-Check: PASSED

- `tests/test_html_export.py` exists and contains 5 `def test_` functions.
- Commit `befe0f9` exists: `git log --oneline -1` confirms.
- Full suite: 108 passed, 0 failed.
