# Architecture

**Analysis Date:** 2026-05-19

## Pattern Overview

**Overall:** Layered pipeline architecture with three-tier data flow (Ingestion → Routing → Query Execution)

**Key Characteristics:**
- **Multi-modal query routing**: Intelligent classification routes queries to semantic search, SQL, or hybrid approaches
- **Vector-backed semantic search**: Local embeddings via ChromaDB with sentence-transformers for similarity matching
- **LLM-powered SQL generation**: Azure OpenAI translates natural language to DuckDB SQL with few-shot examples
- **Result composition**: Hybrid queries combine and deduplicate SQL + semantic results for comprehensive answers
- **Chart inference**: Automatic detection of chart intent from user queries with smart type selection and category consolidation

## Layers

**Ingestion Layer:**
- Purpose: Load and persist ServiceNow CSV data with schema inference
- Location: `src/ingest.py`
- Contains: CSV parsing with multi-encoding support, DuckDB table creation, append/replace modes, type detection
- Depends on: DuckDB (file-based storage), pandas (data manipulation)
- Used by: Streamlit UI sidebar for upload, schema summary queries

**Embedding Layer:**
- Purpose: Build and manage vector embeddings for semantic search capability
- Location: `src/embeddings.py`
- Contains: SentenceTransformer model initialization, ChromaDB collection management, batch embedding, text preparation
- Depends on: ChromaDB (vector storage), sentence-transformers (embedding model), DuckDB (source data)
- Used by: Semantic search module, UI for embed management

**Query Router (Intent Classification):**
- Purpose: Classify user intent and route to appropriate query method
- Location: `src/query_router.py`
- Contains: Azure OpenAI classification, heuristic fallback, chart request detection, result combination logic
- Depends on: Azure OpenAI API, semantic_search module, sql_generator module
- Used by: Main app entry point for all query processing

**Structured Query Execution:**
- Purpose: Generate and execute SQL queries for filtered/aggregated data
- Location: `src/sql_generator.py`
- Contains: NL-to-SQL generation with few-shot examples, DuckDB execution, security validation (SELECT-only)
- Depends on: Azure OpenAI API, DuckDB
- Used by: Query router for structured queries

**Semantic Search Execution:**
- Purpose: Find incidents by semantic similarity without schema knowledge
- Location: `src/semantic_search.py`
- Contains: ChromaDB vector search, metadata filtering (priority, assignment_group), distance-to-similarity conversion, DuckDB enrichment
- Depends on: ChromaDB, sentence-transformers, DuckDB
- Used by: Query router for semantic queries

**Chart Generation:**
- Purpose: Infer and render visualizations from query results
- Location: `src/chart_generator.py`
- Contains: Chart type inference (pie/bar/line), category consolidation for large datasets, Altair chart generation with dark theme
- Depends on: Altair (visualization), pandas (data inspection)
- Used by: Display results in main query processing, called after results are obtained

**Utilities:**
- Purpose: Cross-cutting concerns (logging, errors, formatting)
- Location: `src/utils.py`
- Contains: Custom exception types (QueryError, IngestionError, EmbeddingError), dataframe formatting, schema representation for LLM
- Depends on: Python stdlib, pandas
- Used by: All modules for error handling and display formatting

**Configuration:**
- Purpose: Centralized settings and environment variables
- Location: `config.py`
- Contains: Azure OpenAI credentials, database paths, field mappings (TEXT_FIELDS, DATE_FIELDS, CATEGORY_FIELDS), limits
- Depends on: python-dotenv
- Used by: All modules

## Data Flow

**Query Processing (Auto Mode):**

1. User enters natural language query via Streamlit chat input
2. `route_query()` calls `classify_intent()` with Azure OpenAI
3. Classification returns: intent (structured|semantic|hybrid), confidence, detected_filters, chart_requested
4. Based on intent:
   - **Structured**: `query_with_sql()` → generates SQL → executes against DuckDB → returns filtered/aggregated rows
   - **Semantic**: `semantic_query()` → embeds query → ChromaDB vector search → enrich from DuckDB → returns similar incidents
   - **Hybrid**: Run both, combine results with deduplication (SQL results first as exact matches)
5. If chart_requested=true, `infer_chart_type()` analyzes result columns and user query
6. If suitable chart inferred, `generate_chart()` creates Altair visualization with dark theme
7. Optional: `generate_executive_summary()` calls Azure OpenAI to summarize results
8. Return to UI: results DataFrame, SQL (if available), explanation, chart, summary

**CSV Ingestion:**

1. User uploads file via password-protected sidebar
2. `load_csv()` reads with multi-encoding fallback
3. Schema detection: `_infer_schema()` analyzes each column (date patterns, numeric ranges, categories)
4. Type conversion for TIMESTAMP fields
5. DuckDB: drop existing table (or append to existing)
6. Register DataFrame as temp_df, CREATE TABLE AS SELECT * FROM temp_df
7. Return schema summary: table name, row count, column metadata with samples

**Embedding Build:**

