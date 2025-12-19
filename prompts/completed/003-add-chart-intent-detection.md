<objective>
Extend the query router to detect chart visualization requests and include chart metadata in the classification result.
</objective>

<context>
SNOWGREP uses `src/query_router.py` to classify user queries into STRUCTURED, SEMANTIC, or HYBRID intents. We need to add detection for chart requests like "Create a pie chart of incidents by priority".

The classification function `classify_intent()` returns a dict with intent type, confidence, and reasoning. We need to add chart-related fields.

Current classification result structure:
```python
{
    "intent": "structured|semantic|hybrid",
    "confidence": float,
    "reasoning": str
}
```
</context>

<requirements>
Modify `src/query_router.py`:

1. **Add Chart Detection Constants**
   ```python
   CHART_KEYWORDS = {
       "pie": ["pie chart", "pie graph", "breakdown by", "proportion"],
       "bar": ["bar chart", "bar graph", "compare", "top \\d+", "ranking"],
       "line": ["line chart", "trend", "over time", "per week", "per month"],
       "histogram": ["histogram", "distribution of"],
   }
   ```

2. **Extend Classification Result**
   Add to returned dict:
   ```python
   {
       ...existing fields...,
       "chart_requested": bool,
       "chart_type": str | None,  # "pie", "bar", "line", "histogram", or None
   }
   ```

3. **Detection Logic**
   - Check query text against CHART_KEYWORDS patterns
   - If explicit chart type found → set that type
   - If implicit (e.g., "breakdown") → infer likely type
   - Chart requests should still route to STRUCTURED (they need SQL aggregation)

4. **Update Heuristic Fallback**
   The `_heuristic_classification()` function should also detect chart keywords
</requirements>

<implementation>
Detection should happen early in `classify_intent()`:

```python
def classify_intent(query: str, schema: dict) -> dict:
    # Detect chart request first
    chart_requested, chart_type = _detect_chart_request(query)

    # Continue with existing classification logic...
    # (chart queries typically need STRUCTURED routing for aggregations)

    return {
        "intent": intent,
        "confidence": confidence,
        "reasoning": reasoning,
        "chart_requested": chart_requested,
        "chart_type": chart_type,
    }
```

New helper function:
```python
def _detect_chart_request(query: str) -> tuple[bool, str | None]:
    """Detect if query requests a chart and what type."""
    query_lower = query.lower()
    # Check patterns, return (True, "pie") or (False, None)
```
</implementation>

<output>
Modify: `./src/query_router.py`
- Add CHART_KEYWORDS constant near top of file
- Add `_detect_chart_request()` helper function
- Modify `classify_intent()` to include chart fields
- Update `_heuristic_classification()` to handle chart keywords
</output>

<verification>
After implementation, test these queries return correct chart detection:

| Query | chart_requested | chart_type |
|-------|-----------------|------------|
| "Show all P1 incidents" | False | None |
| "Create a pie chart by priority" | True | "pie" |
| "Bar chart of top 10 groups" | True | "bar" |
| "Trend of incidents over time" | True | "line" |
| "What's the breakdown by category" | True | "pie" |
| "Compare assignment groups" | True | "bar" |
</verification>

<success_criteria>
- Chart detection works for explicit and implicit requests
- Existing classification logic unchanged for non-chart queries
- All existing tests still pass
- New fields added to classification result
</success_criteria>
