"""
Utility functions for ServiceNow Incident Query Tool.
Includes result formatting, error handling, and logging configuration.
"""
import logging
import sys
from datetime import datetime
from typing import Any

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


def generate_export_filename(prefix: str = "incidents") -> str:
    """
    Generate a timestamped filename for exports.

    Args:
        prefix: Filename prefix

    Returns:
        Filename string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.csv"


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Convert DataFrame to CSV bytes for download.

    Args:
        df: Input DataFrame

    Returns:
        CSV data as bytes
    """
    return df.to_csv(index=False).encode("utf-8")


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
