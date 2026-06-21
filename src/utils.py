"""
Utility functions for ServiceNow Incident Query Tool.
Includes result formatting, error handling, and logging configuration.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from config import LOG_LEVEL


def setup_logging(name: str = "snow_query") -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    return logger


logger = setup_logging()


class QueryError(Exception):
    """Custom exception for query-related errors."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class IngestionError(Exception):
    """Custom exception for data ingestion errors."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class EmbeddingError(Exception):
    """Custom exception for embedding-related errors."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


def format_dataframe_for_display(
    df: pd.DataFrame,
    max_rows: int = 100,
    max_col_width: int = 100
) -> pd.DataFrame:
    """
    Format a DataFrame for display in Streamlit.

    Args:
        df: Input DataFrame
        max_rows: Maximum rows to display
        max_col_width: Maximum column width for text truncation

    Returns:
        Formatted DataFrame
    """
    if df.empty:
        return df

    # Limit rows
    display_df = df.head(max_rows).copy()

    # Truncate long text columns
    for col in display_df.select_dtypes(include=['object']).columns:
        display_df[col] = display_df[col].apply(
            lambda x: truncate_text(str(x), max_col_width) if pd.notna(x) else ""
        )

    return display_df


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length with ellipsis.

    Args:
        text: Input text
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_schema_for_llm(schema_summary: dict[str, Any]) -> str:
    """
    Format schema summary as a string for LLM context.

    Args:
        schema_summary: Schema dictionary from ingest module

    Returns:
        Formatted string suitable for LLM prompt
    """
    lines = [
        f"Table: {schema_summary.get('table_name', 'incidents')}",
        f"Total rows: {schema_summary.get('row_count', 0):,}",
        "",
        "Columns:"
    ]

    for col in schema_summary.get("columns", []):
        sample = col.get("sample", "")
        if sample and len(str(sample)) > 50:
            sample = str(sample)[:47] + "..."
        lines.append(f"  - {col['name']} ({col['type']}): e.g., {sample}")

    return "\n".join(lines)


def format_error_message(error: Exception) -> str:
    """
    Format an exception into a user-friendly error message.

    Args:
        error: Exception instance

    Returns:
        Formatted error message
    """
    if isinstance(error, (QueryError, IngestionError, EmbeddingError)):
        msg = error.message
        if error.details:
            msg += f"\n\nDetails: {error.details}"
        return msg

    return f"An unexpected error occurred: {str(error)}"


def generate_export_filename(prefix: str = "incidents", extension: str = "csv") -> str:
    """
    Generate a timestamped filename for exports.

    Args:
        prefix: Filename prefix
        extension: File extension WITHOUT the leading dot (e.g. "csv", "html")

    Returns:
        Filename string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension.lstrip('.')}"


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Convert DataFrame to CSV bytes for download.

    Args:
        df: Input DataFrame

    Returns:
        CSV data as bytes
    """
    return df.to_csv(index=False).encode("utf-8")


# Loro Piana palette (mirrors src/ui/css.py tokens) — kept inline so the
# exported report is fully self-contained (no external stylesheet/network).
_REPORT_PALETTE = {
    "bg": "#F5F0EB",
    "surface": "#FFFFFF",
    "border": "#E8E0D8",
    "text": "#2C2420",
    "text_muted": "#6B5E52",
    "accent": "#8B7355",
    "gold": "#B8A88A",
}


def _summary_to_html(executive_summary: str) -> str:
    """Convert the executive summary's lightweight markdown to safe HTML.

    The summary produced by generate_executive_summary() uses `**bold**`
    labels (e.g. "**Key Findings**:") and blank-line-separated paragraphs.
    This escapes everything first, then promotes `**...**` to <strong> and
    splits on blank lines into <p> blocks. No raw HTML from the LLM ever
    reaches the document.
    """
    from html import escape
    import re

    escaped = escape(executive_summary.strip())
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", escaped) if p.strip()]
    return "".join(
        f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs
    )


