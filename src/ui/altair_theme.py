"""
Side-effect import module — registers and activates the ``loro_piana`` Altair theme
for SNOWGREP v2.2.

Usage pattern
-------------
Import this module exactly once in ``app.py`` before any ``generate_chart()`` call::

    import src.ui.altair_theme  # noqa: F401  — side-effect: registers & enables loro_piana

Altair's module cache ensures the registration runs once per Python process regardless
of Streamlit reruns.

Design deviation
----------------
REQUIREMENTS.md DVZ-04 says "cashmere palette" for charts.  User-approved deviation:
cashmere (#F5F0EB warm-beige family) applies to chart **chrome** only — background,
gridlines, axis labels, and title.  Chart **data** uses the vibrant categorical palette
below so that bars, pies, and lines are visually distinct.

API note
--------
This module uses Altair 6's ``@alt.theme.register`` decorator (``alt.theme`` namespace).
The deprecated ``alt.themes.*`` API (register / enable / names) was removed in Altair 6
and must NOT be used — it emits ``AltairDeprecationWarning`` on Altair 5.5+ and will
raise ``AttributeError`` in future releases.  See 09-RESEARCH.md Pitfall 1.
"""

from __future__ import annotations

import altair as alt

__all__ = ["VIBRANT_PALETTE", "loro_piana_theme"]

# ---------------------------------------------------------------------------
# Canonical vibrant palette for SNOWGREP v2.2 charts
# ---------------------------------------------------------------------------
# Order matters: VIBRANT_PALETTE[0] is used as the single-series line-chart
# mark color.  Future modules (chart_generator.py) import from here rather
# than redefining the palette — Phase 6 single-source-of-truth pattern.
# ---------------------------------------------------------------------------
VIBRANT_PALETTE: list[str] = [
    "#C0392B",  # crimson       — primary / single-series line
    "#2E5BBA",  # royal blue
    "#2E7D32",  # forest green
    "#E67E22",  # burnt orange
    "#F39C12",  # mustard yellow
]


@alt.theme.register("loro_piana", enable=True)
def loro_piana_theme() -> alt.theme.ThemeConfig:
    """Loro Piana editorial chart theme for SNOWGREP v2.2.

    Returns an ``alt.theme.ThemeConfig`` whose ``config`` block is baked into
    every chart spec at Python generation time.  ``st.altair_chart()`` sends
    the fully-configured spec JSON to Vega-Embed, so the theme renders in the
    browser without any additional client-side theme activation.

    Chrome properties use the cashmere palette (warm-beige gridlines, charcoal
    titles, warm-gray labels).  Data-mark colors are provided via
    ``range.category`` which Altair auto-applies to nominal ``Color`` encodings.
    """
    return alt.theme.ThemeConfig(
        {
            "config": {
                # Inherits the assistant-card white background — do not set
                # a hard colour so the chart blends into whatever card bg is
                # active (future-proof against card colour changes).
                "background": "transparent",
                # EB Garamond title — same headline font as the rest of v2.2
                "title": {
                    "font": "EB Garamond",
                    "fontSize": 20,
                    "fontWeight": 300,
                    "color": "#2C2420",   # charcoal
                    "anchor": "start",
                },
                # Inter axis labels / gridlines — warm cashmere chrome
                "axis": {
                    "labelFont": "Inter",
                    "labelFontSize": 11,
                    "labelColor": "#6B5E52",   # warm-gray
                    "titleFont": "Inter",
                    "titleFontSize": 12,
                    "titleColor": "#6B5E52",   # warm-gray
                    "gridColor": "#E8E0D8",    # warm-beige
                    "gridWidth": 1,
                    "domainWidth": 0,          # no axis box stroke
                    "tickWidth": 0,
                },
                # Remove the thin view border Vega renders by default
                "view": {
                    "stroke": "transparent",
                },
                # Vibrant categorical palette — auto-applied to nominal Color
                # encodings without needing scale=alt.Scale(range=...) on each chart
                "range": {
                    "category": VIBRANT_PALETTE,
                },
            }
        }
    )
