"""Regression test locking the HTML-export helpers in src/utils.py.

Behaviors locked:
  1. XSS escaping — question, cell values, and executive_summary are all
     HTML-escaped; no raw <script> tag survives into the output document.
  2. Bold promotion — **bold** in the executive summary becomes <strong>.
  3. Empty-DataFrame path — no exception; "no results" message present.
  4. Filename extension contract — "html" extension yields .html; default
     (no extension arg) yields .csv (backward-compat lock).
  5. Bytes encoding — html_report_to_bytes returns bytes that round-trips.

Run with: PYTHONPATH=. python -m pytest tests/test_html_export.py -q
Or with the full suite: PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import pandas as pd

from src.utils import build_html_report, generate_export_filename, html_report_to_bytes


def test_xss_escaping_in_question_cells_and_summary():
    """XSS: injected <script>/<img>/<b> in question, cell value, and summary
    are all HTML-escaped; the raw opening tag '<script>' never appears in output.
    """
    injected_question = "<script>alert(1)</script>"
    injected_cell = "<img src=x onerror=1>"
    injected_summary = "<b>raw</b>"

    df = pd.DataFrame({"Description": [injected_cell]})
    html = build_html_report(
        injected_question,
        df,
        executive_summary=injected_summary,
    )

    # The raw opening tag must NOT appear anywhere in the document.
    assert "<script>" not in html, (
        "XSS: raw '<script>' tag found in output — question was not escaped."
    )
    # The escaped form of the injected question MUST be present.
    assert "&lt;script&gt;" in html, (
        "Escaped '&lt;script&gt;' form not found — question escaping broken."
    )
    # Cell value escaping: <img ... > must not survive as a literal tag.
    assert "<img " not in html, (
        "XSS: raw '<img' found in output — DataFrame cell value not escaped."
    )
    # Summary escaping: <b> must not survive as a literal tag.
    assert "<b>raw</b>" not in html, (
        "XSS: raw '<b>' tag found in summary output — summary not escaped first."
    )


def test_bold_promotion_in_executive_summary():
    """**bold** in the executive summary is promoted to <strong>; the raw
    asterisk form is absent.
    """
    summary = "**Key Findings**: stable"
    html = build_html_report("q", pd.DataFrame(), executive_summary=summary)

    assert "<strong>Key Findings</strong>" in html, (
        "Bold promotion failed — '<strong>Key Findings</strong>' not found."
    )
    assert "**Key Findings**" not in html, (
        "Raw '**Key Findings**' still present — bold was not promoted."
    )


def test_empty_dataframe_path_returns_no_results_message():
    """build_html_report with an empty DataFrame must not raise and must
    include the 'No matching incidents were found.' sentinel text.
    """
    result = build_html_report("q", pd.DataFrame())

    assert isinstance(result, str), "Expected str return for empty-df path."
    assert "No matching incidents were found." in result, (
        "Empty-df sentinel message absent from report output."
    )


def test_generate_export_filename_html_extension():
    """generate_export_filename with extension='html' yields a .html filename;
    the default call (no extension arg) yields .csv (backward-compat lock).
    """
    html_name = generate_export_filename("incident_report", "html")
    assert html_name.endswith(".html"), (
        f"Expected .html suffix for extension='html'; got {html_name!r}."
    )

    default_name = generate_export_filename("incidents")
    assert default_name.endswith(".csv"), (
        f"Backward-compat broken: default extension must be .csv; got {default_name!r}."
    )


def test_html_report_to_bytes_returns_bytes_and_round_trips():
    """html_report_to_bytes returns bytes that decode back to the original string."""
    source = "<html><body>hello</body></html>"
    result = html_report_to_bytes(source)

    assert isinstance(result, bytes), (
        f"html_report_to_bytes must return bytes; got {type(result).__name__}."
    )
    assert result.decode("utf-8") == source, (
        "Round-trip decode mismatch — encoding or content was altered."
    )


def test_summary_only_omits_results_and_sql_keeps_summary():
    """summary_only=True keeps the question + executive summary but drops the
    results table (the cell data) and the Generated SQL section.
    """
    df = pd.DataFrame({"number": ["INC1"], "short_description": ["UNIQUE_CELL_TOKEN"]})
    summary = "**Key Findings**: things are stable"
    html = build_html_report(
        "my question",
        df,
        executive_summary=summary,
        sql="SELECT * FROM incidents",
        summary_only=True,
    )

    # Summary + question retained.
    assert "<strong>Key Findings</strong>" in html
    assert "my question" in html
    # Results table content and SQL section omitted.
    assert "UNIQUE_CELL_TOKEN" not in html, "summary_only must not embed the data table"
    assert "Generated SQL" not in html, "summary_only must omit the SQL section"
    assert "<h2>Results</h2>" not in html, "summary_only must omit the Results section"


def test_summary_only_without_summary_states_absence():
    """summary_only=True with no executive summary still produces a valid doc
    that explicitly notes the summary is absent (no near-empty document)."""
    html = build_html_report("q", pd.DataFrame(), executive_summary=None, summary_only=True)

    assert html.strip().startswith("<!DOCTYPE html>")
    assert "No executive summary was generated" in html


def test_full_report_still_includes_results_and_sql():
    """Regression guard: the default (non-summary_only) report keeps the data
    table and SQL — summary_only must not have changed the full-report path."""
    df = pd.DataFrame({"number": ["INC1"], "short_description": ["UNIQUE_CELL_TOKEN"]})
    html = build_html_report(
        "q", df, executive_summary="**X**: y", sql="SELECT 1 FROM incidents"
    )

    assert "UNIQUE_CELL_TOKEN" in html, "full report must embed the data table"
    assert "<h2>Results</h2>" in html
    assert "Generated SQL" in html
