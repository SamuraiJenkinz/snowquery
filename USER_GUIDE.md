# ServiceNow Incident Query Tool - User Guide

**Created by Kevin "Overlord of AI Bespoke Apps" Taylor**

A natural language query interface for ServiceNow incident data using AI-powered search and analysis.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Loading Data](#loading-data)
3. [Building Embeddings](#building-embeddings)
4. [Query Modes](#query-modes)
5. [Writing Effective Queries](#writing-effective-queries)
6. [Understanding Results](#understanding-results)
7. [Settings](#settings)
8. [Tips & Best Practices](#tips--best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the Application

Open your web browser and navigate to:
```
http://<server-name>:8501
```

### Interface Overview

The application has two main areas:

| Area | Purpose |
|------|---------|
| **Sidebar (Left)** | Data management, embeddings, settings |
| **Main Area (Right)** | Query interface and results |

---

## Loading Data

### Uploading CSV Files

1. Click **"Browse files"** in the sidebar under "Upload ServiceNow CSV Export"
2. Select your ServiceNow incident export CSV file
3. Choose load mode:
   - **Replace**: Overwrites existing data (use for first upload or fresh start)
   - **Append**: Adds to existing data (use for combining multiple exports)

### Combining Multiple CSV Files

To aggregate data from multiple exports:

1. Upload first CSV → Click **Replace**
2. Upload second CSV → Click **Append**
3. Upload additional CSVs → Click **Append** for each
4. After all files loaded → Click **Rebuild** embeddings

### Recommended Fields

For optimal performance, export these ServiceNow fields:

**Essential:**
- number, sys_id
- short_description, description, close_notes
- priority, urgency, impact, severity
- state, category, subcategory
- assignment_group, assigned_to
- opened_at, closed_at, resolved_at

See `recommended_fields.txt` for the complete list.

---

## Building Embeddings

Embeddings enable semantic (AI-powered) search. Required for "Find Similar" and "Analyze" modes.

### When to Build

| Scenario | Action |
|----------|--------|
| First time loading data | Click **Rebuild** |
| Replaced all data | Click **Rebuild** |
| Appended new data | Click **Update** or **Rebuild** |

### Rebuild vs Update

- **Rebuild**: Clears all embeddings and creates fresh (use after Replace)
- **Update**: Only adds embeddings for new incidents (faster, use after Append)

### Build Time

Approximate times based on incident count:

| Incidents | Time |
|-----------|------|
| 10,000 | ~1-2 minutes |
| 50,000 | ~5-10 minutes |
| 100,000 | ~15-20 minutes |

---

## Query Modes

Select query mode from the dropdown in the main area:

### Auto (Default)

AI automatically determines the best search method based on your question.

**Best for:** General use, when unsure which mode to use

### Report (SQL)

Generates SQL queries for structured data retrieval.

**Best for:**
- Counts and aggregations ("How many P1 incidents?")
- Date-based queries ("Incidents from last month")
- Filtering ("Show all incidents for Team X")
- Sorting ("Top 10 by volume")

**Example queries:**
- "How many incidents were opened this week?"
- "Show all P1 incidents from November 2024"
- "Top 5 assignment groups by incident count"
- "Average resolution time by priority"

### Find Similar (Semantic)

Uses AI embeddings to find conceptually similar incidents.

**Best for:**
- Finding related issues ("Incidents similar to Outlook crashes")
- Symptom-based search ("Users unable to login")
- Exploratory queries ("Network connectivity problems")

**Example queries:**
- "Find incidents similar to VPN connection failures"
- "Issues where users report slow performance"
- "Problems related to password resets"

### Analyze (Hybrid)

Combines SQL filtering with semantic search for comprehensive results.

**Best for:**
- Complex queries needing both filtering and similarity
- Analysis requiring structured + unstructured search

**Example queries:**
- "P1 incidents similar to database outages"
- "Top trending Outlook issues this month"
- "Critical incidents involving network problems"

---

## Writing Effective Queries

### Good Query Examples

| Query Type | Example |
|------------|---------|
| Count | "How many incidents were opened in December 2024?" |
| Filter | "Show all P1 incidents assigned to Service Desk" |
| Trend | "What are the top 10 incident categories this quarter?" |
| Similar | "Find incidents similar to email delivery failures" |
| Analysis | "What were the most common Outlook issues in November?" |

### Tips for Better Results

1. **Be specific with dates**: "November 2024" instead of "recently"
2. **Use actual field values**: "P1" or "1 - Critical" for priority
3. **Include context**: "Outlook incidents" instead of just "Outlook"
4. **For similar search**: Describe the symptom or problem

### Query Keywords

The AI recognizes these patterns:

| Keywords | Triggers |
|----------|----------|
| "how many", "count", "total" | SQL aggregation |
| "top N", "most", "highest" | SQL with ordering |
| "last month", "this week", "between" | SQL date filtering |
| "similar to", "like", "related" | Semantic search |
| "issues with", "problems about" | Semantic search |

---

## Understanding Results

### Result Display

Each query shows:

1. **Route**: Which search method was used (Structured/Semantic/Hybrid)
2. **Confidence**: AI's confidence in the routing decision
3. **Reasoning**: Why this route was chosen
4. **Results Count**: Number of incidents found

### Executive Summary

When enabled, an AI-generated summary appears above results:

- **Key Findings**: Main insights from the data
- **Patterns/Trends**: Notable observations
- **Recommendation**: Actionable suggestions

### Results Table

- Columns are prioritized: number, short_description, priority, opened_at
- Click column headers to sort
- Scroll horizontally for additional columns

### Exporting Results

Click **"Export CSV"** to download the current results as a CSV file.

### Viewing SQL

If "Show generated SQL" is enabled, expand the **"Generated SQL"** section to see the query.

---

## Settings

Access settings in the sidebar under **"Settings" → "Query Settings"**:

| Setting | Description | Default |
|---------|-------------|---------|
| Results (semantic) | Number of results for semantic search | 10 |
| Show generated SQL | Display SQL queries in results | On |
| Show executive summary | Generate AI summary of results | On |

---

## Tips & Best Practices

### Performance

- Use **Report (SQL)** mode for simple counts/filters - faster than semantic
- Limit semantic results to what you need (default 10 is usually sufficient)
- For large datasets, be specific to narrow results

### Data Management

- Export only needed fields from ServiceNow (see `recommended_fields.txt`)
- Rebuild embeddings after major data changes
- Use Append for incremental data loads

### Query Strategy

1. Start with **Auto** mode to let AI choose
2. If results aren't right, manually select the appropriate mode
3. For trending/volume analysis → **Report (SQL)**
4. For "find similar" or symptom search → **Find Similar**
5. For complex analysis → **Analyze (Hybrid)**

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No data loaded" | Upload a CSV file first |
| "No embeddings built" | Click Rebuild in sidebar |
| "Azure OpenAI API error" | Check .env configuration, verify API access |
| Slow queries | Reduce semantic result count, be more specific |
| Schema mismatch on append | Use Replace instead, or ensure CSVs have same columns |

### Error Messages

**"Failed to load CSV file"**
- Check CSV format and encoding
- Ensure file isn't corrupted
- Try a smaller test file first

**"Azure OpenAI API call failed"**
- Verify network connectivity
- Check API key is valid
- Confirm endpoint URL is correct

**"No results found"**
- Try different search terms
- Switch query modes
- Check date ranges are valid
- Verify data exists for your criteria

### Getting Help

Contact your system administrator or refer to the project repository for technical documentation.

---

## Quick Reference

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Submit query | Enter |
| Clear chat | Click "Clear Chat" button |

### Status Indicators

| Icon | Meaning |
|------|---------|
| ✅ | Success/Ready |
| ⚠️ | Warning/Attention needed |
| ❌ | Error |
| 📊 | Structured (SQL) route |
| 🔮 | Semantic route |
| 🔄 | Hybrid route |

---

*Last updated: December 2024*
