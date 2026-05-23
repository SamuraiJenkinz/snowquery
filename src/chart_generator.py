"""Chart generation module for SNOWGREP.
Renders Pie / Bar / Line charts using Altair, styled by the loro_piana theme
(see src/ui/altair_theme.py).
"""
from __future__ import annotations

import re
from typing import Any, Optional

import altair as alt
import pandas as pd

from src.utils import logger
from src.ui.altair_theme import VIBRANT_PALETTE

# Chart detection patterns
CHART_PATTERNS = {
    "pie": [r"pie\s+chart", r"pie\s+graph", r"breakdown\s+by", r"proportion"],
    "bar": [r"bar\s+chart", r"bar\s+graph", r"compare", r"top\s+\d+", r"ranking"],
    "line": [r"line\s+chart", r"trend", r"over\s+time", r"per\s+week", r"per\s+month"],
}

# Maximum categories for different chart types
MAX_PIE_SLICES = 10
MAX_BAR_CATEGORIES = 20
MIN_ROWS_FOR_CHART = 2


def _detect_column_type(series: pd.Series) -> str:
    """
    Detect the type of a column for chart purposes.

    Args:
        series: pandas Series to analyze

    Returns:
        Column type: 'categorical', 'numeric', or 'temporal'
    """
    # Check for temporal data
    if pd.api.types.is_datetime64_any_dtype(series):
        return "temporal"

    # Try parsing as datetime for string columns
    if series.dtype == "object":
        try:
            # Try parsing with warnings suppressed
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pd.to_datetime(series.dropna().head(10), errors="raise")
            return "temporal"
        except (ValueError, TypeError):
            pass
        # String columns are categorical
        return "categorical"

    # Check for numeric data
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Default to categorical for other types
    return "categorical"


def _match_chart_pattern(query: str, chart_type: str) -> bool:
    """
    Check if query text matches patterns for a specific chart type.

    Args:
        query: User query text
        chart_type: Chart type to check ('pie', 'bar', 'line')

    Returns:
        True if pattern matches
    """
    query_lower = query.lower()
    patterns = CHART_PATTERNS.get(chart_type, [])

    for pattern in patterns:
        if re.search(pattern, query_lower):
            return True

    return False


def _consolidate_small_categories(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    max_categories: int
) -> pd.DataFrame:
    """
    Consolidate small categories into 'Other' category.

    Args:
        df: Input DataFrame
        x_col: Category column name
        y_col: Value column name
        max_categories: Maximum number of categories to keep

    Returns:
        DataFrame with consolidated categories
    """
    if len(df) <= max_categories:
        return df

    # Sort by value and keep top N-1 categories
    df_sorted = df.sort_values(y_col, ascending=False)
    top_categories = df_sorted.head(max_categories - 1)
    other_categories = df_sorted.tail(len(df) - (max_categories - 1))

    # Sum the 'Other' categories
    if len(other_categories) > 0:
        other_row = pd.DataFrame([{
            x_col: "Other",
            y_col: other_categories[y_col].sum()
        }])
        result = pd.concat([top_categories, other_row], ignore_index=True)
    else:
        result = top_categories

    return result