1. User clicks REBUILD or UPDATE in sidebar
2. `build_embeddings()` fetches all rows from incidents table
3. For each row: `_prepare_text()` concatenates TEXT_FIELDS (short_description, description, close_notes)
4. Batch encode using SentenceTransformer with BATCH_SIZE=500
5. Store in ChromaDB with metadata: incident ID, priority, assignment_group
6. Progress callback updates UI
7. Return stats: total_embedded, time_taken

**State Management:**

- **Session state** (Streamlit): schema, messages, data_loaded, embeddings_ready, upload_authenticated
- **Persistent storage**: DuckDB file (db/incidents.duckdb), ChromaDB directory (db/chroma)
- **No server-side state**: Each Streamlit session manages its own context, reloads data from disk

## Key Abstractions

**ClassificationResult:**
- Purpose: Encapsulates intent classification output
- Examples: `src/query_router.py` → lines 201-210 (classify_intent return dict)
- Pattern: Dict with intent, confidence, reasoning, detected_filters, chart_requested, chart_type

**QueryResult:**
- Purpose: Unified result format across query methods
- Examples: All query methods (structured, semantic, hybrid) return dict with: results (DataFrame), row_count, explanation, error, route_used
- Pattern: Allows unified handling in display layer regardless of execution path

**SchemaInfo:**
- Purpose: Metadata about data structure for LLM context
- Examples: `src/ingest.py` → lines 264-275 (schema_summary dict)
- Pattern: Contains table_name, row_count, columns (list of {name, type, sample})

**ChartConfig:**
- Purpose: Instructions for chart generation
- Examples: `src/chart_generator.py` → lines 139-258 (infer_chart_type return dict)
- Pattern: Dict with type (pie|bar|line|None), x_col, y_col, optional feedback message

## Entry Points

**Streamlit Web UI (Primary):**
- Location: `app.py` (canonical entry point)
- Triggers: `streamlit run app.py` from command line
- Responsibilities: Session state init, sidebar render (data upload, embeddings manage), main chat interface, result display
- Call chain: main() → init_session_state() → render_sidebar() + render_main_content() → process_query() → route_query()

**Chart Generation Subprocess:**
- Location: `src/chart_generator.py` (called by app.py process_query)
- Triggers: After query results obtained, if chart_requested detected
- Responsibilities: Infer chart type from data shape and query, generate Altair visualization
- Call chain: process_query() → infer_chart_type() → generate_chart()

**Embedding Build Subprocess:**
- Location: `src/embeddings.py` (called by app.py sidebar)
- Triggers: User clicks REBUILD or UPDATE button
- Responsibilities: Load incidents, generate embeddings, store in ChromaDB with progress callback
- Call chain: render_sidebar() → _build_embeddings_with_progress() → build_embeddings()

## Error Handling

**Strategy:** Fail gracefully with user-friendly messages; fallback to heuristic classifiers when LLM unavailable

**Patterns:**

- **API Failures**: Azure OpenAI timeouts or rate limits in `sql_generator.py` and `query_router.py` → catch RequestException → raise QueryError with message + details
- **CSV Parsing**: Multiple encoding attempts (utf-8, cp1252, latin-1) before raising IngestionError
- **Embeddings**: Model loading failures raise EmbeddingError with details; search failures caught and returned as error in result dict
- **DuckDB Queries**: SQL syntax errors caught, returned as error message in result dict instead of crashing
- **Missing Data**: Check `table_exists()` and `embeddings_exist()` before operations; return helpful messages if prerequisites not met

**Exception Hierarchy:**

```python
QueryError(Exception):       # Query processing failures (SQL gen, routing)
IngestionError(Exception):   # CSV loading, schema inference failures  
EmbeddingError(Exception):   # Embedding model load, vector search failures
```

All three carry `message` and `details` fields for rich error reporting to user.

## Cross-Cutting Concerns

**Logging:** 
- Implementation: `src/utils.py` → setup_logging() configures StreamHandler with ISO datetime format
- Used by: All modules via `from src.utils import logger` then `logger.info/warning/error/exception`
- Level: Configurable via LOG_LEVEL env var (default INFO)

**Validation:**
- SQL Security: `sql_generator.py` → execute_sql() blocks UPDATE/DELETE/INSERT/DROP/ALTER keywords
- CSV Encoding: `ingest.py` → tries multiple encodings before failing
- Schema Types: `ingest.py` → _detect_column_type() heuristics for DATE_FIELDS, CATEGORY_FIELDS, TEXT_FIELDS
- Chart Data: `chart_generator.py` → validates >= 2 rows, >= 2 columns before generation

**Authentication:**
- Password Protection: Sidebar upload locked by SNOWGREP_UPLOAD_PASSWORD env var (default "admin123" for dev)
- Session State: upload_authenticated flag in Streamlit session prevents access until password entered

**Data Privacy:**
- All processing local: CSV data never leaves machine
- Only Azure OpenAI calls (query routing, SQL gen, summaries) are external
- No data sent to embeddings service: SentenceTransformer runs locally
- Persistent storage: DuckDB (.duckdb file), ChromaDB (chroma directory)

---

*Architecture analysis: 2026-05-19*