def build_html_report(
    question: str,
    df: pd.DataFrame,
    executive_summary: str | None = None,
    *,
    sql: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    route: str | None = None,
) -> str:
    """Build a self-contained, Loro Piana–styled HTML report of a query answer.

    The report bundles the original question, the executive summary, the full
    result table, and (when supplied) the generated SQL plus the provider/model
    provenance. All styling is inlined so the file opens correctly offline with
    no network access. Every dynamic value is HTML-escaped.

    Args:
        question: The natural-language question the user asked.
        df: The result DataFrame (rendered as a table; empty → "no results").
        executive_summary: Optional LLM summary (lightweight markdown).
        sql: Optional generated SQL to include in a footer block.
        provider: Optional provider key for the provenance line.
        model: Optional model identifier for the provenance line.
        route: Optional route label (structured/semantic/hybrid).

    Returns:
        A complete HTML document as a string.
    """
    from html import escape

    p = _REPORT_PALETTE
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Result table — pandas renders escaped cell values; we add the class hook.
    if df is None or df.empty:
        table_html = '<p class="report-empty">No matching incidents were found.</p>'
        row_note = "0 incidents"
    else:
        table_html = df.to_html(
            index=False, border=0, classes="report-table", na_rep="", escape=True
        )
        row_note = f"{len(df):,} incident{'s' if len(df) != 1 else ''}"

    summary_block = ""
    if executive_summary and executive_summary.strip():
        summary_block = (
            '<section class="report-summary">'
            '<h2>Executive Summary</h2>'
            f'<div class="report-summary-body">{_summary_to_html(executive_summary)}</div>'
            "</section>"
        )

    provenance_bits = []
    if route:
        provenance_bits.append(f"Route: {escape(route.upper())}")
    if provider:
        provenance_bits.append(f"Provider: {escape(provider)}")
    if model:
        provenance_bits.append(f"Model: {escape(model)}")
    provenance_line = " · ".join(provenance_bits)

    sql_block = ""
    if sql and sql.strip():
        sql_block = (
            '<section class="report-sql">'
            "<h2>Generated SQL</h2>"
            f"<pre><code>{escape(sql.strip())}</code></pre>"
            "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SNOWGREP Report — {escape(question)}</title>
<style>
  :root {{
    --bg: {p['bg']}; --surface: {p['surface']}; --border: {p['border']};
    --text: {p['text']}; --muted: {p['text_muted']}; --accent: {p['accent']};
    --gold: {p['gold']};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 48px 24px; background: var(--bg); color: var(--text);
    font-family: Inter, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6; -webkit-font-smoothing: antialiased;
  }}
  .report {{ max-width: 960px; margin: 0 auto; }}
  .report-brand {{
    font-size: 12px; letter-spacing: 0.28em; text-transform: uppercase;
    color: var(--accent); margin-bottom: 8px;
  }}
  h1, h2 {{
    font-family: "EB Garamond", Georgia, "Times New Roman", serif;
    font-weight: 500; color: var(--text);
  }}
  h1 {{ font-size: 30px; margin: 0 0 4px; line-height: 1.25; }}
  h2 {{
    font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--muted); border-bottom: 1px solid var(--border);
    padding-bottom: 8px; margin: 40px 0 16px;
  }}
  .report-meta {{ font-size: 13px; color: var(--muted); margin-bottom: 32px; }}
  .report-meta .rule {{
    height: 2px; width: 56px; background: var(--gold);
    margin: 20px 0 0; border: 0;
  }}
  .report-summary-body p {{ margin: 0 0 12px; }}
  .report-summary-body strong {{ color: var(--accent); }}
  .report-table {{
    width: 100%; border-collapse: collapse; font-size: 13px;
    background: var(--surface);
  }}
  .report-table th {{
    font-family: "EB Garamond", Georgia, serif; font-weight: 600;
    text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--accent);
    color: var(--text); white-space: nowrap;
  }}
  .report-table td {{
    padding: 9px 12px; border-bottom: 1px solid var(--border);
    vertical-align: top;
  }}
  .report-table tr:nth-child(even) td {{ background: var(--bg); }}
  .report-empty {{ color: var(--muted); font-style: italic; }}
  .report-sql pre {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 4px; padding: 14px 16px; overflow-x: auto;
    font-size: 12.5px; color: var(--text);
  }}
  footer {{
    margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--border);
    font-size: 11px; letter-spacing: 0.04em; color: var(--muted);
  }}
</style>
</head>
<body>
  <main class="report">
    <p class="report-brand">SNOWGREP · Incident Intelligence</p>
    <h1>{escape(question)}</h1>
    <div class="report-meta">
      {escape(row_note)} · Generated {escape(generated_at)}
      {f'<br>{provenance_line}' if provenance_line else ''}
      <hr class="rule">
    </div>
    {summary_block}
    <section class="report-results">
      <h2>Results</h2>
      {table_html}
    </section>
    {sql_block}
    <footer>Generated locally by SNOWGREP. All incident data was processed on-device.</footer>
  </main>
</body>
</html>"""


def html_report_to_bytes(html: str) -> bytes:
    """Encode an HTML report string to UTF-8 bytes for st.download_button."""
    return html.encode("utf-8")


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.

    Args:
        data: Input dictionary
        keys: Sequence of keys to traverse
        default: Default value if key not found

    Returns:
        Value at key path or default
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result