def infer_chart_type(query: str, df: pd.DataFrame) -> dict[str, Any] | None:
    """
    Analyze query text and DataFrame to infer appropriate chart type.

    Args:
        query: User's natural language query
        df: Result DataFrame to visualize

    Returns:
        Chart config dict with keys: type, x_col, y_col, feedback (optional)
        Returns None if no suitable chart can be inferred
    """
    # Validate minimum requirements
    if df.empty or len(df) < MIN_ROWS_FOR_CHART:
        logger.info("DataFrame too small for chart generation")
        return {"type": None, "feedback": f"Chart requires at least {MIN_ROWS_FOR_CHART} rows of data."}

    if len(df.columns) < 2:
        logger.info("Need at least 2 columns for chart generation")
        return {"type": None, "feedback": "Chart requires at least 2 columns (one category, one value)."}

    # Analyze column types
    column_types = {col: _detect_column_type(df[col]) for col in df.columns}

    categorical_cols = [col for col, typ in column_types.items() if typ == "categorical"]
    numeric_cols = [col for col, typ in column_types.items() if typ == "numeric"]
    temporal_cols = [col for col, typ in column_types.items() if typ == "temporal"]

    # Check for explicit chart type in query
    if _match_chart_pattern(query, "pie"):
        # Pie chart: need 1 categorical + 1 numeric
        if categorical_cols and numeric_cols:
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            num_categories = df[x_col].nunique()

            # Auto-switch to bar if too many categories for pie
            if num_categories > MAX_PIE_SLICES:
                if num_categories <= MAX_BAR_CATEGORIES:
                    logger.info(f"Switched from pie to bar chart ({num_categories} categories)")
                    return {
                        "type": "bar",
                        "x_col": x_col,
                        "y_col": y_col,
                        "feedback": f"Switched to bar chart: {num_categories} categories exceeds pie chart limit of {MAX_PIE_SLICES}."
                    }
                else:
                    # Too many even for bar - consolidate
                    logger.info(f"Too many categories ({num_categories}), will consolidate to top {MAX_BAR_CATEGORIES}")
                    return {
                        "type": "bar",
                        "x_col": x_col,
                        "y_col": y_col,
                        "feedback": f"Showing top {MAX_BAR_CATEGORIES - 1} categories (of {num_categories}) with remaining grouped as 'Other'."
                    }

            return {"type": "pie", "x_col": x_col, "y_col": y_col}
        else:
            return {"type": None, "feedback": "Pie chart requires one text column and one numeric column."}

    if _match_chart_pattern(query, "line"):
        # Line chart: need 1 temporal + 1 numeric
        if temporal_cols and numeric_cols:
            x_col = temporal_cols[0]
            y_col = numeric_cols[0]
            return {"type": "line", "x_col": x_col, "y_col": y_col}
        else:
            return {"type": None, "feedback": "Line chart requires one date/time column and one numeric column."}

    if _match_chart_pattern(query, "bar"):
        # Bar chart: need 1 categorical + 1 numeric
        if categorical_cols and numeric_cols:
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            num_categories = df[x_col].nunique()

            # Check category count
            if num_categories > MAX_BAR_CATEGORIES:
                logger.info(f"Too many categories ({num_categories}), will consolidate to top {MAX_BAR_CATEGORIES}")
                return {
                    "type": "bar",
                    "x_col": x_col,
                    "y_col": y_col,
                    "feedback": f"Showing top {MAX_BAR_CATEGORIES - 1} categories (of {num_categories}) with remaining grouped as 'Other'."
                }

            return {"type": "bar", "x_col": x_col, "y_col": y_col}
        else:
            return {"type": None, "feedback": "Bar chart requires one text column and one numeric column."}

    # Auto-detect based on data shape if no explicit pattern
    if temporal_cols and numeric_cols:
        return {"type": "line", "x_col": temporal_cols[0], "y_col": numeric_cols[0]}

    if categorical_cols and numeric_cols:
        x_col = categorical_cols[0]
        y_col = numeric_cols[0]
        num_categories = df[x_col].nunique()

        if num_categories <= MAX_PIE_SLICES:
            return {"type": "pie", "x_col": x_col, "y_col": y_col}
        elif num_categories <= MAX_BAR_CATEGORIES:
            return {"type": "bar", "x_col": x_col, "y_col": y_col}
        else:
            # Consolidate for very large category counts
            return {
                "type": "bar",
                "x_col": x_col,
                "y_col": y_col,
                "feedback": f"Showing top {MAX_BAR_CATEGORIES - 1} categories (of {num_categories}) with remaining grouped as 'Other'."
            }

    # No suitable columns found
    if not categorical_cols and not temporal_cols:
        return {"type": None, "feedback": "Chart requires at least one text or date column for the axis."}
    if not numeric_cols:
        return {"type": None, "feedback": "Chart requires at least one numeric column for values."}

    logger.info("Could not infer suitable chart type from data")
    return {"type": None, "feedback": "Unable to determine suitable chart type for this data."}


