# ServiceNow Incident Query Tool

A local Python application that enables natural language querying of ServiceNow incident CSV exports.

**Created by Kevin "Overlord of AI Bespoke Apps" Taylor**

## Features

- **CSV Import**: Upload ServiceNow incident exports with automatic schema detection
- **SQL Queries**: Ask structured questions in plain English (e.g., "Show all P1 incidents from last month")
- **Semantic Search**: Find similar incidents using natural language (e.g., "Find incidents like Outlook crashes")
- **Intelligent Routing**: Automatically routes queries to the best search method

## Tech Stack

- **Python 3.10+**
- **DuckDB** - Fast SQL queries on local data
- **ChromaDB** - Vector embeddings for semantic search
- **sentence-transformers** - Local embedding generation
- **OpenAI API** - Query routing and SQL generation
- **Streamlit** - Web interface

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure OpenAI** (optional, for query routing):
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export OPENAI_API_BASE="https://your-corporate-endpoint"  # if using corporate instance
   ```

3. **Run the app**:
   ```bash
   streamlit run app.py
   ```

4. **Upload data**: Use the sidebar to upload a ServiceNow CSV export

## Project Structure

```
snow_query/
├── app.py                 # Streamlit entry point
├── config.py              # Configuration settings
├── data/                  # CSV uploads (runtime)
├── db/                    # DuckDB and ChromaDB persistence
├── src/
│   ├── ingest.py          # CSV → DuckDB loader
│   ├── embeddings.py      # Vector embeddings
│   ├── query_router.py    # Intent classification
│   ├── sql_generator.py   # NL → SQL
│   ├── semantic_search.py # Vector similarity search
│   └── utils.py           # Utilities
├── requirements.txt
└── README.md
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (required for query features) |
| `OPENAI_API_BASE` | API endpoint URL | https://api.openai.com/v1 |
| `OPENAI_MODEL` | Model to use | gpt-4o |
| `LOG_LEVEL` | Logging verbosity | INFO |

## Data Privacy

- All data processing happens locally
- Only OpenAI API calls leave your machine (for query routing/SQL generation)
- CSV data and embeddings are stored in the `db/` directory
