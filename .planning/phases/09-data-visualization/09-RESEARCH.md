# Phase 9: Data Visualization - Research

**Researched:** 2026-05-23
**Domain:** Altair 6 theme system, HTML table rendering in Streamlit, pandas display helpers
**Confidence:** HIGH (all findings verified against live environment)

---

## Summary

The environment runs **Altair 6.0.0** and **Streamlit 1.52.1**. This is critical: Altair 5.5+ deprecated `alt.themes` in favor of `alt.theme` (new decorator API). The old `alt.themes.register()` / `alt.themes.enable()` calls still work but emit `AltairDeprecationWarning`. Phase 9 must use the new `@alt.theme.register('loro_piana', enable=True)` decorator API exclusively.

The theme config dict is **baked into the chart spec JSON** at Python generation time (not applied browser-side), so `st.altair_chart()` sends a fully-configured spec to Vega-Embed. The existing `configure_chart_theme()` function in `chart_generator.py` must be **deleted entirely** — not skipped, not disabled — because calling `.configure_*()` on a chart overrides theme properties for those keys.

The editorial HTML table uses `st.markdown(html, unsafe_allow_html=True)`. Streamlit applies **no sanitization** when `unsafe_allow_html=True` — all HTML/CSS passes directly to the browser. Cell content from the DataFrame must be escaped with `html.escape()` (stdlib). The `title` attribute on `<td>` elements (for hover text) must use `html.escape(text, quote=True)`.

**Primary recommendation:** Register the Loro Piana theme via `@alt.theme.register('loro_piana', enable=True)` at module scope in `src/ui/altair_theme.py`, import it from `app.py` as a side-effect import, and delete `configure_chart_theme()` from `chart_generator.py`.

---

## Standard Stack

### Core (verified installed)
| Library | Version | Purpose |
|---------|---------|---------|
| altair | 6.0.0 | Chart generation + theming |
| streamlit | 1.52.1 | App framework, `st.markdown`, `st.expander`, `st.altair_chart` |
| pandas | (installed) | DataFrame manipulation, `df.head(50)` |
| html (stdlib) | built-in | `html.escape()` for XSS protection in HTML table cells |

### New module to create
| File | Purpose |
|------|---------|
| `src/ui/altair_theme.py` | Theme registration side-effect module. Import in `app.py` activates theme. |

### Installation
No new packages required. All dependencies are present.

---

## Architecture Patterns

### Recommended Project Structure (Phase 9 additions)

```
src/
├── ui/
│   ├── css.py               # Extend with editorial table CSS (append to LORO_PIANA_CSS)
│   ├── altair_theme.py      # NEW: Altair theme registration + VIBRANT_PALETTE constant
│   ├── results.py           # NEW (recommended): _render_editorial_table(), _render_empty_state()
│   └── splash.py            # Unchanged
└── chart_generator.py       # Edit: delete CHART_COLORS, delete configure_chart_theme(),
                             #        rewrite generate_chart() for horizontal bar + value labels
app.py                       # Edit: import altair_theme (side-effect), update display_results,
                             #        update 0-row handling in process_query + render paths
```

### Pattern 1: Altair Theme Registration (Altair 6 New API)

**What:** Register a named theme via decorator at module scope; importing the module activates it.

**When to use:** Always — one-shot at Python process start.

```python
# src/ui/altair_theme.py
import altair as alt

VIBRANT_PALETTE = ['#C0392B', '#2E5BBA', '#2E7D32', '#E67E22', '#F39C12']

@alt.theme.register('loro_piana', enable=True)
def loro_piana_theme() -> alt.theme.ThemeConfig:
    return alt.theme.ThemeConfig({
        'config': {
            'background': 'transparent',
            'title': {
                'font': 'EB Garamond',
                'fontSize': 20,
                'fontWeight': 300,
                'color': '#2C2420',
                'anchor': 'start',
            },
            'axis': {
                'labelFont': 'Inter',
                'labelFontSize': 11,
                'labelColor': '#6B5E52',
                'titleFont': 'Inter',
                'titleFontSize': 12,
                'titleColor': '#6B5E52',
                'gridColor': '#E8E0D8',
                'gridWidth': 1,
                'domainWidth': 0,    # no axis box stroke
                'tickWidth': 0,
            },
            'view': {
                'stroke': 'transparent',  # removes view border
            },
            'range': {
                # categorical color range — consumed by color=alt.Color(...) without
                # needing scale=alt.Scale(range=[...]) on every chart
                'category': VIBRANT_PALETTE,
            },
        }
    })
```