def generate_chart(df: pd.DataFrame, chart_config: dict[str, Any]) -> alt.Chart | None:
    """
    Generate Altair chart based on configuration.

    Args:
        df: Data to visualize
        chart_config: Chart configuration with keys: type, x_col, y_col

    Returns:
        Altair Chart object or None if generation fails
    """
    try:
        chart_type = chart_config.get("type")
        x_col = chart_config.get("x_col")
        y_col = chart_config.get("y_col")

        if not all([chart_type, x_col, y_col]):
            logger.error("Invalid chart config: missing required fields")
            return None

        if x_col not in df.columns or y_col not in df.columns:
            logger.error(f"Chart columns not found in DataFrame: {x_col}, {y_col}")
            return None

        # Validate minimum data
        if df.empty or len(df) < MIN_ROWS_FOR_CHART:
            logger.info("Insufficient data for chart generation")
            return None

        # Create working copy
        chart_df = df[[x_col, y_col]].copy()

        # Generate chart based on type
        if chart_type == "pie":
            # Consolidate categories if needed
            if chart_df[x_col].nunique() > MAX_PIE_SLICES:
                chart_df = _consolidate_small_categories(
                    chart_df, x_col, y_col, MAX_PIE_SLICES
                )

            chart = alt.Chart(chart_df).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field=y_col, type="quantitative"),
                color=alt.Color(
                    field=x_col,
                    type="nominal",
                    scale=alt.Scale(range=VIBRANT_PALETTE),
                    legend=alt.Legend(title=x_col.replace("_", " ").title())
                ),
                tooltip=[
                    alt.Tooltip(x_col, title=x_col.replace("_", " ").title()),
                    alt.Tooltip(y_col, title=y_col.replace("_", " ").title())
                ]
            ).properties(
                width=500,
                height=400,
                title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}"
            )

        elif chart_type == "bar":
            # Consolidate categories if needed
            if chart_df[x_col].nunique() > MAX_BAR_CATEGORIES:
                chart_df = _consolidate_small_categories(
                    chart_df, x_col, y_col, MAX_BAR_CATEGORIES
                )

            # Phase 9 DVZ-05: HORIZONTAL bar — value (Q) on x, category (N) on y.
            # sort='-x' on the Y encoding produces "largest bar at top" ordering.
            # See 09-RESEARCH.md Pitfall 5 for the -x vs -y sort gotcha.
            base = alt.Chart(chart_df)

            bars = base.mark_bar().encode(
                x=alt.X(
                    field=y_col,
                    type="quantitative",
                    title=y_col.replace("_", " ").title()
                ),
                y=alt.Y(
                    field=x_col,
                    type="nominal",
                    sort="-x",
                    title=x_col.replace("_", " ").title()
                ),
                color=alt.Color(
                    field=x_col,
                    type="nominal",
                    scale=alt.Scale(range=VIBRANT_PALETTE),
                    legend=None
                ),
                tooltip=[
                    alt.Tooltip(x_col, title=x_col.replace("_", " ").title()),
                    alt.Tooltip(y_col, title=y_col.replace("_", " ").title())
                ]
            )

            # Layered text marks — value labels to the right of each bar.
            # Inter 12px charcoal, comma-formatted; matches mockup
            # .planning/design-mockups/02-results-chart.png.
            labels = base.mark_text(
                align="left",
                baseline="middle",
                dx=4,
                font="Inter",
                fontSize=12,
                color="#2C2420"
            ).encode(
                x=alt.X(field=y_col, type="quantitative"),
                y=alt.Y(field=x_col, type="nominal", sort="-x"),
                text=alt.Text(field=y_col, type="quantitative", format=",")
            )

            chart = alt.layer(bars, labels).properties(
                width=600,
                height=max(200, len(chart_df) * 32),
                title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}"
            )

        elif chart_type == "line":
            # Sort by x-axis for line chart
            chart_df = chart_df.sort_values(x_col)

            chart = alt.Chart(chart_df).mark_line(
                point=True,
                color="#C0392B"  # crimson — VIBRANT_PALETTE[0]
            ).encode(
                x=alt.X(
                    field=x_col,
                    type="temporal" if _detect_column_type(chart_df[x_col]) == "temporal" else "quantitative",
                    title=x_col.replace("_", " ").title()
                ),
                y=alt.Y(
                    field=y_col,
                    type="quantitative",
                    title=y_col.replace("_", " ").title()
                ),
                tooltip=[
                    alt.Tooltip(x_col, title=x_col.replace("_", " ").title()),
                    alt.Tooltip(y_col, title=y_col.replace("_", " ").title())
                ]
            ).properties(
                width=600,
                height=400,
                title=f"{y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}"
            )

        else:
            logger.error(f"Unsupported chart type: {chart_type}")
            return None

        logger.info(f"Generated {chart_type} chart successfully")
        return chart

    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None
