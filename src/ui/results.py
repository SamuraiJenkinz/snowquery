"""Editorial HTML renderers for SNOWGREP v2.2 results layer.

Three pure-Python string builders. No Streamlit dependency — callers inject
the returned HTML via ``st.markdown(html, unsafe_allow_html=True)``.

XSS-safety contract
-------------------
- Every ``<td>`` cell value is passed through ``html.escape()`` before
  interpolation.
- ``short_description`` cells that receive a ``title=`` hover attribute use
  ``html.escape(text, quote=True)`` to escape both tags and attribute-special
  characters (``"``, ``'``, ``&``).
- ``None`` / NaN values are normalised to ``""`` *before* escaping; calling
  ``html.escape(None)`` raises ``TypeError``.

Mono-boundary pattern
---------------------
``number`` (INC IDs) and ``similarity_score`` cells receive a ``lp-mono``
class on their ``<td>`` elements.  They inherit JetBrains Mono via the
Phase 6 mono-boundary rule in ``src/ui/css.py``::

    code, pre, kbd, samp, .lp-mono, [data-testid="stCodeBlock"], ...

The global selector is NOT expanded here — only the class is applied.
"""

from __future__ import annotations

import html

import pandas as pd

# ---------------------------------------------------------------------------
# Column-classification constants
# ---------------------------------------------------------------------------

_NUMBER_COLS: frozenset[str] = frozenset({"number"})
"""INC ID column → mono + right-align."""

_SCORE_COLS: frozenset[str] = frozenset({"similarity_score"})
"""Similarity score column → mono + right-align."""

_PRIORITY_COLS: frozenset[str] = frozenset({"priority"})
"""Priority column → italic."""

_DATE_COLS: frozenset[str] = frozenset({"opened_at", "resolved_at", "closed_at", "updated_at"})
"""Date-like columns → italic, slightly smaller."""

_SHORT_DESC_COLS: frozenset[str] = frozenset({"short_description"})
"""Short description column → min-width 320px, 140-char visible truncation."""

_TRUNCATION_CAP: int = 50
"""DVZ-03 user-approved deviation from REQUIREMENTS.md ``>1000`` literal.

Editorial table is the hero view and must always be scannable at a glance;
rows beyond 50 belong in the expander's native ``st.dataframe``.
"""

_SHORT_DESC_MAX_CHARS: int = 140
"""Visible cell length cap; full text shown in ``title=`` hover attribute."""

_PRIORITY_COLUMN_ORDER: tuple[str, ...] = (
    "number",
    "short_description",
    "priority",
    "opened_at",
    "similarity_score",
)
"""Priority columns rendered first (left-to-right) when present in the df."""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _td_classes(col_name: str, series: pd.Series) -> str:
    """Return space-separated CSS class string for a ``<td>`` element.

    Parameters
    ----------
    col_name:
        Column name (will be compared lowercased).
    series:
        The full column Series — used to detect numeric dtypes for
        non-named columns.

    Returns
    -------
    str
        Space-separated CSS class string (may be empty).
    """
    col_lower = col_name.lower()

    if col_lower in _NUMBER_COLS or col_lower in _SCORE_COLS:
        return "lp-mono lp-et-right"
    if col_lower in _PRIORITY_COLS:
        return "lp-et-priority"
    if col_lower in _DATE_COLS:
        return "lp-et-date"
    if col_lower in _SHORT_DESC_COLS:
        return "lp-et-desc"
    if pd.api.types.is_numeric_dtype(series):
        return "lp-et-right"
    return ""


def _ordered_columns(columns: list[str]) -> list[str]:
    """Return columns reordered so priority columns come first.

    Priority columns (``_PRIORITY_COLUMN_ORDER``) are placed in their
    specified order when present, followed by all remaining columns in
    their original order.

    Parameters
    ----------
    columns:
        Original column list from the DataFrame.

    Returns
    -------
    list[str]
        Reordered column list.
    """
    cols_set = set(columns)
    priority = [c for c in _PRIORITY_COLUMN_ORDER if c in cols_set]
    rest = [c for c in columns if c not in _PRIORITY_COLUMN_ORDER]
    return priority + rest


# ---------------------------------------------------------------------------
# Public renderers
# ---------------------------------------------------------------------------


