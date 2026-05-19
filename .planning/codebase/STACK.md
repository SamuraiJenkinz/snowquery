# Technology Stack

**Analysis Date:** 2026-05-19

## Languages

**Primary:**
- Python 3.11 - Entire application (recommended for ML package compatibility)

**Secondary:**
- HTML/CSS - Streamlit theming and custom styling injections

## Runtime

**Environment:**
- Python 3.11 (recommended for PyTorch and transformers compatibility)

**Package Manager:**
- pip
- Lockfile: Not detected (requirements.txt only)

## Frameworks

**Core UI:**
- Streamlit >=1.40.0 - Web interface and interactive components

**Database/Query:**
- DuckDB >=1.1.0 - Fast SQL execution on incident data
- chromadb >=0.5.0 - Vector store for semantic search

**ML/NLP:**
- sentence-transformers >=3.0.0 - Local embedding generation (`all-MiniLM-L6-v2` model)
- torch >=2.6.0 - Deep learning backend (pinned for security)
- transformers >=4.51.0 - Transformer-based NLP utilities (pinned for security)
- onnxruntime >=1.14.1 - ONNX model inference acceleration

**Data Processing:**
- pandas >=2.2.0 - DataFrames and data manipulation

**Visualization:**
- altair >=5.0.0 - Interactive charts (pie, bar, line) with dark theme

## Key Dependencies

**Critical:**
- torch >=2.6.0 - CVE-2025-32434: RCE via torch.load() - pinned to patched version
- transformers >=4.51.0 - CVE-2025-14927, CVE-2025-14924: Code injection via checkpoint files - pinned
- sentence-transformers >=3.0.0 - Secure embedding model loading

**Infrastructure:**
- requests >=2.31.0 - HTTP client for Azure OpenAI API calls
- python-dotenv >=1.0.0 - Environment variable management
- python-certifi-win32 >=1.6.1 (Windows only) - Corporate proxy certificate support

## Configuration

**Environment:**
- `.env` file (git-ignored) with Azure OpenAI credentials
- `config.py` centralized configuration module
- Runtime paths: `data/` (CSV uploads), `db/` (DuckDB + ChromaDB persistence)

**Key Configuration Variables:**
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI deployment URL
- `AZURE_OPENAI_API_KEY` - API authentication key
- `API_VERSION` - Azure API version (default: 2023-05-15)
- `EMBEDDING_MODEL` - Model identifier: `all-MiniLM-L6-v2`
- `DUCKDB_PATH` - Database file location: `db/incidents.duckdb`
- `CHROMA_PATH` - Vector store location: `db/chroma`
- `LOG_LEVEL` - Logging verbosity (default: INFO)

**Build Configuration:**
- No build tool detected (pure Python application)
- Entry points: `app.py`, `fixedapp.py`, `app_brutalist.py`, `designui.py`

## Platform Requirements

**Development:**
- Python 3.11
- Virtual environment support
- Windows, macOS, or Linux (cross-platform)
- 500+ MB disk space (for model downloads)
- Network access for Azure OpenAI API

**Production:**
- Python 3.11 runtime
- Persistent file system (DuckDB + ChromaDB)
- Network access to Azure OpenAI API
- Corporate proxy support (Windows cert store integration)

## Model Specifications

**Embedding Model:**
- Name: `all-MiniLM-L6-v2` (from sentence-transformers)
- Dimensions: 384-d embeddings
- Context limit: 256 tokens max per document
- Used for: semantic similarity search in ChromaDB

**LLM Services:**
- Azure OpenAI Chat Completions API
- Temperature: 0.1 (deterministic outputs for routing/SQL)
- Max tokens: 500 per request

---

*Stack analysis: 2026-05-19*
