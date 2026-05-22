# ServiceNow Incident Query Tool - User Guide

**Created by Kevin "Overlord of AI Bespoke Apps" Taylor**

A natural language query interface for ServiceNow incident data using AI-powered search and analysis.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Loading Data](#loading-data)
3. [Building Embeddings](#building-embeddings)
4. [Query Modes](#query-modes)
5. [Chart Visualization](#chart-visualization)
6. [Writing Effective Queries](#writing-effective-queries)
7. [Understanding Results](#understanding-results)
8. [Settings](#settings)
9. [LLM Provider Selection](#llm-provider-selection)
10. [Tips & Best Practices](#tips--best-practices)
11. [Troubleshooting](#troubleshooting)

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

### Unlocking CSV Upload

CSV upload is password-protected. To upload files:

1. Enter the upload password in the sidebar
2. Click **"UNLOCK UPLOAD"**
3. Once unlocked, the file uploader appears
4. Click **"LOCK UPLOAD"** when finished to re-secure

**Default password:** `admin123` (change via `SNOWGREP_UPLOAD_PASSWORD` environment variable)

### Uploading CSV Files

1. Unlock the upload section (see above)
2. Click **"Browse files"** in the sidebar
3. Select your ServiceNow incident export CSV file
4. Choose load mode:
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

## Chart Visualization

Request charts in your queries to visualize data. Charts appear above the results table.

### Supported Chart Types

| Chart Type | Keywords | Best For |
|------------|----------|----------|
| **Pie Chart** | "pie chart", "breakdown", "proportion" | Category distribution |
| **Bar Chart** | "bar chart", "top 10", "compare", "ranking" | Comparisons, rankings |
| **Line Chart** | "line chart", "trend", "over time" | Time-based trends |

### Example Chart Queries

**Pie Charts:**
- "Create a pie chart of incidents by priority"
- "Show breakdown of incidents by category"
- "What's the proportion of incidents by assignment group?"

**Bar Charts:**
- "Bar chart of top 10 assignment groups by incident count"
- "Compare incident volumes by category"
- "Show ranking of most common issues"

**Line Charts:**
- "Show trend of incidents over time"
- "Line chart of incidents opened per week"
- "How have P1 incidents trended per month?"

### Chart Features

- **Vibrant Colors**: Each segment uses distinct, high-contrast colors
- **Dark Theme**: Charts match the application's terminal aesthetic
- **Interactive**: Hover for details (powered by Altair)
- **Auto-Detection**: The AI infers the best chart type if not specified

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
| "pie chart", "breakdown", "proportion" | Pie chart |
| "bar chart", "compare", "ranking" | Bar chart |
| "trend", "over time", "per week/month" | Line chart |

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

## LLM Provider Selection

### Overview

This app supports two LLM backends, selectable per session in the sidebar:

- **Azure OpenAI** (default) — existing behavior, unchanged.
- **Anthropic Claude (MGTI)** — Claude 4.5+ via the MGTI Apigee gateway.

The active provider is chosen from the sidebar `LLM PROVIDER` block, positioned between `EMBEDDINGS` and `CONFIG`. The currently active model identifier is displayed beneath the dropdown as `MODEL: <model-name>`. Every assistant response is captioned with the provider that produced it.

### MGTI-Only Constraint for Anthropic

Anthropic access in this app is **restricted to MGTI-enrolled users**. Credentials (`ANTHROPIC_API_KEY`) are issued only via the **Hubble** onboarding portal at https://hubble.mmc.com/apps after the coreapi-infrastructure onboarding step. The app does NOT connect to `api.anthropic.com` directly — that endpoint is not authorized in the MMC corporate app context.

If you do not have MGTI credentials, **stay on Azure OpenAI**. Selecting `Anthropic Claude (MGTI)` without credentials will display an inline warning in the sidebar and disable query submission until you switch back or populate the missing variables.

### How to Switch Providers

1. Locate the **`LLM PROVIDER`** block in the sidebar (between `EMBEDDINGS` and `CONFIG`).
2. Open the **`LLM provider`** dropdown and choose either `Azure OpenAI` or `Anthropic Claude (MGTI)`.
3. Confirm the **`MODEL:`** caption beneath the dropdown updates to the new provider's model identifier.
4. Send a query as usual — the next response will be produced by the new provider.
5. Verify the `via **<Provider>** · \`<model>\`` caption above the assistant's reply names the expected provider.

The switch takes effect on the **next query only** — in-flight queries finish on the previously selected provider, and historical messages keep their original provenance caption.

### What the Per-Message Caption Means

Every assistant response carries a small caption naming the provider and model that produced it. Format:

- Azure example: `via **Azure OpenAI** · \`gpt-4o-mini\``
- Anthropic example: `via **Anthropic Claude (MGTI)** · \`eu.anthropic.claude-sonnet-4-5-20250929-v1:0\``

Captions are written at response time and **never recomputed** — if you switch providers, historical messages keep their original captions. This is intentional: the caption reflects which provider actually produced that specific message, not which provider is currently selected.

### What to Do When a Provider Warning Appears

If you select a provider whose required environment variables are missing, the sidebar shows an orange warning naming each missing variable, and the chat input is disabled with the placeholder `QUERY DISABLED — see sidebar warning`. Use the table below to resolve.

| Warning text mentions   | Cause                                | Fix                                                                                          |
|-------------------------|--------------------------------------|----------------------------------------------------------------------------------------------|
| `ANTHROPIC_BASE_URL`    | Anthropic proxy URL not set          | Add `ANTHROPIC_BASE_URL` to `.env`; restart Streamlit                                        |
| `ANTHROPIC_API_KEY`     | Anthropic API key not set or empty   | Request via Hubble; add `ANTHROPIC_API_KEY` to `.env`; restart Streamlit                     |
| `ANTHROPIC_MODEL`       | Claude model identifier not set      | Set e.g. `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0` in `.env`; restart   |
| `AZURE_OPENAI_ENDPOINT` | Azure endpoint URL not set           | Add `AZURE_OPENAI_ENDPOINT` to `.env`; restart Streamlit                                     |
| `AZURE_OPENAI_API_KEY`  | Azure API key not set or empty       | Add `AZURE_OPENAI_API_KEY` to `.env`; restart Streamlit                                      |

Recovery paths (either works):

- **Populate the missing variables in `.env` and restart Streamlit.** The warning vanishes and the chat input becomes interactive on the next rerun.
- **Switch back to the other provider** in the sidebar dropdown. The warning is provider-scoped — switching to a configured provider clears it immediately.

### First-Time Anthropic Setup Checklist

If you are switching to Anthropic Claude for the first time, run through these four steps in order:

1. **Obtain MGTI access via Hubble.** Visit https://hubble.mmc.com/apps and complete the coreapi-infrastructure onboarding to receive your `ANTHROPIC_API_KEY`.
2. **Populate `.env`** with the three required Anthropic variables: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`. See `.env.example` for the template and the optional tuning variables.
3. **Run the smoke test** before opening the UI:
   ```bash
   python scripts/smoke_llm.py --provider anthropic_mgti --verbose
   ```
   Confirm `Exit: 0`. If it fails, the script prints the failing check — fix the env or contact your MGTI sponsor before proceeding.
4. **Restart Streamlit**, switch the sidebar selector to `Anthropic Claude (MGTI)`, send a test query, and confirm the per-message caption shows the Anthropic model.

### Mid-Session Switching Behavior

- Switches take effect on the **next query only**.
- In-flight queries finish on the previously selected provider (Streamlit's synchronous execution model means a switch cannot interleave with an in-flight call).
- Historical messages **retain** their original provider's caption — switching does not re-render historical provenance.
- The active model caption beneath the sidebar dropdown DOES update immediately to reflect the new selection.

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

*Last updated: May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)*
