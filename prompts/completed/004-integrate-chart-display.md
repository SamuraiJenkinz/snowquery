<objective>
Integrate chart rendering into the SNOWGREP application, displaying charts above data tables when chart visualization is requested.
</objective>

<context>
Prerequisites (must be completed first):
- `src/chart_generator.py` exists with `infer_chart_type()` and `generate_chart()` functions
- `src/query_router.py` returns `chart_requested` and `chart_type` in classification

Current display flow in `app.py`:
1. User submits query via chat input
2. `process_query()` calls `route_query()` and gets results
3. `display_results()` shows executive summary + data table + export button

We need to insert chart rendering between executive summary and data table.
</context>

<requirements>
Modify `app.py`:

1. **Import Chart Module**
   ```python
   from src.chart_generator import infer_chart_type, generate_chart
   ```

2. **Update process_query() Function**
   - Extract `chart_requested` and `chart_type` from classification
   - If chart requested, call chart generator
   - Pass chart config to response dict

3. **Update display_results() Function**
   Add `chart` parameter and render if provided:
   ```python
   def display_results(df, sql, query_id, executive_summary=None, chart=None):
       # Executive summary (existing)
       if executive_summary:
           ...

       # Chart display (NEW)
       if chart is not None:
           st.markdown("### VISUALIZATION")
           st.altair_chart(chart, use_container_width=True)
           st.divider()

       # Data table (existing)
       ...
   ```

4. **Update Message History**
   Store chart in session state messages so it persists in chat history

5. **Style Chart Container**
   Add CSS for chart container to match theme:
   - Border: 1px solid #333
   - Padding: 1rem
   - Background: transparent (chart has own background)
</requirements>

<implementation>
Flow modification in `process_query()`:

```python
def process_query(user_query: str, mode: str):
    # ... existing code to get result from route_query() ...

    classification = result.get("classification", {})
    chart_requested = classification.get("chart_requested", False)
    chart_type = classification.get("chart_type")

    # Generate chart if requested and we have results
    chart = None
    if chart_requested and result.get("results") is not None:
        df = result["results"]
        if not df.empty:
            chart_config = infer_chart_type(user_query, df)
            if chart_config:
                # Override with explicit type if provided
                if chart_type:
                    chart_config["type"] = chart_type
                chart = generate_chart(df, chart_config)

    return {
        "content": "...",
        "results": result.get("results"),
        "sql": result.get("sql"),
        "executive_summary": executive_summary,
        "chart": chart,  # NEW
    }
```

Update `render_chat_history()` to pass chart to display_results:
```python
if "results" in message and message["results"] is not None:
    display_results(
        message["results"],
        message.get("sql"),
        message.get("query_id", ""),
        message.get("executive_summary"),
        message.get("chart"),  # NEW
    )
```
</implementation>

<output>
Modify: `./app.py`
- Add import for chart_generator module
- Update `process_query()` to generate charts
- Update `display_results()` to render charts
- Update `render_chat_history()` to pass chart
- Update message storage to include chart
- Add CSS for chart container styling
</output>

<verification>
After implementation, test end-to-end:

1. Start app: `streamlit run app.py`
2. Load sample CSV data
3. Test queries:
   - "Create a pie chart of incidents by priority" → Should show pie chart + table
   - "Bar chart of top 10 assignment groups" → Should show bar chart + table
   - "Show trend of incidents over time" → Should show line chart + table
   - "Show all P1 incidents" → Should show table only (no chart)
4. Verify chart appears above data table
5. Verify chart styling matches theme (dark background, green colors)
6. Verify chat history preserves charts on scroll
</verification>

<success_criteria>
- Charts render correctly for pie, bar, and line requests
- Charts styled with terminal theme
- Non-chart queries unchanged (table only)
- Charts persist in chat history
- Graceful fallback if chart generation fails (show table only)
- No errors in console
</success_criteria>
