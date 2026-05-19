# External Integrations

**Analysis Date:** 2026-05-19

## APIs & External Services

**Azure OpenAI (LLM):**
- Service: Azure OpenAI Chat Completions API
  - SDK/Client: `requests` library (HTTP POST)
  - Auth: API key via header (`api-key`)
  - Endpoint: `AZURE_OPENAI_ENDPOINT` (environment variable)
  - API Version: `API_VERSION` (default: 2023-05-15)
  - Usage:
    - Query intent classification (structured vs semantic vs hybrid)
    - Natural language to SQL generation
    - Executive summary generation
  - Timeout: 30 seconds per request
  - Files: `src/query_router.py:105-141`, `src/sql_generator.py:70-130`

**HTTP Client:**
- Package: `requests >=2.31.0`
- Used for: All Azure OpenAI API calls
- Error handling: Raises `QueryError` on connection/response failures

## Data Storage

**Databases:**
- DuckDB (Local embedded database)
  - Connection: File-based at `db/incidents.duckdb`
  - Client: `duckdb` Python package
  - Purpose: Fast SQL queries on incident CSV data
  - Table: `incidents` (inferred schema from CSV)
  - Data types: TIMESTAMP, VARCHAR, INTEGER (auto-detected)
  - Features: SQL for structured queries, aggregations, filters
  - Files: `src/sql_generator.py`, `src/semantic_search.py:165-197`, `src/ingest.py`

- ChromaDB (Vector database)
  - Client: `chromadb` Python package (persistent mode)
  - Location: `db/chroma/`
  - Purpose: Vector embeddings for semantic similarity search
  - Collection: `incidents` (contains embedded incident text)
  - Dimensions: 384-d (from sentence-transformers `all-MiniLM-L6-v2`)
  - Metadata: Priority, assignment_group, and other categorical fields
  - Features: Cosine distance similarity, metadata filtering
  - Files: `src/embeddings.py`, `src/semantic_search.py:21-105`

**File Storage:**
- Local filesystem only
  - CSV uploads: `data/` directory (runtime uploaded files)
  - Databases: `db/` directory (DuckDB `.duckdb` files, ChromaDB directories)
  - No cloud storage integration

## Authentication & Identity

**Auth Provider:**
- Custom: Environment-based API key authentication
  - Method: Bearer-like API key in HTTP headers
  - Provider: Azure OpenAI
  - Environment variables:
    - `AZURE_OPENAI_API_KEY` - Required for LLM calls
    - `AZURE_OPENAI_ENDPOINT` - Required for LLM calls
  - Implementation: Direct HTTP requests with header injection (`src/query_router.py:119-127`)

**Application-Level Access:**
- Password protection for CSV upload (mentioned in config but implementation varies by app version)
- Files: `app.py`, `fixedapp.py`, `app_brutalist.py` (Streamlit session state)

## Monitoring & Observability

**Error Tracking:**
- Built-in logging only
  - Logger: Python `logging` module
  - Level: Configured via `LOG_LEVEL` env var (default: INFO)
  - Handler: StreamHandler (stdout)
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Files: `src/utils.py:17-43`

**Logs:**
- Console/stdout only
- No persistent logging, monitoring, or external log aggregation
- Custom error classes:
  - `QueryError` - Query execution failures
  - `IngestionError` - CSV loading failures
  - `EmbeddingError` - Embedding/vector search failures
  - Files: `src/utils.py:46-71`

## CI/CD & Deployment

**Hosting:**
- Local execution only (Streamlit development server or containerized)
- No cloud deployment integration detected
- Runs as: `streamlit run app.py`

**CI Pipeline:**
- Not detected
- No GitHub Actions, Jenkins, or equivalent configuration

## Environment Configuration

**Required env vars:**
- `AZURE_OPENAI_ENDPOINT` - Azure deployment URL (no default)
- `AZURE_OPENAI_API_KEY` - API authentication key (no default)

**Optional env vars:**
- `API_VERSION` - Azure API version (default: 2023-05-15)
- `LOG_LEVEL` - Logging level (default: INFO)
- `SNOWGREP_UPLOAD_PASSWORD` - CSV upload password (mentioned in README, implementation varies)

**Secrets location:**
- `.env` file (git-ignored via `.gitignore`)
- Template: `.env.example` with placeholder values
- Files: `config.py:13` loads via `python-dotenv`

## Data Flow Architecture

**CSV Upload → DuckDB:**
1. User uploads ServiceNow CSV via Streamlit UI
2. `src/ingest.py:load_csv()` reads file into pandas
3. Type detection (`_detect_column_type()`) infers column types
4. Schema creation and loading into DuckDB table `incidents`
5. Persistence: `db/incidents.duckdb`

**Embeddings Pipeline:**
1. Load incident text fields (short_description, description, close_notes) from DuckDB
2. Batch encode using `sentence-transformers` model `all-MiniLM-L6-v2`
3. Store embeddings + metadata in ChromaDB collection `incidents`
4. Persistence: `db/chroma/` directory

**Query Classification:**
1. User submits natural language query
2. `src/query_router.py:classify_intent()` calls Azure OpenAI
3. Classification result: structured|semantic|hybrid
4. If structured: SQL generation via `src/sql_generator.py:query_with_sql()`
5. If semantic: Vector search via `src/semantic_search.py:semantic_query()`
6. If hybrid: Both approaches combined

**Chart Generation:**
1. Query results (pandas DataFrame) sent to `src/chart_generator.py`
2. Infer chart type from query intent or user request
3. Generate Altair visualization with dark theme colors
4. Return as Streamlit component

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## API Response Patterns

**Azure OpenAI Responses:**
- Format: JSON
- Structure:
  ```json
  {
    "choices": [
      {
        "message": {
          "content": "..."
        }
      }
    ]
  }
  ```
- Error handling: HTTP status validation via `requests.raise_for_status()`

**ChromaDB Responses:**
- Query results include: ids, distances, documents, metadatas
- Distance metric: Cosine distance (converted to similarity via `1 - distance`)

**DuckDB Responses:**
- `.fetchdf()` returns pandas DataFrame
- `.execute()` with parameterized queries (no direct SQL injection)

## Integration Points & Risk Areas

**Azure OpenAI Dependency:**
- Critical for: Query routing and SQL generation
- Risk: Network failures, API quota exhaustion, credential leakage
- Mitigation: 30-second timeout, error handling with user-friendly messages
- Fallback: Heuristic classification if API fails (`src/query_router.py:195`)

**ChromaDB Persistence:**
- Risk: Corrupted vector store (no backup mechanism)
- Mitigation: `embeddings_exist()` check before search
- Recovery: Rebuild embeddings button in UI

**DuckDB File Locking:**
- Risk: Multiple processes on same database file
- Mitigation: Read-only mode for queries (`read_only=True`)
- Implementation: `src/semantic_search.py:166`

---

*Integration audit: 2026-05-19*
