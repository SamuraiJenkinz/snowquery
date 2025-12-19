<objective>
Create a new chart generation module for SNOWGREP that renders HTML charts (Pie, Bar, Line) using Altair, with a vibrant color palette on dark background.
</objective>

<context>
SNOWGREP is a Streamlit application for querying ServiceNow incident data. Currently it only displays results as tables. We're adding chart visualization capabilities.

Tech stack:
- Python 3.x with Streamlit
- Altair for charting (add to requirements.txt)
- Dark terminal theme background (#0a0a0a)

Existing patterns to follow:
- See `src/sql_generator.py` for module structure
- See `src/utils.py` for error handling patterns (custom exceptions)
- All src modules use type hints and docstrings
</context>

<requirements>
Create `src/chart_generator.py` with:

1. **Chart Type Inference Function**
   ```python
   def infer_chart_type(query: str, df: pd.DataFrame) -> dict | None
   ```
   - Analyze query text for chart keywords
   - Validate DataFrame shape supports the chart type
   - Return: `{"type": "pie|bar|line", "x_col": str, "y_col": str}` or None

2. **Chart Generation Function**
   ```python
   def generate_chart(df: pd.DataFrame, chart_config: dict) -> alt.Chart | None
   ```
   - Create Altair chart based on config
   - Apply dark background with vibrant colors
   - Handle edge cases gracefully

3. **Color Palette - VIBRANT & VARIED**
   Use a diverse, high-contrast color palette (NOT just green):
   ```python
   CHART_COLORS = [
       "#FF6B6B",  # Coral Red
       "#4ECDC4",  # Teal
       "#45B7D1",  # Sky Blue
       "#96CEB4",  # Sage Green
       "#FFEAA7",  # Soft Yellow
       "#DDA0DD",  # Plum
       "#98D8C8",  # Mint
       "#F7DC6F",  # Gold
       "#BB8FCE",  # Lavender
       "#85C1E9",  # Light Blue
   ]
   ```
   - Background: #0a0a0a (dark, matches app)
   - Text/labels: #e0e0e0 (light gray)
   - Axis lines: #333333

4. **Font Configuration**
   - Font: JetBrains Mono (fallback: monospace)
   - Title size: 14px
   - Label size: 11px

5. **Validation Rules**
   - Pie: max 10 slices (combine excess into "Other")
   - Bar: max 20 categories
   - Line: requires sortable x-axis (dates or numbers)
   - Minimum 2 rows required for any chart
</requirements>

<implementation>
Chart keyword detection patterns:

```python
CHART_PATTERNS = {
    "pie": ["pie chart", "pie graph", "breakdown by", "proportion"],
    "bar": ["bar chart", "bar graph", "compare", "top \\d+", "ranking"],
    "line": ["line chart", "trend", "over time", "per week", "per month"],
}
```

Column type detection:
- Categorical: object/string dtype, or numeric with <15 unique values
- Numeric: int64, float64
- Temporal: datetime64, or string columns parseable as dates

Chart type mapping logic:
| Data Shape | Preferred Chart |
|------------|-----------------|
| 1 categorical + 1 numeric | Pie (if ≤10 cats) or Bar |
| 1 temporal + 1 numeric | Line |
| 2 numeric | Bar (or scatter) |

Altair theme configuration example:
```python
def configure_chart_theme(chart: alt.Chart) -> alt.Chart:
    return chart.configure(
        background='#0a0a0a'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelColor='#e0e0e0',
        titleColor='#e0e0e0',
        gridColor='#333333',
        domainColor='#333333'
    ).configure_legend(
        labelColor='#e0e0e0',
        titleColor='#e0e0e0'
    ).configure_title(
        color='#e0e0e0'
    )
```
</implementation>

<output>
Create: `./src/chart_generator.py`

Module should export:
- `infer_chart_type(query: str, df: pd.DataFrame) -> dict | None`
- `generate_chart(df: pd.DataFrame, chart_config: dict) -> alt.Chart | None`
- `CHART_COLORS` (color palette list)

Also modify: `./requirements.txt`
- Add: `altair>=5.0.0`
</output>

<verification>
After implementation, verify:
1. Module imports without errors
2. `infer_chart_type("Create a pie chart by priority", df)` returns correct config
3. `generate_chart(df, config)` returns valid Altair chart object
4. Charts render with dark background (#0a0a0a)
5. Chart segments/bars use varied colors (red, teal, blue, yellow, etc.)
6. Edge cases handled: empty df, single row, too many categories
</verification>

<success_criteria>
- Clean module structure matching existing src/ patterns
- Type hints on all functions
- Docstrings explaining parameters and return values
- Graceful error handling (return None, don't raise)
- Dark background with VIBRANT, VARIED colors (not monochrome)
- Each pie slice / bar segment is a distinct, easily distinguishable color
</success_criteria>