def _render_editorial_table(df: pd.DataFrame) -> str:
    """Return an editorial HTML table string for *df*.

    Behaviour
    ---------
    - Returns ``""`` for an empty DataFrame.
    - Truncates to ``_TRUNCATION_CAP`` (50) rows and appends a spec-locked
      caption when ``len(df) > 50``.
    - Reorders columns so priority columns appear first.
    - Applies per-column CSS classes via ``_td_classes``.
    - Truncates ``short_description`` cells at 140 chars with an ellipsis;
      full text is exposed via a ``title=`` hover attribute.
    - All cell content is XSS-escaped via ``html.escape()``.

    Parameters
    ----------
    df:
        Result DataFrame from a query.  May have any column subset.

    Returns
    -------
    str
        HTML string (table + optional caption).  Caller injects via
        ``st.markdown(html, unsafe_allow_html=True)``.
    """
    if df.empty:
        return ""

    n_total = len(df)
    truncated = n_total > _TRUNCATION_CAP
    display_df = df.head(_TRUNCATION_CAP) if truncated else df

    # Reorder columns
    ordered_cols = _ordered_columns(list(display_df.columns))
    display_df = display_df.reindex(columns=ordered_cols)

    parts: list[str] = []

    # ---- Table open + header ----
    parts.append('<table class="lp-editorial-table">')
    parts.append("<thead><tr>")
    for col in ordered_cols:
        header_text = html.escape(col.replace("_", " ").upper())
        parts.append(f"<th>{header_text}</th>")
    parts.append("</tr></thead>")

    # ---- Body ----
    parts.append("<tbody>")
    for _, row in display_df.iterrows():
        parts.append("<tr>")
        for col in ordered_cols:
            raw_val = row[col]
            # NaN/None → empty string BEFORE escaping (html.escape(None) raises TypeError)
            cell_text = "" if pd.isna(raw_val) else str(raw_val)

            classes = _td_classes(col, display_df[col])
            class_attr = f' class="{classes}"' if classes else ""

            col_lower = col.lower()
            if col_lower in _SHORT_DESC_COLS and len(cell_text) > _SHORT_DESC_MAX_CHARS:
                display_text = cell_text[:_SHORT_DESC_MAX_CHARS] + "..."
                title_attr = f' title="{html.escape(cell_text, quote=True)}"'
            else:
                display_text = cell_text
                title_attr = ""

            parts.append(
                f"<td{class_attr}{title_attr}>{html.escape(display_text)}</td>"
            )
        parts.append("</tr>")
    parts.append("</tbody>")

    # ---- Table close ----
    parts.append("</table>")

    # ---- Truncation caption (spec-locked verbatim) ----
    # Middot is U+00B7; N is comma-formatted.
    if truncated:
        parts.append(
            f'<p class="lp-et-caption">'
            f"SHOWING 50 OF {n_total:,} ROWS · EXPAND BELOW FOR FULL DATA"
            f"</p>"
        )

    return "".join(parts)


def _render_empty_state() -> str:
    """Return the spec-locked 0-row empty-state HTML fragment.

    Spec-locked verbatim strings (do NOT alter):
    - Label: ``NO RESULTS``
    - Body:  ``No incidents matched your query. Try a different search or mode.``

    Body text is charcoal (NOT muted gold) per the Phase 9 text-contrast
    principle: decorative de-emphasis is reserved for provenance captions
    and chart axis labels only.

    Returns
    -------
    str
        Self-contained ``<div>`` HTML fragment.
    """
    return (
        '<div class="lp-et-empty">'
        '<p class="lp-et-empty-label">NO RESULTS</p>'
        '<p class="lp-et-empty-body">'
        "No incidents matched your query. Try a different search or mode."
        "</p>"
        "</div>"
    )


def _render_chart_unavailable(feedback: str) -> str:
    """Return the editorial chart-unavailable card for a 1-data-point guard.

    The ``feedback`` argument comes from ``chart_generator`` (e.g.
    ``"Chart requires at least 2 rows of data."``).  It is HTML-escaped
    defensively even though the source is internal.

    Spec-locked label: ``CHART UNAVAILABLE``

    Parameters
    ----------
    feedback:
        Human-readable explanation string from the chart generator.

    Returns
    -------
    str
        Self-contained ``<div>`` HTML fragment.
    """
    escaped_feedback = html.escape(feedback)
    return (
        '<div class="lp-chart-unavailable">'
        '<p class="lp-chart-unavailable-label">CHART UNAVAILABLE</p>'
        f'<p class="lp-chart-unavailable-body">{escaped_feedback}</p>'
        "</div>"
    )


__all__ = ["_render_editorial_table", "_render_empty_state", "_render_chart_unavailable"]