**Integration point in `app.py`:**
```python
import src.ui.altair_theme  # noqa: F401  — side-effect: registers & enables 'loro_piana'
```
Place this import BEFORE any `generate_chart()` call. Module caching ensures it runs once per Python process regardless of Streamlit reruns.

**Verified behavior (Altair 6.0.0):**
- Theme config IS baked into the chart spec JSON (`to_dict()` shows the config block).
- `st.altair_chart()` sends that JSON to Vega-Embed → theme renders in browser.
- `alt.theme.active` = `'loro_piana'` after registration.
- Process-global singleton; no threading race when registration happens at import time.

### Pattern 2: Altair Horizontal Bar with Value Labels

**What:** Layered chart — `mark_bar()` + `mark_text()` showing count to right of bar.

```python
# Source: verified against Altair 6.0.0 in project environment
VIBRANT_PALETTE = ['#C0392B', '#2E5BBA', '#2E7D32', '#E67E22', '#F39C12']

base = alt.Chart(chart_df)

bars = base.mark_bar().encode(
    x=alt.X(f'{y_col}:Q', title=y_col.replace('_', ' ').title()),
    y=alt.Y(f'{x_col}:N', sort='-x', title=x_col.replace('_', ' ').title()),
    color=alt.Color(
        f'{x_col}:N',
        scale=alt.Scale(range=VIBRANT_PALETTE),
        legend=None
    ),
    tooltip=[
        alt.Tooltip(x_col, title=x_col.replace('_', ' ').title()),
        alt.Tooltip(y_col, title=y_col.replace('_', ' ').title()),
    ]
)

labels = base.mark_text(
    align='left',
    baseline='middle',
    dx=4,
    font='Inter',
    fontSize=12,
    color='#2C2420'
).encode(
    x=alt.X(f'{y_col}:Q'),
    y=alt.Y(f'{x_col}:N', sort='-x'),
    text=alt.Text(f'{y_col}:Q', format=',')
)

chart = alt.layer(bars, labels).properties(
    title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
    width=550,
    height=300
)
```

**Sort behavior verified:** `sort='-x'` on `Y` encoding sorts categories descending by the X-axis value — largest bar at top. This replaces the old `sort="-y"` (which was vertical-bar syntax).

