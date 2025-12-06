"""
Data ingestion module for ServiceNow Incident Query Tool.
Handles CSV loading, type inference, and DuckDB persistence.
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Optional

import duckdb
import pandas as pd

from config import (
    CATEGORY_FIELDS,
    DATE_FIELDS,
    DUCKDB_PATH,
    TEXT_FIELDS,
)
from src.utils import IngestionError, logger


# Patterns for date detection
DATE_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}",  # ISO date: 2024-01-15
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # ISO datetime
    r"\d{2}/\d{2}/\d{4}",  # US date: 01/15/2024
    r"\d{2}-\d{2}-\d{4}",  # EU date: 15-01-2024
]


def _detect_column_type(
    column_name: str,
    sample_values: list[Any]
) -> str:
    """
    Detect the appropriate DuckDB type for a column.

    Args:
        column_name: Name of the column
        sample_values: Sample values from the column

    Returns:
        DuckDB type string
    """
    col_lower = column_name.lower()

    # Check known date fields
    if col_lower in [f.lower() for f in DATE_FIELDS]:
        return "TIMESTAMP"

    # Check known category fields
    if col_lower in [f.lower() for f in CATEGORY_FIELDS]:
        return "VARCHAR"

    # Check known text fields
    if col_lower in [f.lower() for f in TEXT_FIELDS]:
        return "VARCHAR"

    # Analyze sample values
    non_null_values = [v for v in sample_values if pd.notna(v) and str(v).strip()]

    if not non_null_values:
        return "VARCHAR"

    # Check for date patterns
    date_matches = 0
    for value in non_null_values[:10]:
        str_val = str(value)
        for pattern in DATE_PATTERNS:
            if re.match(pattern, str_val):
                date_matches += 1
                break

    if date_matches >= len(non_null_values[:10]) * 0.8:
        return "TIMESTAMP"

    # Check for numeric
    numeric_count = 0
    for value in non_null_values[:10]:
        try:
            float(str(value).replace(",", ""))
            numeric_count += 1
        except (ValueError, TypeError):
            pass

    if numeric_count >= len(non_null_values[:10]) * 0.9:
        # Check if integer or float
        all_int = all(
            float(str(v).replace(",", "")).is_integer()
            for v in non_null_values[:10]
            if pd.notna(v)
        )
        return "BIGINT" if all_int else "DOUBLE"

    # Default to VARCHAR
    return "VARCHAR"


def _infer_schema(df: pd.DataFrame) -> dict[str, str]:
    """
    Infer DuckDB schema from DataFrame.

    Args:
        df: Input DataFrame

    Returns:
        Dictionary mapping column names to DuckDB types
    """
    schema = {}
    for col in df.columns:
        sample_values = df[col].head(100).tolist()
        schema[col] = _detect_column_type(col, sample_values)
    return schema


def _get_sample_value(df: pd.DataFrame, column: str) -> Any:
    """
    Get a representative sample value from a column.

    Args:
        df: Input DataFrame
        column: Column name

    Returns:
        Sample value or empty string
    """
    non_null = df[column].dropna()
    if len(non_null) == 0:
        return ""

    # Get first non-empty value
    for val in non_null.head(10):
        if str(val).strip():
            return val

    return non_null.iloc[0] if len(non_null) > 0 else ""


def load_csv(
    file: str | Path | BinaryIO | BytesIO,
    table_name: str = "incidents"
) -> dict[str, Any]:
    """
    Load a CSV file into DuckDB with automatic type inference.

    Args:
        file: File path, BytesIO, or file-like object
        table_name: Name of the table to create

    Returns:
        Schema summary dictionary

    Raises:
        IngestionError: If CSV loading fails
    """
    logger.info("Starting CSV ingestion")

    try:
        # Try different encodings for CSV reading
        encodings = ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1']
        df = None

        for encoding in encodings:
            try:
                if isinstance(file, (str, Path)):
                    df = pd.read_csv(file, low_memory=False, encoding=encoding)
                else:
                    # Reset file position if BytesIO
                    if hasattr(file, "seek"):
                        file.seek(0)
                    df = pd.read_csv(file, low_memory=False, encoding=encoding)
                logger.info(f"Successfully read CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                logger.debug(f"Failed to read with {encoding} encoding, trying next...")
                continue

        if df is None:
            raise IngestionError(
                "Failed to read CSV file",
                "Could not decode file with any supported encoding (utf-8, cp1252, latin-1)"
            )

        if df.empty:
            raise IngestionError(
                "CSV file is empty",
                "The uploaded file contains no data rows."
            )

        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns")

        # Infer schema
        schema = _infer_schema(df)
        logger.info(f"Inferred schema: {schema}")

        # Convert date columns
        for col, dtype in schema.items():
            if dtype == "TIMESTAMP" and col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception as e:
                    logger.warning(f"Could not convert {col} to datetime: {e}")

        # Ensure database directory exists
        DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB and load data
        conn = duckdb.connect(str(DUCKDB_PATH))

        try:
            # Drop existing table if exists
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Register DataFrame and create table
            conn.register("temp_df", df)
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            conn.unregister("temp_df")

            # Get row count
            row_count = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            logger.info(f"Loaded {row_count} rows into {table_name}")

        finally:
            conn.close()

        # Build schema summary
        schema_summary = {
            "table_name": table_name,
            "row_count": row_count,
            "columns": [
                {
                    "name": col,
                    "type": schema[col],
                    "sample": str(_get_sample_value(df, col))[:100]
                }
                for col in df.columns
            ]
        }

        return schema_summary

    except IngestionError:
        raise
    except pd.errors.EmptyDataError:
        raise IngestionError(
            "CSV file is empty or malformed",
            "Could not read any data from the file."
        )
    except pd.errors.ParserError as e:
        raise IngestionError(
            "CSV parsing failed",
            f"The file could not be parsed as CSV: {str(e)}"
        )
    except Exception as e:
        logger.exception("Unexpected error during CSV ingestion")
        raise IngestionError(
            "Failed to load CSV file",
            str(e)
        )


def get_schema_summary(table_name: str = "incidents") -> dict[str, Any] | None:
    """
    Get schema summary for an existing table.

    Args:
        table_name: Name of the table

    Returns:
        Schema summary dictionary or None if table doesn't exist
    """
    if not DUCKDB_PATH.exists():
        return None

    try:
        conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)

        try:
            # Check if table exists
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                f"WHERE table_name = '{table_name}'"
            ).fetchall()

            if not tables:
                return None

            # Get row count
            row_count = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            # Get column info
            columns_info = conn.execute(
                f"DESCRIBE {table_name}"
            ).fetchall()

            # Get sample values
            sample_row = conn.execute(
                f"SELECT * FROM {table_name} LIMIT 1"
            ).fetchone()

            columns = []
            for i, col_info in enumerate(columns_info):
                col_name = col_info[0]
                col_type = col_info[1]
                sample = sample_row[i] if sample_row else ""
                columns.append({
                    "name": col_name,
                    "type": col_type,
                    "sample": str(sample)[:100] if sample else ""
                })

            return {
                "table_name": table_name,
                "row_count": row_count,
                "columns": columns
            }

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error getting schema summary: {e}")
        return None


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Get a DuckDB connection.

    Args:
        read_only: Whether to open in read-only mode

    Returns:
        DuckDB connection
    """
    if not DUCKDB_PATH.exists():
        raise IngestionError(
            "Database not found",
            "Please upload a CSV file first."
        )
    return duckdb.connect(str(DUCKDB_PATH), read_only=read_only)


def table_exists(table_name: str = "incidents") -> bool:
    """
    Check if a table exists in the database.

    Args:
        table_name: Name of the table

    Returns:
        True if table exists
    """
    if not DUCKDB_PATH.exists():
        return False

    try:
        conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name = '{table_name}'"
            ).fetchone()
            return result[0] > 0
        finally:
            conn.close()
    except Exception:
        return False
