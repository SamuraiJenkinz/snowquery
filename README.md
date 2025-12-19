# ServiceNow Incident Query Tool

A local Python application that enables natural language querying of ServiceNow incident CSV exports.

**Created by Kevin "Overlord of AI Bespoke Apps" Taylor**

## Features

- **CSV Import**: Upload ServiceNow incident exports with automatic schema detection
- **Password-Protected Upload**: Secure file uploads with configurable password
- **SQL Queries**: Ask structured questions in plain English (e.g., "Show all P1 incidents from last month")
- **Semantic Search**: Find similar incidents using natural language (e.g., "Find incidents like Outlook crashes")
- **Chart Visualization**: Generate pie, bar, and line charts from query results
- **Intelligent Routing**: Automatically routes queries to the best search method

## Tech Stack

- **Python 3.11** (recommended - best compatibility with ML packages)
- **DuckDB** - Fast SQL queries on local data
- **ChromaDB** - Vector embeddings for semantic search
- **sentence-transformers** - Local embedding generation
- **Azure OpenAI** - Query routing and SQL generation
- **Altair** - Interactive chart visualization
- **Streamlit** - Web interface

## Quick Start

1. **Create virtual environment** (Python 3.11 recommended):
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Azure OpenAI**:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

4. **Run the app**:
   ```bash
   streamlit run app.py
   ```

5. **Upload data**: Use the sidebar to upload a ServiceNow CSV export

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
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | (required) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | (required) |
| `API_VERSION` | Azure API version | 2023-05-15 |
| `SNOWGREP_UPLOAD_PASSWORD` | Password to unlock CSV upload | admin123 |
| `LOG_LEVEL` | Logging verbosity | INFO |

## Data Privacy

- All data processing happens locally
- Only Azure OpenAI API calls leave your machine (for query routing/SQL generation)
- CSV data and embeddings are stored in the `db/` directory