**Note on `range=VIBRANT_PALETTE`:** With `range.category` set in the theme, you can omit `scale=alt.Scale(range=VIBRANT_PALETTE)` on the Color encoding — the theme provides it. Either approach works; explicit `scale=` is safer during the transition (ensures theme doesn't interfere) and is fine to keep.

### Pattern 3: Editorial HTML Table Construction

**What:** Manual string-building approach (recommended over `df.to_html()` + post-processing).

**Why not `df.to_html()`:** It doesn't support per-cell CSS classes, per-column styling, or HTML `title` attributes for hover text without complex post-processing. Manual building is explicit and testable.

```python
# src/ui/results.py (recommended location)
import html
from typing import Optional
import pandas as pd

_PRIORITY_COLS = {'priority'}
_DATE_COLS = {'opened_at', 'resolved_at', 'closed_at', 'updated_at'}
_NUMBER_COLS = {'number'}           # INC IDs
_SCORE_COLS = {'similarity_score'}
_SHORT_DESC_COLS = {'short_description'}
_SHORT_DESC_MAX_CHARS = 140

def _cell_classes(col_name: str, series: pd.Series) -> tuple[str, str]:
    """Return (td_classes, cell_style) for a column."""
    col_lower = col_name.lower()
    if col_lower in _NUMBER_COLS:
        return 'lp-mono', 'text-align:right'
    if col_lower in _SCORE_COLS:
        return 'lp-mono lp-et-right', ''
    if col_lower in _PRIORITY_COLS:
        return 'lp-et-priority', ''
    if col_lower in _DATE_COLS:
        return 'lp-et-date', ''
    if col_lower in _SHORT_DESC_COLS:
        return 'lp-et-desc', ''
    if pd.api.types.is_numeric_dtype(series):
        return 'lp-et-right', ''
    return '', ''

def _render_editorial_table(df: pd.DataFrame) -> str:
    """Return HTML string for the editorial table."""
    if df.empty:
        return ''

    n_total = len(df)
    truncated = n_total > 50
    display_df = df.head(50) if truncated else df

    # Build column order: priority cols first
    priority_order = ['number', 'short_description', 'priority', 'opened_at', 'similarity_score']
    available = [c for c in priority_order if c in display_df.columns]
    rest = [c for c in display_df.columns if c not in priority_order]
    cols = available + rest
    display_df = display_df[cols]

    lines = ['<table class="lp-editorial-table">']
    # Header
    lines.append('<thead><tr>')
    for col in display_df.columns:
        lines.append(f'<th>{html.escape(col.replace("_", " ").upper())}</th>')
    lines.append('</tr></thead>')
    # Body
    lines.append('<tbody>')
    for _, row in display_df.iterrows():
        lines.append('<tr>')
        for col in display_df.columns:
            td_classes, _ = _cell_classes(col, display_df[col])
            raw_val = row[col]
            cell_text = '' if pd.isna(raw_val) else str(raw_val)
            col_lower = col.lower()

            if col_lower in _SHORT_DESC_COLS:
                display_text = cell_text[:_SHORT_DESC_MAX_CHARS] + '...' \
                    if len(cell_text) > _SHORT_DESC_MAX_CHARS else cell_text
                title_attr = f' title="{html.escape(cell_text, quote=True)}"'
            else:
                display_text = cell_text
                title_attr = ''
            class_attr = f' class="{td_classes}"' if td_classes else ''
            lines.append(
                f'<td{class_attr}{title_attr}>{html.escape(display_text)}</td>'
            )
        lines.append('</tr>')
    lines.append('</tbody>')
    lines.append('</table>')

    if truncated:
        caption = (
            f'<p class="lp-et-caption">'
            f'SHOWING 50 OF {n_total:,} ROWS · EXPAND BELOW FOR FULL DATA'
            f'</p>'
        )
        return '\n'.join(lines) + '\n' + caption

    return '\n'.join(lines)
```

### Pattern 4: 0-Row Editorial Empty State

**What:** Replaces the `_No results. Try different query or mode._` text in `process_query` content.

**Implementation path:** Phase 9 should:
1. **Remove** the `if row_count == 0: content_parts.append("_No results..._")` line from `process_query` (line 665-666 in current `app.py`).
2. **Change** the empty guard in both `render_chat_history` and `render_main_content` from:
   ```python
   if "results" in message and message["results"] is not None:
       if not message["results"].empty:
           display_results(...)
   ```
   to:
   ```python
   if "results" in message and message["results"] is not None:
       display_results(...)  # handles empty df internally
   ```
3. **Add** a 0-row branch at the start of `display_results`:
   ```python
   if df.empty:
       st.markdown(
           '<div class="lp-et-empty">'
           '<p class="lp-et-empty-label">NO RESULTS</p>'
           '<p class="lp-et-empty-body">No incidents matched your query. '
           'Try a different search or mode.</p>'
           '</div>',
           unsafe_allow_html=True,
       )
       return
   ```

**Note on backwards compatibility:** Historical messages stored in `st.session_state.messages` that were generated before Phase 9 will have `results` as either `None` or an empty DataFrame. The change to call `display_results` for empty frames will render the new editorial empty state for these historical messages (on rerun). This is acceptable — the user only sees it if they don't refresh the session.

### Anti-Patterns to Avoid

- **Keeping `configure_chart_theme()`:** Even if you just stop calling it, leaving the function in the file is a trap for future callers. Delete it entirely.
- **Using `alt.themes` (deprecated):** Emits warnings on every chart render. Use `alt.theme`.
- **Calling `alt.theme.enable()` on every Streamlit rerun:** Safe but unnecessary. Module-scope registration with `enable=True` runs once.
- **Expanding the mono CSS selector:** Do NOT add `td.lp-et-number, td.lp-et-score` to the global mono boundary selector in `css.py`. Instead, add `.lp-mono` class to the `<td>` element in Python and let the existing boundary handle it.
- **Using `df.to_html()`:** Loses per-cell control; `classes=` parameter applies to the whole table only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XSS protection for HTML cells | Custom regex sanitizer | `html.escape()` stdlib | Handles all HTML entities + `quote=True` for attributes |
| Color theme injection | Per-chart `scale=alt.Scale(range=...)` everywhere | `range.category` in theme config | One definition; auto-applied to all Color encodings |
| Altair chart config | `.configure_*()` chain on each chart | `@alt.theme.register` | Global, rerun-safe, no per-chart boilerplate |
| Unique widget keys | Timestamp generation | Pass `query_id` from `display_results` args | Already exists; reuse `f"export_{query_id}"`, etc. |

---

## Common Pitfalls

### Pitfall 1: Using the deprecated `alt.themes` API

**What goes wrong:** `alt.themes.register(...)` / `alt.themes.enable(...)` emit `AltairDeprecationWarning` on Altair 5.5+ (including 6.0.0). The warnings may pollute Streamlit logs.

**How to avoid:** Use `@alt.theme.register('loro_piana', enable=True)` decorator. Verified against Altair 6.0.0 in this environment.

### Pitfall 2: `configure_chart_theme()` overrides the new theme

**What goes wrong:** The existing `configure_chart_theme()` calls `chart.configure(background='#0a0a0a').configure_axis(labelColor='#e0e0e0')...`. When a theme is active and `.configure()` is also called, the `.configure()` call **wins for overlapping keys** — the old dark theme overrides the Loro Piana theme.

**How to avoid:** Delete `configure_chart_theme()` entirely. Remove the `chart = configure_chart_theme(chart)` call at line 424. The theme handles all chrome.

### Pitfall 3: `CHART_COLORS[0]` in the line chart `mark_line(color=CHART_COLORS[0])`

**What goes wrong:** The current code passes `color=CHART_COLORS[0]` (coral red `#FF6B6B`) directly as a mark property. When `CHART_COLORS` is deleted, this raises `NameError`.

**How to avoid:** Replace with the new vibrant palette's crimson: `color='#C0392B'` hardcoded or `color=VIBRANT_PALETTE[0]` imported from `altair_theme.py`.

**All `CHART_COLORS` references in `src/chart_generator.py`:**
- Line 17: `CHART_COLORS = [...]` — the definition itself (DELETE)
- Line 343: `scale=alt.Scale(range=CHART_COLORS)` in pie chart
- Line 378: `scale=alt.Scale(range=CHART_COLORS)` in bar chart
- Line 397: `color=CHART_COLORS[0]` in line chart mark

### Pitfall 4: Streamlit widget key collisions in chat history

**What goes wrong:** `display_results()` is called for EVERY message in `st.session_state.messages` during history render. If `st.expander`, `st.dataframe`, or `st.download_button` use static keys, Streamlit raises `DuplicateWidgetID` on the second message.

**How to avoid:** `display_results()` already receives `query_id` (unique timestamp string per message). Use it as suffix: `key=f"export_{query_id}"` for download button. `st.expander` has **no `key` parameter** (verified against Streamlit 1.52.1 signature) — that's fine, it doesn't create widget state. `st.dataframe` does accept `key=` — use `key=f"df_{query_id}"` if needed.

### Pitfall 5: `sort='-y'` (old vertical bar sort) vs `sort='-x'` (new horizontal)

**What goes wrong:** The current bar chart uses `x=category, y=value, sort='-y'`. In horizontal bars, the axes flip: `x=value, y=category`. The sort shorthand `-x` on the Y encoding means "sort categories by the X-axis field descending." Using `-y` by mistake sorts by the category column itself (alphabetically, descending).

**How to avoid:** In the horizontal bar, the Y encoding gets `sort='-x'`. Verified behavior: produces "largest bar at top" ordering.

### Pitfall 6: `html.escape()` on NaN / None cell values

**What goes wrong:** `html.escape(None)` raises `TypeError`. DataFrames may contain `NaN`, `None`, or `pd.NA`.

**How to avoid:** Normalize before escaping: `cell_text = '' if pd.isna(raw_val) else str(raw_val)`. Always call `html.escape()` on the string, not the raw value.

### Pitfall 7: 0-row edge case — chart_feedback still set

**What goes wrong:** When `row_count == 0` and the user asked for a chart, `infer_chart_type()` is called on an empty DataFrame. It returns `{"type": None, "feedback": "Chart requires at least 2 rows of data."}`. The `chart_feedback` string is stored in the message dict. In Phase 9, `display_results()` is called for empty DataFrames. The function must **not render** the `chart_feedback` warning when `df.empty` — the CONTEXT.md spec says: 0-row + chart requested → show 0-row empty state ONLY; suppress chart_feedback.

**How to avoid:** The 0-row branch in `display_results` must `return` before reaching the chart_feedback rendering logic.

### Pitfall 8: `format_dataframe_for_display()` call conflict

**What goes wrong:** The current `display_results()` calls `format_dataframe_for_display(df)` which applies its own `max_rows=100` truncation and `max_col_width=100` truncation. Phase 9's editorial table has its own 50-row and 140-char truncation logic. If `format_dataframe_for_display()` is still called for the editorial table, it may double-truncate descriptions at 100 chars instead of 140.

**How to avoid:** Pass the **raw `df`** directly to `_render_editorial_table()`. Keep calling `format_dataframe_for_display(df)` only for the `st.dataframe()` inside the expander (native Streamlit handles its own column-width concerns). Alternatively, drop `format_dataframe_for_display()` entirely from the expander path since `st.dataframe()` handles display natively — but this is a planner decision.

---

## Code Examples

### Altair Theme Registration (Altair 6 — verified)

```python
# src/ui/altair_theme.py
# Source: verified against Altair 6.0.0, Python 3.11
import altair as alt

VIBRANT_PALETTE: list[str] = ['#C0392B', '#2E5BBA', '#2E7D32', '#E67E22', '#F39C12']

@alt.theme.register('loro_piana', enable=True)
def loro_piana_theme() -> alt.theme.ThemeConfig:
    """Loro Piana editorial chart theme for SNOWGREP v2.2."""
    return alt.theme.ThemeConfig({
        'config': {
            'background': 'transparent',
            'title': {
                'font': 'EB Garamond',
                'fontSize': 20,
                'fontWeight': 300,
                'color': '#2C2420',
                'anchor': 'start',
            },
            'axis': {
                'labelFont': 'Inter',
                'labelFontSize': 11,
                'labelColor': '#6B5E52',
                'titleFont': 'Inter',
                'titleFontSize': 12,
                'titleColor': '#6B5E52',
                'gridColor': '#E8E0D8',
                'gridWidth': 1,
                'domainWidth': 0,
                'tickWidth': 0,
            },
            'view': {
                'stroke': 'transparent',
            },
            'range': {
                'category': VIBRANT_PALETTE,
            },
        }
    })
```

### Horizontal Bar with Value Labels (Altair 6 — verified)

```python
# Source: verified against Altair 6.0.0 layered chart compilation
from src.ui.altair_theme import VIBRANT_PALETTE

base = alt.Chart(chart_df)

bars = base.mark_bar().encode(
    x=alt.X(f'{y_col}:Q', title=y_col.replace('_', ' ').title()),
    y=alt.Y(f'{x_col}:N', sort='-x', title=x_col.replace('_', ' ').title()),
    color=alt.Color(f'{x_col}:N', scale=alt.Scale(range=VIBRANT_PALETTE), legend=None),
    tooltip=[alt.Tooltip(x_col), alt.Tooltip(y_col)],
)

labels = base.mark_text(
    align='left', baseline='middle', dx=4,
    font='Inter', fontSize=12, color='#2C2420'
).encode(
    x=alt.X(f'{y_col}:Q'),
    y=alt.Y(f'{x_col}:N', sort='-x'),
    text=alt.Text(f'{y_col}:Q', format=','),
)

chart = alt.layer(bars, labels).properties(
    title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
    width=550,
    height=max(200, len(chart_df) * 32),
)
```

### HTML Escaping (stdlib — verified)

```python
import html

# Cell content (safe for innerHTML)
safe_text = html.escape(str(raw_value))

# Attribute content (safe for title="...")
safe_attr = html.escape(str(raw_value), quote=True)
```

### Pie Chart (replace CHART_COLORS with theme palette)

```python
# Replace: scale=alt.Scale(range=CHART_COLORS)
# With:
from src.ui.altair_theme import VIBRANT_PALETTE

color=alt.Color(
    field=x_col,
    type='nominal',
    scale=alt.Scale(range=VIBRANT_PALETTE),
    legend=alt.Legend(title=x_col.replace('_', ' ').title())
)
```

### Line Chart (replace CHART_COLORS[0])

```python
# Replace: mark_line(point=True, color=CHART_COLORS[0])
# With:
chart = alt.Chart(chart_df).mark_line(
    point=True,
    color='#C0392B'  # crimson, matches VIBRANT_PALETTE[0]
)
# No color encoding needed for single-series; no legend rendered
```

---

## Integration into `app.py::display_results`

### Current Structure (lines 530–583)

```
display_results(df, sql, query_id, executive_summary, chart, chart_feedback):
  1. Executive summary (st.markdown)
  2. Chart display (st.altair_chart) or chart_feedback warning
  3. format_dataframe_for_display(df) + column ordering
  4. st.dataframe(display_df)
  5. st.columns([1,3])
     - col1: st.download_button("EXPORT CSV")
     - col2: st.expander("GENERATED SQL") → st.code(sql)
```

### Target Structure (Phase 9)

```
display_results(df, sql, query_id, executive_summary, chart, chart_feedback):
  0. [NEW] if df.empty → render editorial empty state → return (suppresses chart_feedback)
  1. Executive summary (unchanged)
  2. Chart display (unchanged call site; theme applies automatically)
     - chart_feedback restyled: "CHART UNAVAILABLE" small-caps + italic body
     - Remove: st.info(f"📊 {chart_feedback}") and st.warning(f"📊 {chart_feedback}")
  3. [NEW] st.markdown(_render_editorial_table(df), unsafe_allow_html=True)
  4. [NEW] with st.expander("EXPAND · INTERACTIVE VIEW", expanded=False):
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("EXPORT CSV", ..., key=f"export_{query_id}")
  5. SQL expander (unchanged, stays in col2 or moved outside columns)
```

### Call sites to update (in `app.py`)

**render_chat_history (line 516-525):** Remove the `if not message["results"].empty:` guard. Simplify to:
```python
if "results" in message and message["results"] is not None:
    display_results(
        message["results"],
        message.get("sql"),
        message.get("query_id", ""),
        message.get("executive_summary"),
        message.get("chart"),
        message.get("chart_feedback"),
    )
```

**render_main_content (line 815):** Same change — remove `.empty` guard.

**process_query (line 665-666):** Remove:
```python
if row_count == 0:
    content_parts.append("\n\n_No results. Try different query or mode._")
```
The editorial empty state in `display_results` replaces this.

---

## CSS Extension Strategy

Extend `LORO_PIANA_CSS` in `src/ui/css.py` by appending a `/* === Phase 9 DVZ-* === */` section. Do NOT create a separate CSS module — CONTEXT.md is explicit that `css.py` is the single source of truth for all Loro Piana CSS.

**New CSS classes to add:**

```css
/* === Phase 9 DVZ-01 — Editorial results table === */

.lp-editorial-table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  font-family: var(--lp-font-body);
  background: transparent;
}

/* Header row — warm-beige bg, EB Garamond small-caps */
.lp-editorial-table thead th {
  background: var(--lp-border);    /* #E8E0D8 warm-beige */
  color: var(--lp-text);
  font-family: var(--lp-font-headline);
  font-variant: small-caps;
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 16px 24px;
  border-bottom: 1px solid var(--lp-border);
  text-align: left;
}

/* Body rows — warm-beige 1px row dividers, no zebra, no vertical borders */
.lp-editorial-table tbody td {
  border-bottom: 1px solid var(--lp-border);   /* warm-beige row divider */
  border-left: none;
  border-right: none;
  padding: 16px 24px;
  color: var(--lp-text);                        /* charcoal #2C2420 */
  font-size: 15px;
  vertical-align: top;
}

.lp-editorial-table tbody tr:hover td {
  background: rgba(245, 240, 235, 0.5);        /* warm-beige tint */
}

/* Per-column type overrides */
.lp-editorial-table td.lp-et-priority {
  font-style: italic;
  font-size: 15px;
}

.lp-editorial-table td.lp-et-date {
  font-style: italic;
  font-size: 14px;
}

.lp-editorial-table td.lp-et-desc {
  min-width: 320px;
  font-size: 15px;
}

.lp-editorial-table td.lp-et-right,
.lp-editorial-table th.lp-et-right {
  text-align: right;
}

/* Truncation caption */
.lp-et-caption {
  font-family: var(--lp-font-body);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text);          /* charcoal — NOT muted gold */
  margin: var(--lp-space-3) 0 0 0;
  text-align: right;
}

/* 0-row empty state */
.lp-et-empty {
  padding: 48px 0;
  text-align: center;
}

.lp-et-empty-label {
  font-family: var(--lp-font-body);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text);           /* charcoal */
  margin: 0 0 var(--lp-space-3) 0;
}

.lp-et-empty-body {
  font-family: var(--lp-font-body);
  font-style: italic;
  font-size: 15px;
  color: var(--lp-text);
  margin: 0;
}

/* 1-data-point chart unavailable feedback */
.lp-chart-unavailable-label {
  font-family: var(--lp-font-body);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text);
  margin: 0 0 var(--lp-space-2) 0;
}

.lp-chart-unavailable-body {
  font-family: var(--lp-font-body);
  font-style: italic;
  font-size: 15px;
  color: var(--lp-text);
  margin: 0;
}
```

**Note on `.lp-mono` for INC IDs and similarity_score:** The existing Phase 6 mono boundary already covers `.lp-mono`. Apply `.lp-mono` as an additional class on those `<td>` elements in the Python rendering function. No new CSS needed for mono — just `class="lp-mono"` on the `<td>`.

---

## Test Impact

### tests/test_phase5_ui.py (22 tests — must stay green)

**Directly relevant tests:**
- `test_sc4_render_history_...` tests exercise `render_chat_history()`. Phase 9 modifies this function. However, the test messages have `"results": None` — so `display_results` is never called in these tests. Safe.
- `dataframe` mock is registered in `_build_streamlit_mock_surface()` (line 106). Phase 9 changes where `st.dataframe` is called (now inside an expander), but the mock surface still covers it. Safe.
- No test references `CHART_COLORS`, `display_results`, `chart_feedback`, or `configure_chart_theme`.

**Phase 9 must NOT break:**
- `test_sc3_chat_input_disabled_when_blocked_flag_true` — exercises `render_main_content()`. Phase 9 changes the empty-DataFrame guard inside `render_main_content`. The test never submits a query (chat_input returns `""`), so the `display_results` path is never reached. Safe.
- `test_sc4_render_provenance_caption_does_not_read_session_state` — AST-based test on `_render_provenance_caption`. Phase 9 does NOT touch this function. Safe.
- `test_sc5_readme_contains_required_topics` and `test_sc5_user_guide_...` — read README/USER_GUIDE files. Phase 9 doesn't change docs. Safe.

**`_build_streamlit_mock_surface()` may need extension** if Phase 9 adds new Streamlit primitives to `render_main_content` or `render_chat_history`. Currently safe because:
- `st.markdown` is already mocked
- `st.expander` is already mocked (`side_effect=lambda *a, **kw: _make_cm()`)
- `st.dataframe` is already mocked
- `st.download_button` is already mocked

If Phase 9 adds `st.info`, `st.warning` directly (instead of the HTML restyling), check that they're in the mock surface. Currently present: `info` and `warning` are in the surface (lines 101-102). Phase 9 replaces them with HTML — so these mocked calls will simply not happen. Safe.

### No existing test for `CHART_COLORS` or `configure_chart_theme`

Grepped the entire test suite: zero references. Deleting these is safe from a test-regression perspective.

### Phase 11 tests (not yet written)

Phase 11 is expected to add visual/CSS tests (`tests/test_phase6_visual.py` per CONTEXT.md). Phase 9 should NOT name CSS classes or HTML structures in ways that would conflict with the Phase 11 test plan. The `.lp-editorial-table` naming convention (Phase 6-style `lp-` prefix) is consistent.

---

## Module Location Recommendation: `_render_editorial_table`

**Recommendation: Create `src/ui/results.py`.**

Rationale:
- `src/utils.py` has zero Streamlit imports. It contains pure Python utilities (logging, error formatting, DataFrame formatting). Adding a function that generates HTML for Streamlit-rendered tables breaks its separation of concerns.
- `src/ui/results.py` is the logical home: it's a UI helper, lives alongside `css.py` and `splash.py`, and can import from `src/ui/css.py` for token values if needed.
- The module would export: `_render_editorial_table(df)`, `_render_empty_state()` (optional), and any other results-display HTML helpers.

**Counter-argument (planner may override):** If the planner prefers one fewer module, placing it in `utils.py` works mechanically — the function takes `pd.DataFrame` and returns `str`, no Streamlit calls. The Streamlit call is the `st.markdown()` in `display_results`, not in the helper itself. In that reading, utils.py is fine.

**Decision for planner:** Either location is technically valid. `src/ui/results.py` is cleaner.

---

## Open Questions

1. **`format_dataframe_for_display()` fate inside expander:** The current code calls this on the df before passing to `st.dataframe()`. Phase 9 passes raw `df` to the expander. Should `format_dataframe_for_display()` still be called for the expander's `st.dataframe()`? It truncates text at 100 chars and limits to 100 rows — both handled better by native `st.dataframe`. Recommendation: drop it for the expander path entirely (expander already has the full DataFrame via the `df` param).

2. **`#` column width in editorial table:** The `number` column (INC IDs like `INC0001234`) is mono, right-aligned. No `width: max-content` CSS class was specified — the CSS above uses `td` padding only. If INC IDs ever vary wildly in length, a `width: max-content` rule on `.lp-et-number` column header might be needed. Low-risk; can be added if visual inspection shows misalignment.

3. **Background `transparent` in Altair theme vs `#FFFFFF` card:** The assistant card has `background: #FFFFFF` (via `.lp-msg-assistant`). Charts are rendered inside that card via `st.altair_chart()`. Setting `background: transparent` in the theme means the chart background inherits the card's white — correct behavior. If the card background ever changes, chart background adapts automatically.

4. **Altair `LayerChart` and `st.altair_chart()`:** `st.altair_chart()` accepts `alt.Chart`, `alt.LayerChart`, `alt.ConcatChart`, and other top-level chart objects. The horizontal bar produces a `LayerChart` — verified to compile successfully. No API difference from the caller's perspective.

---

## Risk Register

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| `configure_chart_theme()` not deleted (leftover call overrides theme) | HIGH | HIGH without explicit task | Make deletion a mandatory task step, not optional |
| `CHART_COLORS[0]` NameError in line chart after deletion | HIGH | HIGH | Explicit task: replace with `'#C0392B'` literal or `VIBRANT_PALETTE[0]` |
| `sort='-x'` vs `sort='-y'` confusion on bar chart axis flip | MEDIUM | MEDIUM | Verify in code review: Y encoding gets `sort='-x'` |
| Duplicate widget keys in chat history (st.dataframe with key=) | MEDIUM | LOW | `st.dataframe` key is optional; only needed if selection enabled. Skip `key=` unless selection is used. |
| 0-row + chart_feedback rendered (spec says suppress) | MEDIUM | MEDIUM | Early return in `display_results` for empty df |
| Historical messages re-rendered with new editorial empty state | LOW | HIGH (by design) | Acceptable behavioral change; no data loss |
| CSS class name conflicts with future Phase 11 tests | LOW | LOW | Using consistent `lp-et-*` prefix mitigates |
| `html.escape()` not called on one column type | HIGH | MEDIUM | Code review: every `<td>` content goes through `html.escape()` |
| Altair `ThemeConfig` import path changes in future Altair versions | LOW | LOW | `alt.theme.ThemeConfig` is the stable public API in Altair 6 |

---

## Sources

### Primary (HIGH confidence — verified against live environment)
- Altair 6.0.0 `alt.theme` module — `help(alt.themes)` deprecation message, `@alt.theme.register` source code, `alt.theme.ThemeConfig` docs — verified 2026-05-23
- Streamlit 1.52.1 `st.expander` signature (no `key=` parameter), `st.dataframe` signature (`key=` optional), `st.download_button` signature — verified via `inspect.signature`
- `src/chart_generator.py` — CHART_COLORS defined at lines 17-28; referenced at lines 343, 378, 397
- `app.py` — `display_results` at lines 530-583; 0-row guard at lines 516-517; `process_query` no-results text at lines 665-666
- `src/ui/css.py` — 950 lines, 29KB; `LORO_PIANA_CSS` string; `__all__` whitelist; `.lp-mono` boundary at lines 363-371

### Secondary (MEDIUM confidence)
- `html.escape()` behavior verified empirically for `<`, `>`, `&`, `"` characters and `quote=True` for attribute escaping
- Altair `sort='-x'` shorthand behavior on Y nominal encoding verified by inspecting chart spec `to_dict()`
- `config.background` in theme spec verified to be baked into chart JSON (not applied client-side only)

---

## Metadata

**Confidence breakdown:**
- Altair theme API: HIGH — tested against installed 6.0.0, new decorator API confirmed
- HTML table rendering: HIGH — `unsafe_allow_html` behavior documented and verified
- Chart restyle: HIGH — `CHART_COLORS` reference sites confirmed by grep; layered chart compiled
- Integration split point: HIGH — `display_results` read and analyzed line-by-line
- CSS extension: HIGH — `css.py` read in full; extension approach consistent with Phase 6 pattern
- Test impact: HIGH — test file read in full; no tests reference chart or table rendering paths

**Research date:** 2026-05-23
**Valid until:** 2026-06-23 (Altair/Streamlit APIs are stable; 30-day window is conservative)
